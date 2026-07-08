import logging
from typing import Dict, Any
from backend.agents.state import AgentState

logger = logging.getLogger(__name__)

def visualization_reflection_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates if the visualization was generated successfully.
    Schedules retries for visualization_generator if needed.
    """
    import time
    node_name = "visualization_reflection"
    start_time = time.time()
    vis_retry_count = state.get("vis_retry_count", 0)
    
    logger.info(f"Node started: {node_name} (Retry count: {vis_retry_count})")
    
    execution_success = state.get("execution_success", False)
    failure_summary = state.get("failure_summary")
    vis_retry_history = list(state.get("vis_retry_history", []))
    output_summary = state.get("output_summary") or {}
    chart_json = output_summary.get("chart_json")
    
    status = "success"
    error_msg = None
    updates = {}

    # Move all Plotly validation here. Verify:
    # - chart.json exists (chart_json is not None)
    # - chart_json is not empty (is a dictionary and contains data traces)
    # - serialization succeeded (execution_success is True)
    chart_valid = False
    if chart_json and isinstance(chart_json, dict):
        if "data" in chart_json and len(chart_json["data"]) > 0:
            chart_valid = True

    if execution_success and chart_valid:
        logger.info("Plotly chart generated and validated successfully. Hinting REPORT.")
        routing_hint = "REPORT"

    # Hard cap of 3 visualization retries reached
    elif vis_retry_count >= 3:
        logger.warning("Hard retry limit of 3 reached for visualization. Graceful degradation to REPORT.")
        if failure_summary:
            vis_retry_history.append(failure_summary)
        status = "failed"
        error_msg = "Hard retry limit of 3 reached for visualization."
        routing_hint = "REPORT"
        updates = {
            "graceful_failure": True,
            "vis_retry_history": vis_retry_history
        }

    # Prepare retry routing logic
    else:
        if not failure_summary:
            if not execution_success:
                error_msg = output_summary.get("error", "Plotly execution crashed.")
                failure_summary = {
                    "failure_type": "visualization",
                    "error_message": error_msg,
                    "code_context": output_summary.get("code_context", state.get("vis_generated_code") or ""),
                    "expected_vs_actual": f"Expected: Successful Plotly run. Actual: Subprocess failed: {error_msg}"
                }
            elif not chart_json:
                error_msg = "chart.json is missing or empty."
                failure_summary = {
                    "failure_type": "visualization",
                    "error_message": error_msg,
                    "code_context": state.get("vis_generated_code") or "",
                    "expected_vs_actual": "Expected: chart.json file generated. Actual: File not found in session scratch."
                }
            else:
                error_msg = "Plotly chart JSON is invalid or missing traces."
                failure_summary = {
                    "failure_type": "visualization",
                    "error_message": error_msg,
                    "code_context": state.get("vis_generated_code") or "",
                    "expected_vs_actual": f"Expected: Plotly JSON with traces in 'data'. Actual: {list(chart_json.keys())}"
                }

        vis_retry_history.append(failure_summary)
        new_vis_retry_count = vis_retry_count + 1

        logger.info(f"Retrying visualization capability. Attempt {new_vis_retry_count}/3")
        status = "failed"
        if not error_msg:
            error_msg = failure_summary.get("error_message")
            
        routing_hint = "VISUALIZATION"
        updates = {
            "vis_retry_count": new_vis_retry_count,
            "vis_retry_history": vis_retry_history,
            "graceful_failure": False
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
    
    worker_result = {
        "worker_name": "VISUALIZATION",
        "status": status,
        "confidence": 1.0 if status == "success" else 0.0,
        "summary": error_msg if error_msg else "Visualization generated successfully.",
        "routing_hint": routing_hint,
        "duration_ms": duration_ms
    }
    updates["last_worker_result"] = worker_result
    
    return updates
