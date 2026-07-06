import json
import logging
from typing import Dict, Any
from backend.agents.state import AgentState
from backend.config import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

VISUALIZATION_GENERATOR_SYSTEM_PROMPT = """You are the Plotly Visualization Generator for the Autonomous Data Analyst Agent.
Your job is to generate a self-contained Python script that creates a Plotly visualization from pre-computed SQL results.

CRITICAL RULES:
1. NEVER LOAD OR READ THE CSV FILE: Do NOT use `pd.read_csv` or attempt to read files.
2. NEVER QUERY THE DATABASE: Do NOT import duckdb or attempt to run SQL queries.
3. NEVER PERFORM DATA PROCESSING: Do NOT perform aggregations, filters, groupings, joins, or calculate statistics. All data processing has already been performed in SQL.
4. DATA RECONSTRUCTION:
   - You must reconstruct the pandas DataFrame from the provided `query_result` dictionary variable.
   - You MUST define the variable `query_result` at the top of your script exactly as provided in the instructions.
   - Reconstruct the DataFrame using:
     ```python
     import pandas as pd
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
    Generates a Python script containing hardcoded SQL query results to build a Plotly chart.
    """
    question = state.get("question")
    query_result = state.get("query_result")
    vis_retry_history = state.get("vis_retry_history", [])
    
    logger.info(f"Running Visualization Generator Node for question: '{question}'")

    if not query_result:
        logger.error("No SQL query results found in AgentState for visualization.")
        return {"vis_generated_code": ""}

    # Format the query_result dictionary as a pretty JSON block to embed in the prompt
    query_result_json = json.dumps(query_result, indent=2,default=str)

    prompt = f"""
User Question: {question}

You MUST hardcode the following query_result variable at the top of your Python script:
query_result = {query_result_json}

Reconstruct the DataFrame from query_result and generate the requested Plotly chart. Write ONLY raw Python code.
"""

    messages = [
        SystemMessage(content=VISUALIZATION_GENERATOR_SYSTEM_PROMPT),
        HumanMessage(content=prompt)
    ]

    # Inject failure history if we are retrying visualization generation
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

    try:
        llm = get_llm(temperature=0.0) # 0.0 temperature for deterministic code generation
        response = llm.invoke(messages)
        code = response.content.strip()

        # Clean markdown code blocks (e.g. ```python)
        if code.startswith("```"):
            lines = code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            code = "\n".join(lines).strip()

        logger.info("Generated Python Plotly visualization code successfully.")
        return {"vis_generated_code": code}
    except Exception as e:
        logger.error(f"Error in Visualization Generator Node: {e}")
        return {"vis_generated_code": ""}
