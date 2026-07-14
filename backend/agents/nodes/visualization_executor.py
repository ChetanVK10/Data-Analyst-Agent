import time
import logging
import pandas as pd
from typing import Dict, Any
from backend.agents.state import AgentState
from backend.agents.sandbox import run_python_in_sandbox
from backend.agents.schemas import VisualizationSpec, ChartType
from backend.services.visualization.selector import select_best_chart_type
from backend.services.visualization.validator import validate_data_requirements
from backend.services.visualization.templates import render_chart

def validate_chart_spec(vis_spec: VisualizationSpec, columns: list, dtypes: dict, rows: list) -> tuple[bool, str, bool]:
    """
    Returns (is_valid, error_msg, is_no_visualization)
    """
    if not vis_spec.is_appropriate:
        return False, "Visualization explicitly marked as not appropriate.", True
        
    if len(columns) == 1 and len(rows) == 1:
        return False, "Result is a single scalar value, cannot be visualized.", True
        
    if len(columns) == 1 and dtypes.get(columns[0]) != "number" and vis_spec.chart_type != ChartType.OTHER:
        return False, "Result is a single non-numeric column, cannot be visualized.", True

    chart_type = vis_spec.chart_type
    if not chart_type:
        return False, "Chart type is required.", False
        
    def check_col(col):
        if col and col not in columns:
            return False, f"Referenced column '{col}' does not exist in query result."
        return True, ""
        
    x = vis_spec.x_column
    y = vis_spec.y_column
    y_cols = vis_spec.y_columns or ([y] if y else [])
    
    # Check existence of referenced columns
    for c in [x, vis_spec.color_column]:
        ok, err = check_col(c)
        if not ok: return False, err, False
    for c in y_cols:
        ok, err = check_col(c)
        if not ok: return False, err, False

    if chart_type == ChartType.BAR:
        if y and dtypes.get(y) != "number":
            return False, f"Y-axis column '{y}' must be numeric for bar chart.", False
        if not y:
            return False, f"Y-axis is required for bar chart.", False
            
    elif chart_type == ChartType.AREA:
        if not y_cols:
            return False, f"Y-axis is required for area chart.", False
        for yc in y_cols:
            if dtypes.get(yc) != "number":
                return False, f"Y-axis column '{yc}' must be numeric for area chart.", False
            
    elif chart_type == ChartType.LINE:
        if not y_cols:
            return False, f"Y-axis is required for line chart.", False
        for yc in y_cols:
            if dtypes.get(yc) != "number":
                return False, f"Y-axis column '{yc}' must be numeric for line chart.", False
            
    elif chart_type == ChartType.SCATTER:
        if x and dtypes.get(x) != "number":
            return False, f"X-axis column '{x}' must be numeric for scatter chart.", False
        if y and dtypes.get(y) != "number":
            return False, f"Y-axis column '{y}' must be numeric for scatter chart.", False
        if not x or not y:
            return False, f"Both X and Y axes are required for scatter chart.", False
            
    elif chart_type == ChartType.PIE:
        if y and dtypes.get(y) != "number":
            return False, f"Value column '{y}' must be numeric for pie chart.", False
        if not y:
            return False, f"Value column (y_column) is required for pie chart.", False
            
    elif chart_type == ChartType.HISTOGRAM:
        if x and dtypes.get(x) != "number":
            return False, f"Value column '{x}' must be numeric for histogram.", False
        if not x:
            return False, f"Value column (x_column) is required for histogram.", False

    return True, "", False

logger = logging.getLogger(__name__)

def visualization_executor_node(state: AgentState) -> Dict[str, Any]:
    """
    Renders the visualization using the Visualization Template Library.
    Falls back to sandbox execution for custom/unsupported types.
    """
    node_name = "visualization_executor"
    start_time = time.time()
    vis_retry_count = state.get("vis_retry_count", 0)
    
    logger.info(f"Node started: {node_name} (Retry count: {vis_retry_count})")
    
    session_id = state.get("session_id")
    dataset_id = state.get("dataset_id")
    query_result = state.get("query_result")
    vis_spec_data = state.get("vis_spec")
    code = state.get("vis_generated_code")
    
    status = "success"
    error_msg = None
    updates = {}

    if not vis_spec_data and not code:
        logger.warning("No visualization spec or code generated to execute.")
        status = "failed"
        error_msg = "No visualization specification was generated."
        updates = {
            "execution_success": False,
            "output_summary": {"error": error_msg}
        }
    else:
        logger.info(f"Running Visualization Executor Node (Session: {session_id})")
        
        chart_json = None
        success = False
        run_err = None
        
        # Determine execution path
        use_template_engine = False
        vis_spec = None
        
        if vis_spec_data and query_result:
            try:
                vis_spec = VisualizationSpec(**vis_spec_data)
                
                import json
                from backend.mcp.client import invoke_mcp_tool_sync
                query_metadata = {
                    "columns": query_result.get("columns", []),
                    "row_count": len(query_result.get("rows", [])),
                    "analytical_roles": query_result.get("analytical_roles", {})
                }
                mcp_res = invoke_mcp_tool_sync("is_result_chartable", {"query_metadata_json": json.dumps(query_metadata)})
                if mcp_res is not None and not mcp_res.get("error"):
                    is_chartable_flag = mcp_res.get("is_chartable", True)
                    logger.info("Checked chartability via MCP tool.")
                else:
                    logger.warning("MCP is_result_chartable failed. Falling back to internal function.")
                    from backend.services.visualization.validator import is_result_chartable
                    is_chartable_flag = is_result_chartable(query_result)
                
                if not is_chartable_flag:
                    logger.info("Deterministic no_visualization: Result is not structurally chartable according to MCP/validator.")
                    success = True
                    chart_json = None
                    vis_spec.is_appropriate = False
                    is_no_vis = True
                    is_valid_spec = False
                    spec_err = "Not chartable."
                else:
                    is_valid_spec, spec_err, is_no_vis = validate_chart_spec(
                        vis_spec, 
                        query_result.get("columns", []), 
                        query_result.get("dtypes", {}), 
                        query_result.get("rows", [])
                    )
                
                if is_no_vis:
                    logger.info(f"Deterministic no_visualization: {spec_err}")
                    success = True
                    chart_json = None
                    vis_spec.is_appropriate = False
                elif not is_valid_spec:
                    logger.warning(f"Deterministic spec validation failed: {spec_err}")
                    run_err = spec_err
                elif vis_spec.chart_type and vis_spec.chart_type != ChartType.OTHER:
                    use_template_engine = True
            except Exception as e:
                logger.error(f"Failed to parse vis_spec_data: {e}")
                run_err = str(e)
                 
        if not success and use_template_engine and vis_spec:
            logger.info(f"Using deterministic template engine for {vis_spec.chart_type.value} chart.")
            try:
                df = pd.DataFrame(query_result.get("rows", []), columns=query_result.get("columns", []))
                
                # 1. Selector overrides
                selected_type = select_best_chart_type(vis_spec, df)
                
                # 2. Validator
                is_valid, val_err = validate_data_requirements(selected_type, vis_spec, df)
                if is_valid:
                    # 3. Render
                    chart_json = render_chart(selected_type, vis_spec, df)
                    if chart_json:
                        success = True
                    else:
                        run_err = "Template engine returned None."
                else:
                    run_err = f"Data validation failed: {val_err}"
            except Exception as e:
                logger.error(f"Template engine crashed: {e}")
                run_err = f"Template engine error: {e}"
 
        # Sandbox Fallback Path
        # Only attempt sandbox if visualization is appropriate and not already successful
        should_run_sandbox = not success and code and not run_err
        if vis_spec and not vis_spec.is_appropriate:
            should_run_sandbox = False
            
        if should_run_sandbox:
            logger.info("Falling back to Sandbox Execution path for custom visualization.")
            try:
                import json
                import os
                from backend.agents.sandbox import prepare_scratch_directory
                session_dir = prepare_scratch_directory(session_id, dataset_id)
                vis_data_path = os.path.join(session_dir, "vis_data.json")
                with open(vis_data_path, "w", encoding="utf-8") as f:
                    json.dump(query_result, f)
                    
                envelope = f"""import pandas as pd
import json

with open('vis_data.json', 'r') as f:
    data = json.load(f)
df = pd.DataFrame(data['rows'], columns=data['columns'])

{code}

if 'fig' in locals():
    with open('chart.json', 'w') as f:
        f.write(fig.to_json())
"""
                sandbox_success, sandbox_err, outputs = run_python_in_sandbox(session_id, dataset_id, envelope)
                
                if sandbox_success:
                    success = True
                    chart_json = outputs.get("chart_json")
                else:
                    run_err = sandbox_err
            except Exception as e:
                run_err = f"Failed to prepare sandbox execution: {e}"

        end_time = time.time()
        execution_time_ms = (end_time - start_time) * 1000

        is_skipped = vis_spec and not vis_spec.is_appropriate
        if success and (chart_json is not None or is_skipped):
            logger.info(f"Visualization generation succeeded. Time: {execution_time_ms:.2f}ms")
            
            from backend.utils.json_sanitizer import sanitize_for_json
            
            output_summary = dict(state.get("output_summary") or {})
            output_summary["chart_json"] = sanitize_for_json(chart_json)
                
            updates = {
                "execution_success": True,
                "output_summary": output_summary,
                "failure_summary": None
            }
        else:
            logger.warning(f"Visualization generation failed: {run_err}")
            status = "failed"
            error_msg = run_err or "Failed to generate visualization."
            updates = {
                "execution_success": False,
                "output_summary": {"error": error_msg, "code_context": code or str(vis_spec_data)},
                "failure_summary": {
                    "failure_type": "visualization",
                    "error_message": error_msg,
                    "code_context": code or str(vis_spec_data),
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
