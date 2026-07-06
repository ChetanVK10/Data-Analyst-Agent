import logging
from typing import Dict, Any
from backend.agents.state import AgentState

logger = logging.getLogger(__name__)

def reflection_node(state: AgentState) -> Dict[str, Any]:
    """
    Decides whether to retry, what node to route to, increments the retry counter,
    and appends the failure to the history.
    """
    validation_passed = state.get("validation_passed", False)
    failure_summary = state.get("failure_summary")
    retry_count = state.get("retry_count", 0)
    retry_history = list(state.get("retry_history", []))

    logger.info(f"Running Reflection Node. Validation passed: {validation_passed}, Retry count: {retry_count}")

    # Success case
    if validation_passed:
        if state.get("expected_output_type") == "chart":
            logger.info("Validation passed. Routing to visualization generator.")
            return {
                "retry_target": "visualization_generator",
                "graceful_failure": False
            }
        else:
            logger.info("Validation passed. Routing to report agent.")
            return {
                "retry_target": "report_agent",
                "graceful_failure": False
            }

    # Hard cap of 3 retries reached
    if retry_count >= 3:
        logger.warning("Hard retry limit of 3 reached. Routing to report agent with graceful failure.")
        if failure_summary:
            retry_history.append(failure_summary)
        return {
            "retry_target": "report_agent",
            "graceful_failure": True,
            "retry_history": retry_history
        }

    # Prepare retry routing logic
    if not failure_summary:
        # Fallback if validation failed but no failure summary was created
        failure_summary = {
            "failure_type": "runtime",
            "error_message": "Validation failed with unspecified error.",
            "code_context": "",
            "expected_vs_actual": ""
        }

    retry_history.append(failure_summary)
    new_retry_count = retry_count + 1

    failure_type = failure_summary.get("failure_type")
    
    # Route logic:
    # - semantic -> back to planner
    # - runtime, structural, timeout, visualization -> back to code_generator
    if failure_type == "semantic":
        retry_target = "planner"
    else:
        retry_target = "code_generator"

    logger.info(f"Retrying. Attempt {new_retry_count}/3. Failure type '{failure_type}' -> Routing to '{retry_target}'")
    
    return {
        "retry_count": new_retry_count,
        "retry_target": retry_target,
        "retry_history": retry_history,
        "graceful_failure": False
    }
