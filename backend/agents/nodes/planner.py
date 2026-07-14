import json
import logging
from typing import Dict, Any
from backend.agents.state import AgentState, get_effective_question
from backend.config import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are the Lead Data Analyst Planner for an Autonomous Data Analyst Agent.
Your job is to analyze the user's natural language question and the schema of the active dataset, and produce a structured, step-by-step analysis plan.

CRITICAL RULES:
1. PREFER SQL OVER PYTHON:
   - For all data retrieval, filtering, aggregations, groupings, averages, trends, stats, and visualization (Plotly charts), choose the "sql" approach.
   - Do NOT write Python code to filter, join, or aggregate data. DuckDB SQL is highly optimized and runs in-memory.
   - For chart generation requests, set approach="sql" and expected_output_type="chart". The system will execute the SQL query first and then automatically run a dedicated Python script to plot the resulting data.
2. CONSTRAIN EXECUTION:
   - All SQL queries will run against the active table name: "{table_name}"
   - Keep the steps clear and minimal.
3. DATE & TIMESTAMP HANDLING IN DUCKDB:
   - Carefully inspect column types and sample values in the schema context.
   - If a VARCHAR column contains dates or timestamps (e.g., "2/24/2003 0:00"), plan to parse it using `strptime(column_name, 'format_string')` inside the SQL query before applying any date operators (like `date_trunc` or `strftime`).
   - Determine the correct `format_string` based on the provided sample values (e.g. '%m/%d/%Y %H:%M' for '2/24/2003 0:00', or '%Y-%m-%d' for '2003-02-24').

You must return a JSON object with the following fields:
{{
  "steps": ["Step 1 explanation...", "Step 2..."],
  "approach": "sql",
  "expected_output_type": "dataframe" or "scalar" or "chart"
}}

Ensure your response is valid JSON only. Do not wrap in markdown blocks other than standard json output.
"""

def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyzes the schema and question, and returns an execution plan.
    """
    import time
    node_name = "planner"
    start_time = time.time()
    retry_count = state.get("retry_count", 0)
    
    logger.info(f"Node started: {node_name} (Retry count: {retry_count})")
    
    question = get_effective_question(state)
    schema_profile = state.get("schema_profile")
    table_name = state.get("duckdb_table") or state.get("dataset_id")
    retry_history = state.get("retry_history", [])
    
    status = "success"
    error_msg = None
    updates = {}
    
    # Construct the schema description for the LLM
    columns_desc = ""
    for col in schema_profile.get("columns", []):
        samples = col.get("sample_values", [])
        samples_str = f" | Samples: {samples}" if samples else ""
        columns_desc += f"- {col['name']} ({col['dtype']}){samples_str}\n"
    
    schema_context = f"""
Dataset Table Name: {table_name}
Total Rows: {schema_profile.get('row_count', 'unknown')}
Columns:
{columns_desc}
"""

    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT.format(table_name=table_name)),
        HumanMessage(content=f"Dataset Schema:\n{schema_context}\n\nUser Question:\n{question}")
    ]

    # If we are retrying due to semantic failure
    if retry_history:
        semantic_failures = [f for f in retry_history if f["failure_type"] == "semantic"]
        if semantic_failures:
            logger.info("Injecting semantic failure history into Planner context.")
            failures_context = "\n---\n".join([
                f"Attempt {i+1} Failure:\n"
                f"- Failure Type: {f['failure_type']}\n"
                f"- Error Message: {f['error_message']}\n"
                f"- Code/SQL Executed: {f['code_context']}\n"
                f"- Mismatch details: {f['expected_vs_actual']}"
                for i, f in enumerate(semantic_failures)
            ])
            messages.append(HumanMessage(
                content=f"ATTENTION: Previous attempts failed validation due to semantic mismatch. Here is the compressed history of failures:\n{failures_context}\n\nPlease adapt your plan to correct these issues."
            ))

    try:
        llm = get_llm(temperature=0.1)
        response = llm.invoke(messages)
        
        # Clean up code blocks if present
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        plan_data = json.loads(content, strict=False)
        logger.info(f"Generated plan. Approach: {plan_data.get('approach')}, Expected Output: {plan_data.get('expected_output_type')}")
        
        updates = {
            "plan": plan_data,
            "expected_output_type": plan_data.get("expected_output_type"),
            "generated_code": None,
            "execution_success": False
        }
    except Exception as e:
        logger.error(f"Error in Planner Node: {e}")
        status = "failed"
        error_msg = str(e)
        # Default plan to allow progression
        fallback_plan = {
            "steps": ["Retrieve data using SELECT *"],
            "approach": "sql",
            "expected_output_type": "dataframe"
        }
        error_str = error_msg.lower()
        if "429" in error_str or "resource_exhausted" in error_str or "rate limit" in error_str:
            logger.error("Provider chain exhausted due to rate limit. Skipping agent retry loop.")
            updates = {
                "plan": fallback_plan,
                "expected_output_type": "dataframe",
                "generated_code": None,
                "execution_success": False,
                "failure_summary": {
                    "failure_type": "provider_error",
                    "error_message": "Provider chain exhausted due to rate limit.",
                    "code_context": "",
                    "expected_vs_actual": error_msg
                }
            }
        else:
            updates = {
                "plan": fallback_plan,
                "expected_output_type": "dataframe",
                "generated_code": None,
                "execution_success": False
            }

    # Record metrics
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000
    logger.info(f"Node completed: {node_name} in {duration_ms:.2f}ms | Status: {status}")
    
    node_metadata = {
        "node_name": node_name,
        "start_time": start_time,
        "end_time": end_time,
        "duration_ms": duration_ms,
        "status": status,
        "retry_count": retry_count,
        "error_message": error_msg
    }
    
    execution_metadata = list(state.get("execution_metadata") or [])
    execution_metadata.append(node_metadata)
    updates["execution_metadata"] = execution_metadata
    
    return updates
