import json
import logging
from typing import Dict, Any
from backend.agents.state import AgentState
from backend.config import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

SQL_GENERATOR_PROMPT = """You are the SQL Code Generator for the Autonomous Data Analyst Agent.
Your job is to generate a single, highly optimized SELECT query to run against DuckDB/PostgreSQL.

CRITICAL RULES:
1. ONLY write a SELECT statement. Do NOT write INSERT, UPDATE, DELETE, CREATE, or DROP statements.
2. The active table name in the query must be "{table_name}".
3. Keep the column names exactly as they appear in the schema.
4. Output ONLY the raw SQL query. Do not wrap it in explanation text or backticks, just output the plain SQL.
5. DATE & TIMESTAMP OPERATIONS (DUCKDB SQL-COMPATIBLE):
   - Review the schema and sample values for columns representing dates/timestamps.
   - If a column is a VARCHAR resembling a date (e.g., '2/24/2003 0:00'), you MUST parse it using the `strptime()` function with the correct format string (e.g. `strptime(OrderDate, '%m/%d/%Y %H:%M')`) before applying date functions like `date_trunc()` or `strftime()`.
   - Never apply `date_trunc` or date aggregations directly on unparsed VARCHAR columns.

Schema:
{schema_context}

Original Question:
{question}

Plan Steps:
{plan_steps}
"""

PYTHON_GENERATOR_PROMPT = """You are the Python Code Generator for the Autonomous Data Analyst Agent.
Your job is to generate a self-contained Python script to solve the analysis plan (typically for visualization or report generation).

CRITICAL RULES:
1. DATA LOADING:
   - The dataset is stored as a CSV file in the current working directory as "{dataset_id}.csv".
   - Load it using pandas: `df = pd.read_csv("{dataset_id}.csv")`
2. VISUALIZATION (IF APPLICABLE):
   - If the expected output is a chart, generate a Plotly chart.
   - You MUST write the Plotly Figure object to a file named "chart.json" in the current directory using fig.write_json("chart.json"):
     ```python
     # Create figure 'fig'
     fig.write_json("chart.json")
     ```
3. PDF GENERATION (IF APPLICABLE):
   - If generating a PDF report, use ReportLab and save the output file to "report.pdf" in the current directory.
4. SANDBOX LIMITS:
   - Do NOT attempt to access the network.
   - Do NOT import unauthorized libraries (standard libraries like pandas, numpy, plotly, reportlab, json, and math are allowed).
5. Output ONLY the raw Python code. Do not wrap it in markdown backticks or explanation text.
6. Handle exceptions gracefully within your script and print clean outputs.

Schema:
{schema_context}

Original Question:
{question}

Plan Steps:
{plan_steps}
"""

def code_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    Generates SQL or Python code based on the plan and schema.
    """
    question = state.get("question")
    schema_profile = state.get("schema_profile")
    plan = state.get("plan") or {}
    dataset_id = state.get("dataset_id")
    table_name = state.get("duckdb_table") or dataset_id
    retry_history = state.get("retry_history", [])
    
    approach = plan.get("approach", "sql")
    plan_steps = "\n".join([f"- {s}" for s in plan.get("steps", [])])

    logger.info(f"Running Code Generator Node for approach: {approach}")

    # Build schema description
    columns_desc = ""
    for col in schema_profile.get("columns", []):
        samples = col.get("sample_values", [])
        samples_str = f" | Samples: {samples}" if samples else ""
        columns_desc += f"- {col['name']} ({col['dtype']}){samples_str}\n"
    schema_context = f"Table: {table_name}\nColumns:\n{columns_desc}"

    if approach == "sql":
        system_prompt = SQL_GENERATOR_PROMPT.format(table_name=table_name, schema_context=schema_context, question=question, plan_steps=plan_steps)
    else:
        system_prompt = PYTHON_GENERATOR_PROMPT.format(dataset_id=dataset_id, schema_context=schema_context, question=question, plan_steps=plan_steps)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Generate the code to answer: '{question}' using the plan above.")
    ]

    # Inject failure history if we are retrying code generation
    if retry_history:
        # Get failures related to code execution (runtime, structural, visualization, timeout)
        code_failures = [f for f in retry_history if f["failure_type"] in ["runtime", "structural", "visualization", "timeout"]]
        if code_failures:
            logger.info("Injecting code execution failure history into Code Generator context.")
            failures_context = "\n---\n".join([
                f"Attempt {i+1} Failure Details:\n"
                f"- Failure Type: {f['failure_type']}\n"
                f"- Error Message: {f['error_message']}\n"
                f"- Code Executed:\n{f['code_context']}\n"
                f"- Mismatch details: {f['expected_vs_actual']}"
                for i, f in enumerate(code_failures)
            ])
            messages.append(HumanMessage(
                content=f"ATTENTION: Previous code execution attempts failed. Here is the compressed history of failures:\n{failures_context}\n\nPlease analyze these failures and rewrite the code to fix the root cause. Do NOT repeat the same mistakes."
            ))

    try:
        llm = get_llm(temperature=0.0) # 0.0 temperature for deterministic code generation
        response = llm.invoke(messages)
        code = response.content.strip()

        # Clean markdown code blocks (e.g. ```sql or ```python)
        if code.startswith("```"):
            lines = code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            code = "\n".join(lines).strip()

        logger.info(f"Generated {approach.upper()} code successfully.")
        return {"generated_code": code}
    except Exception as e:
        logger.error(f"Error in Code Generator Node: {e}")
        return {"generated_code": ""}
