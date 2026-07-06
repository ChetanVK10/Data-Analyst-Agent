import logging
from typing import Dict, Any
from backend.agents.state import AgentState
from backend.mcp.data_access import get_schema

logger = logging.getLogger(__name__)

def schema_profiler_node(state: AgentState) -> Dict[str, Any]:
    """
    Profiles the dataset schema (columns, types, row count) if not already done.
    """
    session_id = state.get("session_id")
    dataset_id = state.get("dataset_id")
    schema_profile = state.get("schema_profile")

    if schema_profile and len(schema_profile) > 0:
        logger.info(f"Schema profile already cached for session {session_id}, skipping profiling.")
        return {}

    logger.info(f"Profiling schema for session {session_id}, dataset {dataset_id}...")
    try:
        profile = get_schema(session_id, dataset_id)
        logger.info(f"Schema profiled successfully. Columns: {[c['name'] for c in profile['columns']]}, Rows: {profile['row_count']}")
        return {"schema_profile": profile}
    except Exception as e:
        logger.error(f"Error in schema_profiler_node: {e}")
        # Return empty schema so down-stream planner handles the error state or asks for clarification
        return {"schema_profile": {"error": str(e), "columns": [], "row_count": 0}}
