import json
import logging
import time
from typing import Dict, Any
from backend.agents.state import AgentState, get_effective_question
from backend.config import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

PYTHON_ANALYST_SYSTEM_PROMPT = """You are the Lead Python Analyst Worker for the Autonomous Data Analyst Agent.
Your job is to generate a structured analysis plan and self-contained Python analysis code to solve the user's question.

CRITICAL CODE CONTRACT RULES:
1. INPUT: A Pandas DataFrame named `df` representing the full dataset is pre-loaded and available in the execution environment.
2. OUTPUT: You MUST assign your final calculated output to a variable named `result`.
3. DATA LOADING: Do NOT attempt to load any CSV, read any files, search directories, or write loading logic (no `pd.read_csv`). Assume `df` is already in scope.
4. PACKAGES: Only import and use the following whitelisted modules: `pandas`, `numpy`, `math`, `statistics`, `re`, `json`, `datetime`, `collections`.
5. FORBIDDEN: Do NOT import `os`, `sys`, `subprocess`, `socket`, `shutil`, `multiprocessing`. Do NOT call `exec()`, `eval()`, `globals()`, `locals()`, or `__import__()`.
6. OPERATION CONSTRAINTS: Write focused, high-quality pandas transformations. Do not build UI templates, plot graphs, or write markdown output.
7. ANALYTICAL RESULT CONTRACT: The final DataFrame assigned to `result` MUST be a self-describing analytical table. Do NOT return just a derived metric (e.g., a single column of moving averages). You MUST preserve the contextual dimensions (e.g., identifiers, temporal dates/months, categorical groupings) alongside the derived metric. For time-series or over-time analysis, you MUST expose a single chronologically sortable temporal dimension (e.g., a proper Date or Timestamp column) rather than keeping year and month split, if the source data provides enough temporal information.

You must output ONLY a valid JSON object matching exactly this schema:
{{
  "plan": {{
    "approach": "python",
    "strategy_summary": "<Short, 1-sentence operational explanation of what this script computes for logs/debugging>",
    "required_columns": ["col1", "col2"], // list of exact column names in the schema that your script reads
    "confidence": 0.95, // self-reported confidence score (0.0 to 1.0)
    "expected_output": "dataframe" | "series" | "scalar" | "dict" | "list"
  }},
  "generated_code": "<Raw python code operating on 'df' and writing to 'result'. Lines should end with proper newlines. Use single quotes or double quotes carefully inside JSON. No markdown wrappers or explanation.>"
}}
"""

def python_analyst_node(state: AgentState) -> Dict[str, Any]:
    """
    Generates structured metadata and Python code in one LLM call.
    """
    node_name = "python_analyst"
    start_time = time.time()
    retry_count = state.get("retry_count", 0)
    
    logger.info(f"Node started: {node_name} (Retry count: {retry_count})")
    
    question = get_effective_question(state)
    schema_profile = state.get("schema_profile") or {}
    dataset_id = state.get("dataset_id")
    table_name = state.get("duckdb_table") or dataset_id
    retry_history = state.get("retry_history", [])
    
    status = "success"
    error_msg = None
    
    # Build schema description
    columns_desc = ""
    for col in schema_profile.get("columns", []):
        samples = col.get("sample_values", [])
        samples_str = f" | Samples: {samples}" if samples else ""
        columns_desc += f"- {col['name']} ({col['dtype']}){samples_str}\n"
    schema_context = f"Table: {table_name}\nColumns:\n{columns_desc}"
    
    messages = [
        SystemMessage(content=PYTHON_ANALYST_SYSTEM_PROMPT),
        HumanMessage(content=f"Dataset Schema:\n{schema_context}\n\nUser Question:\n{question}")
    ]
    
    # Inject retry history if we failed previously
    python_failures = [f for f in retry_history if f.get("failure_type") in ["runtime", "structural", "timeout"]]
    if python_failures:
        logger.info(f"Injecting python execution failure history into Analyst context.")
        failures_context = "\n---\n".join([
            f"Attempt {i+1} Failure:\n"
            f"- Error Message: {f['error_message']}\n"
            f"- Code Executed:\n{f.get('code_context', '')}\n"
            f"- Details: {f.get('expected_vs_actual', '')}"
            for i, f in enumerate(python_failures)
        ])
        messages.append(HumanMessage(
            content=f"ATTENTION: Previous code execution attempts failed. Please review the failures and correct your code:\n{failures_context}"
        ))
        
    try:
        llm = get_llm(temperature=0.0)
        response = llm.invoke(messages)
        content = response.content.strip()
        
        # Clean markdown code fences if LLM accidentally emitted them
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        output_data = json.loads(content, strict=False)
        plan = output_data.get("plan", {})
        generated_code = output_data.get("generated_code", "")
        
        logger.info(f"Generated Python plan: {plan.get('strategy_summary')}")
        
        return {
            "plan": plan,
            "expected_output_type": plan.get("expected_output"),
            "generated_code": generated_code,
            "execution_success": False, # Reset execution status for the next node
            "execution_metadata": list(state.get("execution_metadata") or []) + [{
                "node_name": node_name,
                "start_time": start_time,
                "end_time": time.time(),
                "duration_ms": (time.time() - start_time) * 1000,
                "status": "success",
                "retry_count": retry_count,
                "error_message": None
            }]
        }
    except Exception as e:
        logger.error(f"Error in Python Analyst Node: {e}")
        # Default plan to allow progression and fail at validator/reflection
        fallback_plan = {
            "approach": "python",
            "strategy_summary": "Fallback empty plan due to analyst crash.",
            "required_columns": [],
            "confidence": 0.0,
            "expected_output": "dataframe"
        }
        return {
            "plan": fallback_plan,
            "expected_output_type": "dataframe",
            "generated_code": "",
            "execution_success": False,
            "execution_metadata": list(state.get("execution_metadata") or []) + [{
                "node_name": node_name,
                "start_time": start_time,
                "end_time": time.time(),
                "duration_ms": (time.time() - start_time) * 1000,
                "status": "failed",
                "retry_count": retry_count,
                "error_message": str(e)
            }]
        }
