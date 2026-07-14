import os
import json
import time
import logging
from typing import Dict, Any
from backend.agents.state import AgentState, get_effective_question
from backend.config import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
from backend.agents.schemas import VisualizationSpec

logger = logging.getLogger(__name__)

VISUALIZATION_GENERATOR_SYSTEM_PROMPT = """You are the Visualization Metadata Generator for the Autonomous Data Analyst Agent.
Your job is to determine the most appropriate visualization for the user's question and map the dataset columns to the chart.

CRITICAL RULES:
1. OUTPUT FORMAT: Respond ONLY with a valid JSON object. Do NOT wrap it in markdown backticks or explanation text.
2. The JSON object must strictly match the following schema:
{
  "is_appropriate": true/false, // Whether a visualization is appropriate for this data
  "chart_type": "bar" | "line" | "scatter" | "histogram" | "box" | "heatmap" | "pie" | "other" | null,
  "x_column": "<column name>", // Optional, set to null if not applicable
  "y_column": "<column name>", // Optional, set to null if not applicable
  "y_columns": ["<col1>", "<col2>"], // Optional, use for multi-measure charts (e.g. comparing two metrics over time)
  "color_column": "<column name>", // Optional, set to null if not applicable
  "grouping": "<optional description>", 
  "title": "<chart title>",
  "x_axis_title": "<optional custom title>",
  "y_axis_title": "<optional custom title>",
  "custom_code": "<optional raw Plotly python code ONLY if chart_type is 'other'>"
}
3. If is_appropriate is false, set chart_type to null and columns to null.
4. If chart_type is "other", you MUST provide valid, self-contained Python Plotly code in the `custom_code` field.
   - The environment already has a preloaded pandas DataFrame named `df` containing the query results.
   - DO NOT load data from files (e.g., do not use pd.read_csv, pd.read_json, or open()).
   - Simply use `df` directly to create the Plotly chart.
   - You must assign your final Plotly figure to a variable named `fig`. Do not write to any files.
"""

def visualization_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    Generates a structured visualization specification JSON (VisualizationSpec).
    """
    node_name = "visualization_generator"
    start_time = time.time()
    vis_retry_count = state.get("vis_retry_count", 0)
    
    logger.info(f"Node started: {node_name} (Retry count: {vis_retry_count})")
    
    question = get_effective_question(state)
    query_result = state.get("query_result")
    vis_retry_history = state.get("vis_retry_history", [])
    
    status = "success"
    error_msg = None
    vis_spec_data = None
    vis_code = None
    
    if not query_result:
        logger.error("No SQL query results found in AgentState for visualization.")
        status = "failed"
        error_msg = "No SQL query results found in AgentState for visualization."
    else:
        try:
            # 1. Infer column datatypes for prompt context
            columns = query_result.get("columns", [])
            rows = query_result.get("rows", [])
            provided_dtypes = query_result.get("dtypes", {})
            schema_profile = state.get("schema_profile") or {}
            profile_cols = {c["name"]: c["dtype"] for c in schema_profile.get("columns", [])}
            
            inferred_types = {}
            for col_name in columns:
                if col_name in provided_dtypes:
                    inferred_types[col_name] = provided_dtypes[col_name]
                else:
                    dtype = profile_cols.get(col_name, "unknown")
                    inferred_types[col_name] = dtype

            # 2. Extract first 5 rows for sample context
            sample_rows = rows[:5]
            formatted_samples = []
            for r in sample_rows:
                if isinstance(r, dict):
                    formatted_samples.append(r)
                else:
                    formatted_samples.append(dict(zip(columns, r)))
            
            
            schema_summary = {
                "columns": columns,
                "inferred_data_types": inferred_types,
                "analytical_roles": query_result.get("analytical_roles", {}),
                "total_row_count": len(rows),
                "sample_rows": formatted_samples
            }
            
            
            # 3. Invoke LLM with minimized prompt payload
            prompt = f"""
User Question: {question}

Here is the schema and sample data of the query result:
{json.dumps(schema_summary, indent=2, default=str)}

Return ONLY the JSON VisualizationSpec.
"""
            messages = [
                SystemMessage(content=VISUALIZATION_GENERATOR_SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ]
            
            if vis_retry_history:
                logger.info("Injecting visualization failure history into Generator context.")
                failures_context = "\n---\n".join([
                    f"Attempt {i+1} Visualization Failure Details:\n"
                    f"- Error Message: {f['error_message']}\n"
                    f"- Generated Code context:\n{f['code_context']}"
                    for i, f in enumerate(vis_retry_history)
                ])
                messages.append(HumanMessage(
                    content=f"ATTENTION: Previous visualization execution failed. Here is the failure history:\n{failures_context}\n\nPlease adapt your JSON parameters to correct this error."
                ))
                
            llm = get_llm(temperature=0.0)
            response = llm.invoke(messages)
            output = response.content.strip()

            if output.startswith("```"):
                lines = output.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                output = "\n".join(lines).strip()
            
            try:
                vis_spec_data = json.loads(output)
                # Basic validation using pydantic model
                vis_spec = VisualizationSpec(**vis_spec_data)
                vis_spec_data = vis_spec.model_dump()
                if vis_spec.custom_code:
                    vis_code = vis_spec.custom_code
                logger.info(f"Generated VisualizationSpec successfully: {vis_spec.chart_type}")
            except Exception as e:
                logger.error(f"Failed to parse LLM JSON: {e}")
                status = "failed"
                error_msg = f"Failed to parse LLM output as VisualizationSpec JSON: {e}"
                vis_spec_data = None
                vis_code = None # Explicitly clear malformed code to prevent execution

                # Calculate metrics for early exit
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                node_metadata = {
                    "node_name": node_name,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_ms": duration_ms,
                    "status": status,
                    "retry_count": vis_retry_count,
                    "error_message": error_msg
                }
                execution_metadata = list(state.get("execution_metadata") or [])
                execution_metadata.append(node_metadata)
                
                return {
                    "vis_spec": None,
                    "vis_generated_code": None,
                    "execution_metadata": execution_metadata,
                    "failure_summary": {
                        "failure_type": "visualization",
                        "error_message": error_msg,
                        "code_context": output,
                        "expected_vs_actual": "Expected: Valid JSON VisualizationSpec. Actual: Invalid format or unparseable text."
                    }
                }
            
        except Exception as e:
            logger.error(f"Error in Visualization Generator Node: {e}")
            status = "failed"
            error_msg = str(e)

    # Calculate execution metrics
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000
    logger.info(f"Node completed: {node_name} in {duration_ms:.2f}ms | Status: {status}")
    
    node_metadata = {
        "node_name": node_name,
        "start_time": start_time,
        "end_time": end_time,
        "duration_ms": duration_ms,
        "status": status,
        "retry_count": vis_retry_count,
        "error_message": error_msg
    }
    
    execution_metadata = list(state.get("execution_metadata") or [])
    execution_metadata.append(node_metadata)
    
    return {
        "vis_spec": vis_spec_data,
        "vis_generated_code": vis_code,
        "execution_metadata": execution_metadata
    }

