import time
import logging
from typing import Dict, Any
from backend.agents.state import AgentState
from backend.agents.sandbox import run_python_in_sandbox

logger = logging.getLogger(__name__)

def visualization_executor_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes the generated Python visualization code inside the sandbox.
    Adds the resulting chart_json back into the output_summary.
    """
    session_id = state.get("session_id")
    dataset_id = state.get("dataset_id")
    code = state.get("vis_generated_code")

    if not code:
        logger.warning("No visualization code generated to execute.")
        return {
            "execution_success": False,
            "output_summary": {"error": "No visualization code was generated."}
        }

    logger.info(f"Running Visualization Executor Node (Session: {session_id})")
    
    start_time = time.time()
    success, error_msg, outputs = run_python_in_sandbox(session_id, dataset_id, code)
    end_time = time.time()
    execution_time_ms = (end_time - start_time) * 1000

    if success:
        logger.info(f"Visualization Python execution succeeded. Time: {execution_time_ms:.2f}ms")
        
        # Merge the chart_json into output_summary so Validator and Report Agent can read it
        output_summary = dict(state.get("output_summary") or {})
        output_summary["chart_json"] = outputs.get("chart_json")
        if outputs.get("pdf_path"):
            output_summary["pdf_path"] = outputs.get("pdf_path")
            
        return {
            "execution_success": True,
            "output_summary": output_summary,
            "failure_summary": None
        }
    else:
        logger.warning(f"Visualization Python execution failed: {error_msg}")
        return {
            "execution_success": False,
            "output_summary": {"error": error_msg, "code_context": code},
            "failure_summary": {
                "failure_type": "visualization",
                "error_message": error_msg,
                "code_context": code,
                "expected_vs_actual": "Failed to generate Plotly chart configuration JSON."
            }
        }
