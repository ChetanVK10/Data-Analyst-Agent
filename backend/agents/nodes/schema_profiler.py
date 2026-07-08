import time
import logging
from typing import Dict, Any
from backend.agents.state import AgentState
from backend.mcp.data_access import get_schema

logger = logging.getLogger(__name__)

def schema_profiler_node(state: AgentState) -> Dict[str, Any]:
    """
    Profiles the dataset schema (columns, types, row count) if not already done.
    """
    node_name = "schema_profiler"
    start_time = time.time()
    retry_count = state.get("retry_count", 0)
    
    logger.info(f"Node started: {node_name} (Retry count: {retry_count})")
    
    session_id = state.get("session_id")
    dataset_id = state.get("dataset_id")
    schema_profile = state.get("schema_profile")
    
    status = "success"
    error_msg = None
    updates = {}

    if schema_profile and len(schema_profile) > 0:
        logger.info(f"Schema profile already cached for session {session_id}, skipping profiling.")
    else:
        logger.info(f"Profiling schema for session {session_id}, dataset {dataset_id}...")
        try:
            profile = get_schema(session_id, dataset_id)
            logger.info(f"Schema profiled successfully. Columns: {[c['name'] for c in profile['columns']]}, Rows: {profile['row_count']}")
            updates["schema_profile"] = profile
        except Exception as e:
            logger.error(f"Error in schema_profiler_node: {e}")
            status = "failed"
            error_msg = str(e)
            # Return empty schema so down-stream planner handles the error state or asks for clarification
            updates["schema_profile"] = {"error": str(e), "columns": [], "row_count": 0}

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
    
    worker_result = {
        "worker_name": "SCHEMA",
        "status": status,
        "confidence": 1.0,
        "summary": "Successfully extracted schema." if status == "success" else error_msg,
        "routing_hint": None,
        "duration_ms": duration_ms
    }
    updates["last_worker_result"] = worker_result
    
    return updates
