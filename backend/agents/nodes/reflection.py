import logging
from typing import Dict, Any
from backend.agents.state import AgentState

logger = logging.getLogger(__name__)

def reflection_node(state: AgentState) -> Dict[str, Any]:
    """
    Decides whether to retry, what node to route to, increments the retry counter,
    and appends the failure to the history.
    """
    import time
    node_name = "reflection"
    start_time = time.time()
    retry_count = state.get("retry_count", 0)
    
    logger.info(f"Node started: {node_name} (Retry count: {retry_count})")
    
    validation_passed = state.get("validation_passed", False)
    failure_summary = state.get("failure_summary")
    retry_history = list(state.get("retry_history", []))
    
    status = "success"
    error_msg = None
    updates = {}

    # Success case
    if validation_passed:
        if state.get("expected_output_type") == "chart":
            logger.info("Validation passed. Hinting VISUALIZATION.")
            routing_hint = "VISUALIZATION"
        else:
            logger.info("Validation passed. Hinting REPORT.")
            routing_hint = "REPORT"

    # Hard cap of 3 retries reached
    elif retry_count >= 3:
        logger.warning("Hard retry limit of 3 reached. Graceful degradation to REPORT.")
        if failure_summary:
            retry_history.append(failure_summary)
        status = "failed"
        error_msg = "Hard retry limit of 3 reached."
        routing_hint = "REPORT"
        updates = {
            "graceful_failure": True,
            "retry_history": retry_history
        }

    # Prepare retry routing logic
    else:
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
        
        if failure_type == "provider_error":
            logger.warning("Provider chain exhausted due to rate limit. Skipping agent retry loop.")
            status = "failed"
            error_msg = failure_summary.get("error_message")
            routing_hint = "REPORT"
            updates = {
                "graceful_failure": True,
                "retry_history": retry_history
            }
        else:
            approach = state.get("plan", {}).get("approach", "sql")
            
            if approach == "python":
                logger.info(f"Retrying Python Analysis capability. Attempt {new_retry_count}/3. Failure type '{failure_type}'")
                status = "failed"
                error_msg = failure_summary.get("error_message")
                routing_hint = "PYTHON_ANALYSIS"
            else:
                logger.info(f"Retrying SQL capability. Attempt {new_retry_count}/3. Failure type '{failure_type}'")
                status = "failed"
                error_msg = failure_summary.get("error_message")
                routing_hint = "SQL"
                
            updates = {
                "retry_count": new_retry_count,
                "retry_history": retry_history,
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
        "retry_count": retry_count,
        "error_message": error_msg
    }
    
    execution_metadata = list(state.get("execution_metadata") or [])
    execution_metadata.append(node_metadata)
    updates["execution_metadata"] = execution_metadata
    
    approach = state.get("plan", {}).get("approach", "sql")
    worker_name = "PYTHON_ANALYSIS" if approach == "python" else "SQL"
    
    worker_result = {
        "worker_name": worker_name,
        "status": status,
        "confidence": 1.0 if status == "success" else 0.0,
        "summary": error_msg if error_msg else f"{worker_name} capability completed successfully.",
        "routing_hint": routing_hint,
        "duration_ms": duration_ms
    }
    updates["last_worker_result"] = worker_result
    
    return updates
