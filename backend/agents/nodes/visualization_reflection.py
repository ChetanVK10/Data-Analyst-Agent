import logging
from typing import Dict, Any
from backend.agents.state import AgentState

logger = logging.getLogger(__name__)

def visualization_reflection_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates if the visualization was generated successfully.
    Schedules retries for visualization_generator if needed.
    """
    execution_success = state.get("execution_success", False)
    failure_summary = state.get("failure_summary")
    vis_retry_count = state.get("vis_retry_count", 0)
    vis_retry_history = list(state.get("vis_retry_history", []))
    output_summary = state.get("output_summary") or {}
    chart_json = output_summary.get("chart_json")

    logger.info(f"Running Visualization Reflection. Success: {execution_success}, Chart JSON: {chart_json is not None}, Retry: {vis_retry_count}/3")

    # Move all Plotly validation here. Verify:
    # - chart.json exists (chart_json is not None)
    # - chart_json is not empty (is a dictionary and contains data traces)
    # - serialization succeeded (execution_success is True)
    chart_valid = False
    if chart_json and isinstance(chart_json, dict):
        if "data" in chart_json and len(chart_json["data"]) > 0:
            chart_valid = True

    if execution_success and chart_valid:
        logger.info("Plotly chart generated and validated successfully. Proceeding to report agent.")
        return {
            "retry_target": "report_agent",
            "graceful_failure": False
        }

    # Hard cap of 3 visualization retries reached
    if vis_retry_count >= 3:
        logger.warning("Hard retry limit of 3 reached for visualization. Proceeding to report agent.")
        if failure_summary:
            vis_retry_history.append(failure_summary)
        return {
            "retry_target": "report_agent",
            "graceful_failure": True,
            "vis_retry_history": vis_retry_history
        }

    # Prepare retry routing logic
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
            failure_summary = {
                "failure_type": "visualization",
                "error_message": "chart.json is missing or empty.",
                "code_context": state.get("vis_generated_code") or "",
                "expected_vs_actual": "Expected: chart.json file generated. Actual: File not found in session scratch."
            }
        else:
            failure_summary = {
                "failure_type": "visualization",
                "error_message": "Plotly chart JSON is invalid or missing traces.",
                "code_context": state.get("vis_generated_code") or "",
                "expected_vs_actual": f"Expected: Plotly JSON with traces in 'data'. Actual: {list(chart_json.keys())}"
            }

    vis_retry_history.append(failure_summary)
    new_vis_retry_count = vis_retry_count + 1

    logger.info(f"Retrying visualization. Attempt {new_vis_retry_count}/3 -> Routing to 'visualization_generator'")
    
    return {
        "vis_retry_count": new_vis_retry_count,
        "retry_target": "visualization_generator",
        "vis_retry_history": vis_retry_history,
        "graceful_failure": False
    }
