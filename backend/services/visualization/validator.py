import logging
import pandas as pd
from typing import Tuple
from backend.agents.schemas import ChartType, VisualizationSpec

logger = logging.getLogger(__name__)

def validate_data_requirements(chart_type: ChartType, vis_spec: VisualizationSpec, df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Validates if the dataframe can support the requested chart type and mappings.
    Returns (is_valid, error_message).
    """
    if not vis_spec.is_appropriate:
        return False, "Visualization is not appropriate for this data according to LLM."

    if df.empty:
        return False, "The query result is empty. Cannot generate a visualization."

    x_col = vis_spec.x_column
    y_col = vis_spec.y_column
    y_cols = vis_spec.y_columns or ([y_col] if y_col else [])

    if chart_type in [ChartType.BAR, ChartType.LINE, ChartType.SCATTER, ChartType.AREA]:
        if not x_col or x_col not in df.columns:
            return False, f"Missing or invalid X-axis column '{x_col}' for {chart_type.value} chart."
        if not y_cols:
            return False, f"Missing Y-axis column(s) for {chart_type.value} chart."
            
        for yc in y_cols:
            if yc not in df.columns:
                return False, f"Missing or invalid Y-axis column '{yc}' for {chart_type.value} chart."
            # Check numeric compatibility for Y-axis
            if not pd.api.types.is_numeric_dtype(df[yc]):
                return False, f"Y-axis column '{yc}' must be numeric for {chart_type.value} chart."

    if chart_type == ChartType.PIE:
        if not x_col or x_col not in df.columns:
            return False, f"Missing or invalid label column '{x_col}' for pie chart."
        if not y_cols:
            return False, f"Missing Y-axis value column for pie chart."
        yc = y_cols[0]
        if yc not in df.columns:
            return False, f"Missing or invalid value column '{yc}' for pie chart."
        if not pd.api.types.is_numeric_dtype(df[yc]):
            return False, f"Value column '{yc}' must be numeric for pie chart."
        # Cannot have negative values in a pie chart typically, but let's just check numeric

    if chart_type == ChartType.HISTOGRAM:
        if not x_col or x_col not in df.columns:
            return False, f"Missing or invalid X-axis column '{x_col}' for histogram."
        if not pd.api.types.is_numeric_dtype(df[x_col]):
            return False, f"X-axis column '{x_col}' must be numeric for histogram."

    if getattr(chart_type, 'name', '') == 'BOX' or chart_type == 'box':
        if not y_cols:
            return False, f"Missing Y-axis column for box plot."
        for yc in y_cols:
            if yc not in df.columns:
                return False, f"Missing or invalid Y-axis column '{yc}' for box plot."
            if not pd.api.types.is_numeric_dtype(df[yc]):
                return False, f"Y-axis column '{yc}' must be numeric for box plot."

    # Validate color column if present
    color_col = vis_spec.color_column
    if color_col and color_col not in df.columns:
        logger.warning(f"Color column '{color_col}' not found in dataframe. Ignoring it.")
        # We won't hard fail for a missing color column, just ignore it in templates

    return True, ""

def is_result_chartable(query_result: dict) -> bool:
    """
    Deterministically evaluates if the query result is structurally chartable.
    Safely supports both full query results (containing 'rows') and lightweight metadata (containing 'row_count').
    """
    if not query_result or not isinstance(query_result, dict):
        return False
        
    rows = query_result.get("rows", [])
    row_count = query_result.get("row_count", len(rows) if isinstance(rows, list) else 0)
    if row_count == 0:
        return False
        
    # Single cell / single scalar check
    columns = query_result.get("columns", [])
    if row_count == 1 and len(columns) == 1:
        return False
        
    roles = query_result.get("analytical_roles", {})
    if not roles:
        # Fallback if no roles are available, checking physical types
        dtypes = query_result.get("dtypes", {})
        roles = {}
        for c in columns:
            dt = dtypes.get(c, "unknown")
            if dt == "number":
                roles[c] = "measure"
            elif dt == "datetime":
                roles[c] = "temporal"
            else:
                roles[c] = "categorical"
        
    # Count roles
    measures = [col for col, role in roles.items() if role in ("measure", "derived_measure")]
    temporals = [col for col, role in roles.items() if role == "temporal"]
    categoricals = [col for col, role in roles.items() if role == "categorical"]
    
    if not measures:
        return False
        
    if len(temporals) >= 1 or len(categoricals) >= 1:
        return True
        
    if len(measures) >= 2:
        return True
        
    if len(measures) == 1 and row_count > 1:
        return True
        
    return False

def validate_plotly_figure(fig_json: dict) -> Tuple[bool, str]:
    """
    Validates the generated Plotly JSON structure.
    Checks for empty traces and basic layout elements.
    """
    if not isinstance(fig_json, dict):
        return False, "Chart JSON is not a dictionary."
        
    data = fig_json.get("data", [])
    if not data or not isinstance(data, list):
        return False, "Chart JSON is missing data traces."
        
    # Check for empty traces
    has_data = False
    for trace in data:
        if "x" in trace and len(trace["x"]) > 0:
            has_data = True
        elif "labels" in trace and len(trace["labels"]) > 0: # Pie chart
            has_data = True
        elif "y" in trace and len(trace["y"]) > 0: # Box plot can have just y
            has_data = True
            
    if not has_data:
        return False, "All data traces are empty."

    layout = fig_json.get("layout", {})
    if not layout.get("title", {}).get("text"):
        return False, "Chart title is missing in the generated layout."

    return True, ""
