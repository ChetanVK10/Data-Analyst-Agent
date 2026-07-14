import logging
from typing import Dict, Any, List
import pandas as pd
from backend.agents.schemas import ChartType, VisualizationSpec

logger = logging.getLogger(__name__)

def select_best_chart_type(vis_spec: VisualizationSpec, df: pd.DataFrame) -> ChartType:
    """
    Evaluates the LLM-selected chart type against the actual dataset characteristics.
    If a better deterministic chart exists, it automatically overrides the selection.
    """
    requested_type = vis_spec.chart_type
    
    if df.empty:
        return requested_type
        
    x_col = vis_spec.x_column
    y_col = vis_spec.y_column
    
    # Need both columns to do smart routing for 2D plots
    if not x_col or x_col not in df.columns or not y_col or y_col not in df.columns:
        return requested_type
        
    x_dtype = df[x_col].dtype
    y_dtype = df[y_col].dtype
    
    # 1. Too many categories for a Pie Chart -> Bar Chart
    if requested_type == ChartType.PIE:
        num_categories = df[x_col].nunique()
        if num_categories > 10:
            logger.info(f"Selector: Pie chart requested but has {num_categories} categories. Upgrading to BAR.")
            return ChartType.BAR
            
    # 2. Line chart requested on categorical non-temporal X axis -> Bar Chart
    if requested_type == ChartType.LINE:
        is_datetime = pd.api.types.is_datetime64_any_dtype(x_dtype)
        is_numeric = pd.api.types.is_numeric_dtype(x_dtype)
        # If x is categorical string, Line chart doesn't make sense unless it's a timeseries in string format
        if not is_datetime and not is_numeric:
            # Let's check if it looks like a date string
            try:
                # Try parsing the first valid value
                first_val = df[x_col].dropna().iloc[0]
                pd.to_datetime(first_val)
            except Exception:
                logger.info("Selector: Line chart requested with non-temporal categorical X axis. Upgrading to BAR.")
                return ChartType.BAR
                
    # 3. Bar chart requested but X axis is highly granular temporal/continuous -> Line Chart
    if requested_type == ChartType.BAR:
        is_datetime = pd.api.types.is_datetime64_any_dtype(x_dtype)
        if is_datetime and len(df) > 20:
            logger.info("Selector: Bar chart requested on highly granular temporal data. Upgrading to LINE.")
            return ChartType.LINE

    return requested_type
