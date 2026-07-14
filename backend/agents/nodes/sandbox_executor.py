import time
import logging
from typing import Dict, Any
from backend.agents.state import AgentState, get_effective_question
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
            from backend.services.sql.sql_quality_validator import validate_sql
            
            # Fetch schema for validation
            schema = state.get("schema_profile", {})
            question = get_effective_question(state)
            
            validation = validate_sql(code, schema, question)
            
            if not validation["is_valid"]:
                end_time = time.time()
                execution_time_ms = (end_time - start_time) * 1000
                logger.warning(f"SQL execution prevented by quality validator: {validation['diagnostics']}")
                status = "failed"
                error_msg = validation["diagnostics"]
                updates = {
                    "execution_success": False,
                    "execution_time_ms": execution_time_ms,
                    "output_summary": {"error": error_msg, "code_context": code},
                    "failure_summary": None
                }
            else:
                if validation["warnings"]:
                    logger.info(f"SQL quality warnings: {validation['warnings']}")
                
                # Execute query directly in DuckDB/Postgres
                result = run_query(session_id, dataset_id, code)
                end_time = time.time()
                execution_time_ms = (end_time - start_time) * 1000

                if result.get("success"):
                    # Prepare lightweight summary of the result set
                    rows = result.get("rows", [])
                    columns = result.get("columns", [])
                    
                    def map_semantic_type(val):
                        import datetime
                        if val is None:
                            return "unknown"
                        if isinstance(val, bool):
                            return "boolean"
                        if isinstance(val, (int, float)):
                            return "number"
                        if isinstance(val, (datetime.date, datetime.datetime)):
                            return "datetime"
                        if isinstance(val, str):
                            return "string"
                        return "unknown"

                    dtypes = {}
                    for col in columns:
                        val = next((r.get(col) for r in rows if r.get(col) is not None), None)
                        dtypes[col] = map_semantic_type(val)
                        
                    output_summary = {
                        "columns": columns,
                        "row_count": result.get("row_count", 0),
                        "preview": rows[:5]  # Store top 5 rows only for display/semantic validation
                    }
                    logger.info(f"SQL execution succeeded. Rows: {len(rows)}, Time: {execution_time_ms:.2f}ms")
                    
                    from backend.utils.analytical_roles import infer_analytical_roles
                    roles = infer_analytical_roles(columns, dtypes)
                    
                    updates = {
                        "execution_success": True,
                        "execution_time_ms": execution_time_ms,
                        "output_summary": output_summary,
                        "query_result": {
                            "columns": columns,
                            "dtypes": dtypes,
                            "rows": rows,
                            "row_count": result.get("row_count", 0),
                            "analytical_roles": roles
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
            # 1. AST Validation
            from backend.services.python.python_quality_validator import validate_python_code
            is_ast_valid, ast_err = validate_python_code(code)
            
            # 2. Required Columns Validation
            schema = state.get("schema_profile", {})
            valid_columns = [col["name"].lower() for col in schema.get("columns", [])]
            plan = state.get("plan", {})
            required_cols = plan.get("required_columns", [])
            
            col_err = None
            for col in required_cols:
                if col.lower() not in valid_columns:
                    col_err = f"Column Validation Error: Required column '{col}' does not exist in the dataset schema."
                    break

            if not is_ast_valid:
                logger.warning(f"Python execution prevented by AST quality validator: {ast_err}")
                status = "failed"
                error_msg = ast_err
                updates = {
                    "execution_success": False,
                    "execution_time_ms": 0.0,
                    "output_summary": {"error": error_msg, "code_context": code},
                    "failure_summary": {
                        "failure_type": "structural",
                        "error_message": error_msg,
                        "code_context": code,
                        "expected_vs_actual": "AST quality validator failed verification check."
                    }
                }
            elif col_err:
                logger.warning(f"Python execution prevented by schema column validator: {col_err}")
                status = "failed"
                error_msg = col_err
                updates = {
                    "execution_success": False,
                    "execution_time_ms": 0.0,
                    "output_summary": {"error": error_msg, "code_context": code},
                    "failure_summary": {
                        "failure_type": "semantic",
                        "error_message": error_msg,
                        "code_context": code,
                        "expected_vs_actual": f"Expected columns: {required_cols}. Actual columns available: {[c['name'] for c in schema.get('columns', [])]}"
                    }
                }
            else:
                # Wrap generated Python code with context envelope to load `df` and serialize `result`
                wrapped_code = f"""import pandas as pd
import numpy as np
import re
import json
import math
import statistics
import datetime
import collections

# Load dataset
df = pd.read_csv("{dataset_id}.csv")

# Initialize result variable
result = None

# USER GENERATED CODE START
{code}
# USER GENERATED CODE END

# Output serialization helper
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            if type(obj.index) is not pd.RangeIndex:
                obj = obj.reset_index()
            def map_pd_dtype(dt_obj):
                kind = dt_obj.kind
                if kind in ('i', 'u', 'f', 'c'): return "number"
                elif kind == 'b': return "boolean"
                elif kind == 'M': return "datetime"
                elif kind in ('O', 'S', 'U'): return "string"
                return "unknown"
            dtypes_dict = {{str(k): map_pd_dtype(v) for k, v in obj.dtypes.items()}}
            # Replace NaNs with None to avoid JSON serialization issues
            safe_df = obj.replace({{np.nan: None}})
            return {{"type": "dataframe", "columns": list(obj.columns), "dtypes": dtypes_dict, "rows": safe_df.to_dict(orient="records")}}
        if isinstance(obj, pd.Series):
            safe_series = obj.replace({{np.nan: None}})
            return {{"type": "series", "name": obj.name, "data": safe_series.to_list()}}
        if hasattr(obj, "item"): # numpy types
            return obj.item()
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)

# Save result to json
with open("result.json", "w") as f:
    json.dump({{"result": result}}, f, cls=CustomEncoder)
"""
                # Execute Python code in subprocess sandbox
                success, run_err, outputs = run_python_in_sandbox(session_id, dataset_id, wrapped_code)
                end_time = time.time()
                execution_time_ms = (end_time - start_time) * 1000

                if success:
                    logger.info(f"Python execution succeeded. Time: {execution_time_ms:.2f}ms")
                    updates = {
                        "execution_success": True,
                        "execution_time_ms": execution_time_ms,
                        "output_summary": outputs,  # Contains chart_json, pdf_path, result_data etc.
                        "failure_summary": None
                    }
                    
                    # Convert python analysis results into standardized query_result formats
                    from backend.utils.analytical_roles import infer_analytical_roles
                    
                    result_data = outputs.get("result_data")
                    if isinstance(result_data, dict) and result_data.get("type") == "dataframe":
                        columns = result_data.get("columns", [])
                        dtypes = result_data.get("dtypes", {})
                        roles = infer_analytical_roles(columns, dtypes)
                        updates["query_result"] = {
                            "columns": columns,
                            "dtypes": dtypes,
                            "rows": result_data.get("rows", []),
                            "row_count": len(result_data.get("rows", [])),
                            "analytical_roles": roles
                        }
                    elif isinstance(result_data, dict) and result_data.get("type") == "series":
                        name = result_data.get("name") or "value"
                        data = result_data.get("data", [])
                        columns = ["index", name]
                        dtypes = {"index": "number", name: "unknown"}
                        roles = infer_analytical_roles(columns, dtypes)
                        updates["query_result"] = {
                            "columns": columns,
                            "dtypes": dtypes, # Series fallback
                            "rows": [[idx, val] for idx, val in enumerate(data)],
                            "row_count": len(data),
                            "analytical_roles": roles
                        }
                    elif result_data is not None:
                        columns = ["result"]
                        dtypes = {"result": "unknown"}
                        roles = infer_analytical_roles(columns, dtypes)
                        updates["query_result"] = {
                            "columns": columns,
                            "dtypes": dtypes,
                            "rows": [[result_data]],
                            "row_count": 1,
                            "analytical_roles": roles
                        }
                else:
                    logger.warning(f"Python execution failed: {run_err}")
                    status = "failed"
                    error_msg = run_err
                    updates = {
                        "execution_success": False,
                        "execution_time_ms": execution_time_ms,
                        "output_summary": {"error": error_msg, "code_context": code},
                        "failure_summary": {
                            "failure_type": "runtime",
                            "error_message": error_msg,
                            "code_context": code,
                            "expected_vs_actual": "Subprocess execution crashed or timed out."
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
        "retry_count": retry_count,
        "error_message": error_msg
    }
    
    execution_metadata = list(state.get("execution_metadata") or [])
    execution_metadata.append(node_metadata)
    updates["execution_metadata"] = execution_metadata
    
    return updates
