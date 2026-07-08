import time
import logging
from typing import Dict, Any
from backend.agents.state import AgentState
from backend.agents.sandbox import run_python_in_sandbox
from backend.mcp.data_access import run_query

logger = logging.getLogger(__name__)

def sandbox_executor_node(state: AgentState) -> Dict[str, Any]:
    """
    Executes the generated SQL query or Python code and records the execution metadata.
    """
    node_name = "sandbox_executor"
    start_time = time.time()
    retry_count = state.get("retry_count", 0)
    
    logger.info(f"Node started: {node_name} (Retry count: {retry_count})")
    
    session_id = state.get("session_id")
    dataset_id = state.get("dataset_id")
    plan = state.get("plan") or {}
    code = state.get("generated_code")
    approach = plan.get("approach", "sql")
    
    status = "success"
    error_msg = None
    updates = {}

    if not code:
        logger.warning("No code generated to execute.")
        status = "failed"
        error_msg = "No code was generated."
        updates = {
            "execution_success": False,
            "execution_time_ms": 0.0,
            "output_summary": {"error": error_msg}
        }
    else:
        logger.info(f"Running Sandbox Executor Node for {approach.upper()} (Session: {session_id})")
        
        if approach == "sql":
            # Execute query directly in DuckDB/Postgres
            result = run_query(session_id, dataset_id, code)
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000

            if result.get("success"):
                # Prepare lightweight summary of the result set
                rows = result.get("rows", [])
                output_summary = {
                    "columns": result.get("columns", []),
                    "row_count": result.get("row_count", 0),
                    "preview": rows[:5]  # Store top 5 rows only for display/semantic validation
                }
                logger.info(f"SQL execution succeeded. Rows: {len(rows)}, Time: {execution_time_ms:.2f}ms")
                updates = {
                    "execution_success": True,
                    "execution_time_ms": execution_time_ms,
                    "output_summary": output_summary,
                    "query_result": {
                        "columns": result.get("columns", []),
                        "rows": rows,
                        "row_count": result.get("row_count", 0)
                    },
                    "failure_summary": None
                }
            else:
                logger.warning(f"SQL execution failed: {result.get('error')}")
                status = "failed"
                error_msg = result.get("error")
                updates = {
                    "execution_success": False,
                    "execution_time_ms": execution_time_ms,
                    "output_summary": {"error": error_msg, "code_context": code},
                    "failure_summary": None
                }
                
        else:
            # Execute Python code in subprocess sandbox
            success, run_err, outputs = run_python_in_sandbox(session_id, dataset_id, code)
            end_time = time.time()
            execution_time_ms = (end_time - start_time) * 1000

            if success:
                logger.info(f"Python execution succeeded. Time: {execution_time_ms:.2f}ms")
                updates = {
                    "execution_success": True,
                    "execution_time_ms": execution_time_ms,
                    "output_summary": outputs,  # Contains chart_json, pdf_path etc.
                    "failure_summary": None
                }
            else:
                logger.warning(f"Python execution failed: {run_err}")
                status = "failed"
                error_msg = run_err
                updates = {
                    "execution_success": False,
                    "execution_time_ms": execution_time_ms,
                    "output_summary": {"error": error_msg, "code_context": code},
                    "failure_summary": None
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
    
    return updates
