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
    node_name = "visualization_executor"
    start_time = time.time()
    vis_retry_count = state.get("vis_retry_count", 0)
    
    logger.info(f"Node started: {node_name} (Retry count: {vis_retry_count})")
    
    session_id = state.get("session_id")
    dataset_id = state.get("dataset_id")
    code = state.get("vis_generated_code")
    
    status = "success"
    error_msg = None
    updates = {}

    if not code:
        logger.warning("No visualization code generated to execute.")
        status = "failed"
        error_msg = "No visualization code was generated."
        updates = {
            "execution_success": False,
            "output_summary": {"error": error_msg}
        }
    else:
        logger.info(f"Running Visualization Executor Node (Session: {session_id})")
        
        success, run_err, outputs = run_python_in_sandbox(session_id, dataset_id, code)
        end_time = time.time()
        execution_time_ms = (end_time - start_time) * 1000

        if success:
            logger.info(f"Visualization Python execution succeeded. Time: {execution_time_ms:.2f}ms")
            
            # Merge the chart_json into output_summary so Validator and Report Agent can read it
            output_summary = dict(state.get("output_summary") or {})
            output_summary["chart_json"] = outputs.get("chart_json")
            if outputs.get("pdf_path"):
                output_summary["pdf_path"] = outputs.get("pdf_path")
                
            updates = {
                "execution_success": True,
                "output_summary": output_summary,
                "failure_summary": None
            }
        else:
            logger.warning(f"Visualization Python execution failed: {run_err}")
            status = "failed"
            error_msg = run_err
            updates = {
                "execution_success": False,
                "output_summary": {"error": error_msg, "code_context": code},
                "failure_summary": {
                    "failure_type": "visualization",
                    "error_message": error_msg,
                    "code_context": code,
                    "expected_vs_actual": "Failed to generate Plotly chart configuration JSON."
                }
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
        "retry_count": vis_retry_count,
        "error_message": error_msg
    }
    
    execution_metadata = list(state.get("execution_metadata") or [])
    execution_metadata.append(node_metadata)
    updates["execution_metadata"] = execution_metadata
    
    return updates
