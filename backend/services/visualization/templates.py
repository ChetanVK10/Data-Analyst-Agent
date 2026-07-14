import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Optional, Dict, Any

from backend.agents.schemas import ChartType, VisualizationSpec
from backend.services.visualization.formatter import format_layout

def render_chart(chart_type: ChartType, vis_spec: VisualizationSpec, df: pd.DataFrame) -> Optional[dict]:
    """
    Renders a Plotly figure as a JSON dictionary based on the requested chart type and metadata.
    Returns None if the chart type is OTHER or cannot be rendered via templates.
    """
    fig = None
    x = vis_spec.x_column
    y = vis_spec.y_column
    y_cols = vis_spec.y_columns or ([y] if y else [])
    
    # Fallback for single-series charts if y_column is omitted but y_columns has data
    if not y and y_cols:
        y = y_cols[0]

    color = vis_spec.color_column if vis_spec.color_column in df.columns else None
    
    # Optional parameters for px
    kwargs = {}
    if color:
        kwargs["color"] = color

    if chart_type == ChartType.BAR:
        # If it's a bar chart, we might want to sort it if it's not temporal
        if x and x in df.columns and y and y in df.columns:
            is_temporal = pd.api.types.is_datetime64_any_dtype(df[x])
            plot_df = df.copy()
            if not is_temporal and not color:
                plot_df = plot_df.sort_values(by=y, ascending=False).head(50) # limit to top 50 for readability
            fig = px.bar(plot_df, x=x, y=y, **kwargs)

    elif chart_type == ChartType.LINE:
        if x and y_cols:
            # Sort by x for line charts usually makes sense
            plot_df = df.copy()
            plot_df = plot_df.sort_values(by=x)
            
            # If multiple Y columns are passed, px.line will automatically melt and plot multiple traces
            if len(y_cols) == 1:
                fig = px.line(plot_df, x=x, y=y_cols[0], **kwargs)
            else:
                # When using multiple y columns, px.line creates a legend title 'variable'. We can let it default.
                fig = px.line(plot_df, x=x, y=y_cols, **kwargs)
                
    elif chart_type == ChartType.AREA:
        if x and y_cols:
            plot_df = df.copy()
            plot_df = plot_df.sort_values(by=x)
            if len(y_cols) == 1:
                fig = px.area(plot_df, x=x, y=y_cols[0], **kwargs)
            else:
                fig = px.area(plot_df, x=x, y=y_cols, **kwargs)
            
    elif chart_type == ChartType.SCATTER:
        if x and y:
            fig = px.scatter(df, x=x, y=y, **kwargs)
            
    elif chart_type == ChartType.PIE:
        if x and y:
            plot_df = df.copy()
            # Sort and group small slices if too many categories
            if len(plot_df) > 10:
                plot_df = plot_df.sort_values(by=y, ascending=False)
                top_df = plot_df.iloc[:9]
                other_sum = plot_df.iloc[9:][y].sum()
                other_row = pd.DataFrame([{x: 'Other', y: other_sum}])
                plot_df = pd.concat([top_df, other_row], ignore_index=True)
            
            fig = px.pie(plot_df, names=x, values=y)
            
    elif chart_type == ChartType.HISTOGRAM:
        if x:
            fig = px.histogram(df, x=x, **kwargs)
            
    elif chart_type == ChartType.BOX:
        if y:
            kwargs_box = {}
            if x:
                kwargs_box["x"] = x
            if color:
                kwargs_box["color"] = color
            fig = px.box(df, y=y, **kwargs_box)
            
    elif chart_type == ChartType.HEATMAP:
        # Heatmap usually needs a matrix, or x, y, and z. If we just have x and y, maybe a density heatmap
        if x and y:
            fig = px.density_heatmap(df, x=x, y=y)
            
    if fig is None:
        return None
        
    # Apply standard layout formatting
    fig = format_layout(
        fig, 
        title=vis_spec.title, 
        x_axis_title=vis_spec.x_axis_title or x, 
        y_axis_title=vis_spec.y_axis_title or y
    )
    
    return fig.to_plotly_json()
