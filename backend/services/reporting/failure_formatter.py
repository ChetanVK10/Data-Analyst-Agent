from typing import Dict, Any, List
from backend.agents.state import AgentState

def map_error_to_resolution(failure_type: str) -> str:
    """
    Deterministic mapping between backend error categories and generic recovery suggestions.
    """
    failure_type = failure_type.lower()
    
    if failure_type in ["structural", "syntax", "parser", "parser error"]:
        return "Review SQL syntax and identifier formatting."
    elif failure_type in ["semantic", "binder", "binder error"]:
        return "Verify table and column names exist and exactly match the schema."
    elif failure_type in ["timeout"]:
        return "Reduce query complexity or dataset size."
    elif failure_type in ["visualization"]:
        return "Review the visualization requirements and ensure the data matches the requested chart type."
    else:
        return "Review generated code or execution logs."

def map_error_to_summary(failure_type: str) -> str:
    """
    Deterministic human-readable explanation from the backend.
    """
    failure_type = failure_type.lower()
    
    if failure_type in ["structural", "syntax", "parser", "parser error"]:
        return "The SQL query could not be executed because a syntax error was detected."
    elif failure_type in ["semantic", "binder", "binder error"]:
        return "The query could not be executed because it referenced columns or tables that do not exist."
    elif failure_type in ["timeout"]:
        return "The execution was aborted because it exceeded the allowed time limit."
    elif failure_type in ["visualization"]:
        return "The visualization could not be generated from the returned data."
    else:
        return "The execution encountered an unexpected runtime error."

def determine_failure_location(state: AgentState) -> str:
    """
    Examines the execution metadata to attribute the failure to a specific worker.
    """
    # Prefer failure location from the last worker result if available
    last_worker_result = state.get("last_worker_result")
    if last_worker_result and last_worker_result.get("status") == "failed":
        worker = last_worker_result.get("worker_name", "")
        if worker:
            return f"{worker} Worker".title().replace(" Sql ", " SQL ").replace(" Sql", " SQL")

    # If graceful degradation was triggered, look at retry history
    retry_history = state.get("retry_history") or []
    if retry_history:
        last_fail = retry_history[-1]
        fail_type = last_fail.get("failure_type", "").lower()
        if fail_type == "visualization":
            return "Visualization Worker"
        elif fail_type in ["structural", "semantic"]:
            return "Validator"
        elif fail_type in ["timeout", "runtime"]:
            return "Sandbox Executor"
            
    return "Execution Pipeline"

def generate_failure_report(state: AgentState) -> Dict[str, Any]:
    """
    Consumes existing failure information from AgentState and produces 
    a structured failure response deterministically, bypassing the LLM.
    """
    session_id = state.get("session_id", "unknown")
    dataset_id = state.get("dataset_id", "unknown")
    question = state.get("question", "")
    code = state.get("generated_code") or ""
    plan_steps = state.get("plan", {}).get("steps", [])
    schema_profile = state.get("schema_profile") or {}
    
    # Extract failure history
    retry_history = state.get("retry_history") or []
    vis_retry_history = state.get("vis_retry_history") or []
    
    # Combine histories and get the last failure
    all_failures = retry_history + vis_retry_history
    last_failure = all_failures[-1] if all_failures else {}
    
    failure_type = last_failure.get("failure_type", "runtime")
    error_message = last_failure.get("error_message", "Unknown runtime exception occurred.")
    
    # Generate deterministic fields
    summary = map_error_to_summary(failure_type)
    resolution = map_error_to_resolution(failure_type)
    location = determine_failure_location(state)
    
    # ── Dataset context ──────────────────────────────────────────────────────
    columns_list = schema_profile.get("columns", [])
    dataset_info = {
        "name": dataset_id,
        "rows": schema_profile.get("row_count", 0),
        "columns": len(columns_list),
    }

    # Format the report using the API contract
    final_report = {
        "success": False,
        "dataset": dataset_info,
        "report": {
            "title": "Execution Failed",
            "report_type": "FAILURE",
            "executive_summary": {
                "headline": "System Failure Report",
                "summary": summary,
                "confidence": "Low"
            },
            "tables": [],
            "charts": [],
            "insights": [
                {
                    "title": "Failure Location",
                    "body": location
                },
                {
                    "title": "Technical Details",
                    "body": f"[{failure_type.upper()}] {error_message}"
                },
                {
                    "title": "Possible Resolution",
                    "body": resolution
                }
            ],
            "recommendations": []
        },
        "debug": {
            "generated_code": code or None,
            "execution_mode": state.get("plan", {}).get("approach", "DETERMINISTIC").upper(),
            "execution_plan": "\n".join(f"- {s}" for s in plan_steps) if plan_steps else None,
            "llm_reasoning": "Deterministic failure report generated. LLM bypassed."
        },
        "pdf_path": None,
    }
    
    return final_report
