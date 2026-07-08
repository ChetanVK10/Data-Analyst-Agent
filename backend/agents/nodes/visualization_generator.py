import os
import json
import time
import logging
from typing import Dict, Any
from backend.agents.state import AgentState
from backend.config import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
from backend.agents.sandbox import prepare_scratch_directory

logger = logging.getLogger(__name__)

VISUALIZATION_GENERATOR_SYSTEM_PROMPT = """You are the Plotly Visualization Generator for the Autonomous Data Analyst Agent.
Your job is to generate a self-contained Python script that creates a Plotly visualization from pre-computed SQL results.

CRITICAL RULES:
1. NEVER LOAD OR READ THE CSV FILE: Do NOT use `pd.read_csv` or attempt to read the raw CSV dataset.
2. NEVER QUERY THE DATABASE: Do NOT import duckdb or attempt to run SQL queries.
3. NEVER PERFORM DATA PROCESSING: Do NOT perform aggregations, filters, groupings, joins, or calculate statistics. All data processing has already been performed in SQL.
4. DATA RECONSTRUCTION:
   - The query results are pre-serialized and saved in a file named 'query_result.json' in the current working directory.
   - You MUST load 'query_result.json' and reconstruct the pandas DataFrame using exactly the following block of code:
     ```python
     import json
     import pandas as pd
     with open('query_result.json', 'r') as f:
         query_result = json.load(f)
     df = pd.DataFrame(query_result["rows"], columns=query_result["columns"])
     ```
5. VISUALIZATION:
   - Create the requested Plotly figure (using Plotly Express or Graph Objects).
   - Ensure the chart title, labels, and axes align with the user's question.
6. SERIALIZATION:
   - You MUST save the Plotly Figure object as 'chart.json' in the current directory using fig.write_json("chart.json"):
     ```python
     fig.write_json("chart.json")
     ```
7. OUTPUT FORMAT:
   - Output ONLY the raw, executable Python code. Do not wrap it in markdown backticks or explanation text.
"""

def visualization_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    Generates a Python script containing instructions to load SQL query results from disk and build a Plotly chart.
    """
    node_name = "visualization_generator"
    start_time = time.time()
    vis_retry_count = state.get("vis_retry_count", 0)
    
    logger.info(f"Node started: {node_name} (Retry count: {vis_retry_count})")
    
    question = state.get("question")
    query_result = state.get("query_result")
    vis_retry_history = state.get("vis_retry_history", [])
    session_id = state.get("session_id", "unknown")
    dataset_id = state.get("dataset_id", "unknown")
    
    status = "success"
    error_msg = None
    vis_code = ""
    
    if not query_result:
        logger.error("No SQL query results found in AgentState for visualization.")
        status = "failed"
        error_msg = "No SQL query results found in AgentState for visualization."
    else:
        try:
            # 1. Prepare sandbox scratch directory
            session_dir = prepare_scratch_directory(session_id, dataset_id)
            
            # 2. Serialize query result to a file on disk in CWD
            query_result_file = os.path.join(session_dir, "query_result.json")
            with open(query_result_file, "w", encoding="utf-8") as f:
                json.dump(query_result, f, default=str)
            logger.info(f"Serialized query result to {query_result_file}")
            
            # 3. Infer column datatypes for prompt context
            columns = query_result.get("columns", [])
            rows = query_result.get("rows", [])
            schema_profile = state.get("schema_profile") or {}
            profile_cols = {c["name"]: c["dtype"] for c in schema_profile.get("columns", [])}
            
            inferred_types = {}
            for idx, col_name in enumerate(columns):
                dtype = profile_cols.get(col_name)
                if not dtype and rows:
                    first_val = rows[0].get(col_name) if isinstance(rows[0], dict) else (rows[0][idx] if idx < len(rows[0]) else None)
                    dtype = type(first_val).__name__ if first_val is not None else "unknown"
                elif not dtype:
                    dtype = "unknown"
                inferred_types[col_name] = dtype

            # 4. Extract first 5 rows for sample context
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
                "total_row_count": len(rows),
                "sample_rows": formatted_samples
            }
            
            # 5. Invoke LLM with minimized prompt payload
            prompt = f"""
User Question: {question}

The pre-computed query results are saved in the current directory as 'query_result.json'.
Here is the schema and sample data of this query result:
{json.dumps(schema_summary, indent=2, default=str)}

Write a Python script that loads 'query_result.json', reconstructs the DataFrame, and generates the requested Plotly chart. Write ONLY raw Python code.
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
                    content=f"ATTENTION: Previous visualization code execution failed. Here is the failure history:\n{failures_context}\n\nPlease adapt your code to correct this error."
                ))
                
            llm = get_llm(temperature=0.0)
            response = llm.invoke(messages)
            code = response.content.strip()

            if code.startswith("```"):
                lines = code.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                code = "\n".join(lines).strip()
            
            vis_code = code
            logger.info("Generated Python Plotly visualization code successfully.")
            
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
        "vis_generated_code": vis_code,
        "execution_metadata": execution_metadata
    }
