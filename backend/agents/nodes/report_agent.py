"""
report_agent.py — Generates a fully structured JSON report validated against
the AnalysisResponse Pydantic schema.

The LLM is asked to produce ONLY a JSON object matching LLMReportOutput.
The node then assembles the full AnalysisResponse by merging LLM output
with execution context (tables, charts, SQL, dataset info).

On Pydantic ValidationError the node retries ONCE with the error injected
into the prompt before falling back to a graceful failure report.
"""

import json
import logging
from typing import Any, Dict

from pydantic import ValidationError
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agents.state import AgentState
from backend.agents.schemas import (
    AnalysisResponse,
    ChartSpec,
    ChartType,
    DebugInfo,
    ExecutiveSummary,
    FailureResponse,
    Insight,
    LLMReportOutput,
    Recommendation,
    ReportSection,
    TableResult,
)
from backend.config import get_llm
from backend.services.pdf_generator import generate_pdf_report
from backend.agents.sandbox import prepare_scratch_directory

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

REPORT_SYSTEM_PROMPT = """\
You are the Lead Report Analyst for an Autonomous Data Analyst Agent.
Your ONLY job is to produce a single, valid JSON object that matches the schema below.

OUTPUT RULES:
1. Respond with RAW JSON only — no markdown, no ```json fences, no explanation text.
2. Every field listed as required MUST be present and non-empty.
3. The "headline" must directly answer the user's question in one sentence.
4. The "summary" must be 2-3 paragraphs of professional business narrative.
5. Write 3-5 insights and 2-4 recommendations. Never return empty arrays.
6. Do NOT include SQL, table data, or chart specifications — those are handled by the system.
7. Use specific numbers and entity names from the data preview in your analysis.

REQUIRED JSON SCHEMA:
{
  "title": "<4-8 word descriptive report title>",
  "executive_summary": {
    "headline": "<one sentence that directly answers the question>",
    "summary": "<2-3 paragraph business narrative>",
    "confidence": "High" | "Medium" | "Low"
  },
  "insights": [
    { "title": "<4-6 word title>", "body": "<full insight paragraph>" }
  ],
  "recommendations": [
    { "title": "<4-6 word action title>", "body": "<full recommendation>" }
  ],
  "llm_reasoning": "<optional: brief explanation of your analytical approach>"
}
"""

REPORT_FAILURE_SYSTEM_PROMPT = """\
You are the Lead Failure Diagnostics Analyst for an Autonomous Data Analyst Agent.
The system attempted to answer the user's question but failed within the retry budget.

OUTPUT RULES:
1. Respond with RAW JSON only — no markdown, no fences, no explanation text.
2. Produce a JSON object matching exactly this schema:
{
  "title": "<descriptive failure title>",
  "executive_summary": {
    "headline": "<one sentence describing what was attempted and why it failed>",
    "summary": "<2-3 paragraphs: what was tried, root cause, suggestions to fix>",
    "confidence": "Low"
  },
  "insights": [
    { "title": "<failure insight title>", "body": "<what the agent found before failing>" }
  ],
  "recommendations": [
    { "title": "<action the user should take>", "body": "<how to reformulate the question or fix the data>" }
  ],
  "llm_reasoning": null
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _clean_json(raw: str) -> str:
    """Strip accidental markdown fences that some models still emit."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        # Drop first line (```json or ```) and last line (```)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw


def _call_llm_for_report(
    system_prompt: str,
    user_content: str,
    validation_error: str | None = None,
) -> LLMReportOutput:
    """
    Calls the LLM, parses JSON, validates against LLMReportOutput.
    Raises ValueError or ValidationError on failure.
    """
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    if validation_error:
        messages.append(HumanMessage(
            content=(
                f"Your previous response failed Pydantic validation with this error:\n"
                f"{validation_error}\n\n"
                "Please fix the JSON and return ONLY a valid JSON object."
            )
        ))

    llm = get_llm(temperature=0.3)
    response = llm.invoke(messages)
    raw = _clean_json(response.content)
    data = json.loads(raw)
    return LLMReportOutput.model_validate(data)


def _build_user_prompt(
    question: str,
    code: str,
    preview: list,
    plan_steps: str | None,
) -> str:
    return (
        f"User Question: {question}\n\n"
        f"Execution Plan:\n{plan_steps or 'N/A'}\n\n"
        f"Executed SQL/Code:\n{code or 'N/A'}\n\n"
        f"Data Output Preview (top rows):\n{json.dumps(preview, default=str)}"
    )


def _build_failure_prompt(question: str, code: str, failures: list) -> str:
    failures_desc = "\n".join(
        f"- Attempt {i + 1} ({f['failure_type']}): {f['error_message']}\n"
        f"  Context: {f.get('expected_vs_actual', '')}"
        for i, f in enumerate(failures)
    )
    return (
        f"User Question: {question}\n\n"
        f"Last Attempted Code:\n{code or 'N/A'}\n\n"
        f"Failure History:\n{failures_desc}"
    )


def _plan_steps_str(plan: dict) -> str | None:
    steps = plan.get("steps", [])
    if not steps:
        return None
    return "\n".join(f"- {s}" for s in steps)


# ─────────────────────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────────────────────

def report_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Generates the final AnalysisResponse-shaped dict stored in state.final_report.

    Success path:
      1. Build user prompt from question + SQL + data preview.
      2. Call LLM → validate LLMReportOutput.
      3. On ValidationError: retry ONCE with error context.
      4. Merge with tables (from query_result), charts (from output_summary),
         SQL (from generated_code), plan steps → AnalysisResponse.
      5. Serialize to dict → store as final_report.

    Failure path (graceful_failure=True):
      Same as above but uses REPORT_FAILURE_SYSTEM_PROMPT and omits tables/charts.
    """
    session_id     = state.get("session_id", "")
    question       = state.get("question", "")
    code           = state.get("generated_code") or ""
    output_summary = state.get("output_summary") or {}
    query_result   = state.get("query_result") or {}
    plan           = state.get("plan") or {}
    retry_history  = state.get("retry_history", [])
    graceful_failure = state.get("graceful_failure", False)
    schema_profile = state.get("schema_profile") or {}

    logger.info(f"Report Agent Node — graceful_failure={graceful_failure}")

    # ── Scratch dir for PDF ──────────────────────────────────────────────────
    dataset_id = state.get("dataset_id", "unknown")
    try:
        scratch_dir = prepare_scratch_directory(session_id, dataset_id)
    except Exception as e:
        logger.warning(f"Could not prepare scratch dir: {e}")
        import os
        scratch_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "scratch", session_id)
        )
        os.makedirs(scratch_dir, exist_ok=True)

    # ── Dataset context ──────────────────────────────────────────────────────
    columns_list = schema_profile.get("columns", [])
    dataset_info = {
        "name":    dataset_id,
        "rows":    schema_profile.get("row_count", 0),
        "columns": len(columns_list),
    }

    # ── Plan steps string ────────────────────────────────────────────────────
    plan_steps = _plan_steps_str(plan)

    # ═════════════════════════════════════════════════════════════════════════
    # GRACEFUL FAILURE PATH
    # ═════════════════════════════════════════════════════════════════════════
    if graceful_failure:
        user_prompt = _build_failure_prompt(question, code, retry_history)
        llm_output: LLMReportOutput | None = None
        validation_err: str | None = None

        for attempt in range(2):  # try → retry once
            try:
                llm_output = _call_llm_for_report(
                    REPORT_FAILURE_SYSTEM_PROMPT,
                    user_prompt,
                    validation_error=validation_err,
                )
                break
            except (json.JSONDecodeError, ValidationError, Exception) as exc:
                validation_err = str(exc)
                logger.warning(f"Report Agent failure LLM attempt {attempt + 1} failed: {exc}")

        if llm_output is None:
            # Hard fallback — construct minimal valid output
            llm_output = LLMReportOutput(
                title="Analysis Failed",
                executive_summary=ExecutiveSummary(
                    headline="The agent was unable to answer this question.",
                    summary=(
                        "Multiple attempts were made to execute a query for your question, "
                        "but each encountered errors. Please try rephrasing your question "
                        "or verify the dataset columns match what you are asking about."
                    ),
                    confidence="Low",
                ),
                insights=[Insight(title="Agent Exhausted Retries", body=str(retry_history))],
                recommendations=[
                    Recommendation(
                        title="Rephrase Your Question",
                        body="Try using column names exactly as they appear in the schema explorer.",
                    )
                ],
            )

        # PDF
        pdf_path: str | None = None
        try:
            pdf_path = generate_pdf_report(
                session_id=session_id,
                question=question,
                report_data={
                    "executive_summary": llm_output.executive_summary.model_dump(),
                    "insights": [i.model_dump() for i in llm_output.insights],
                    "recommendations": [r.model_dump() for r in llm_output.recommendations],
                },
                tables=[],
                scratch_dir=scratch_dir,
            )
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")

        final_report = {
            "success": False,
            "dataset": dataset_info,
            "report": {
                "title": llm_output.title,
                "executive_summary": llm_output.executive_summary.model_dump(),
                "tables": [],
                "charts": [],
                "insights": [i.model_dump() for i in llm_output.insights],
                "recommendations": [r.model_dump() for r in llm_output.recommendations],
            },
            "debug": {
                "generated_sql": code or None,
                "execution_plan": plan_steps,
                "llm_reasoning": llm_output.llm_reasoning,
            },
            "pdf_path": pdf_path,
        }
        return {"final_report": final_report}

    # ═════════════════════════════════════════════════════════════════════════
    # SUCCESS PATH
    # ═════════════════════════════════════════════════════════════════════════
    preview = output_summary.get("preview") or []
    user_prompt = _build_user_prompt(question, code, preview, plan_steps)

    llm_output = None
    validation_err = None

    for attempt in range(2):  # try → retry once on validation failure
        try:
            llm_output = _call_llm_for_report(
                REPORT_SYSTEM_PROMPT,
                user_prompt,
                validation_error=validation_err,
            )
            break
        except ValidationError as exc:
            validation_err = str(exc)
            logger.warning(f"Report Agent LLM attempt {attempt + 1} — ValidationError: {exc}")
        except json.JSONDecodeError as exc:
            validation_err = f"JSON decode error: {exc}"
            logger.warning(f"Report Agent LLM attempt {attempt + 1} — JSONDecodeError: {exc}")
        except Exception as exc:
            validation_err = str(exc)
            logger.error(f"Report Agent LLM attempt {attempt + 1} — unexpected error: {exc}")

    if llm_output is None:
        # Hard fallback
        llm_output = LLMReportOutput(
            title="Analysis Complete",
            executive_summary=ExecutiveSummary(
                headline="Analysis executed successfully.",
                summary="The query ran successfully. Please review the results table for detailed findings.",
                confidence="Medium",
            ),
            insights=[],
            recommendations=[],
        )

    # ── Build tables from query_result ───────────────────────────────────────
    tables: list[dict] = []
    qr_cols = query_result.get("columns", [])
    qr_rows = query_result.get("rows", [])
    if qr_cols and qr_rows:
        # rows from mcp/data_access come as list-of-dicts; normalise to list-of-lists
        normalised_rows: list[list] = []
        for row in qr_rows:
            if isinstance(row, dict):
                normalised_rows.append([row.get(c) for c in qr_cols])
            elif isinstance(row, (list, tuple)):
                normalised_rows.append(list(row))
            else:
                normalised_rows.append([row])
        tables.append({
            "title": "Query Results",
            "columns": qr_cols,
            "rows": normalised_rows,
        })

    # ── Build charts from output_summary.chart_json ──────────────────────────
    charts: list[dict] = []
    raw_chart = output_summary.get("chart_json")
    if raw_chart and isinstance(raw_chart, dict):
        # Infer chart type from Plotly trace type
        trace_type = "other"
        data_traces = raw_chart.get("data", [])
        if data_traces and isinstance(data_traces, list):
            trace_type = data_traces[0].get("type", "other")

        try:
            chart_type_enum = ChartType(trace_type)
        except ValueError:
            chart_type_enum = ChartType.OTHER

        layout_title = raw_chart.get("layout", {}).get("title", {})
        chart_title  = (
            layout_title.get("text") if isinstance(layout_title, dict) else layout_title
        ) or llm_output.title

        charts.append({
            "title":       chart_title,
            "type":        chart_type_enum.value,
            "plotly_json": raw_chart,
        })

    # ── Generate PDF ─────────────────────────────────────────────────────────
    pdf_path = None
    try:
        pdf_path = generate_pdf_report(
            session_id=session_id,
            question=question,
            report_data={
                "executive_summary": llm_output.executive_summary.model_dump(),
                "insights": [i.model_dump() for i in llm_output.insights],
                "recommendations": [r.model_dump() for r in llm_output.recommendations],
            },
            tables=tables,
            scratch_dir=scratch_dir,
        )
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")

    # ── Assemble final_report dict ────────────────────────────────────────────
    final_report = {
        "success": True,
        "dataset": dataset_info,
        "report": {
            "title": llm_output.title,
            "executive_summary": llm_output.executive_summary.model_dump(),
            "tables": tables,
            "charts": charts,
            "insights": [i.model_dump() for i in llm_output.insights],
            "recommendations": [r.model_dump() for r in llm_output.recommendations],
        },
        "debug": {
            "generated_sql": code or None,
            "execution_plan": plan_steps,
            "llm_reasoning": llm_output.llm_reasoning,
        },
        "pdf_path": pdf_path,
    }

    logger.info("Report Agent — structured report assembled successfully.")
    return {"final_report": final_report}
