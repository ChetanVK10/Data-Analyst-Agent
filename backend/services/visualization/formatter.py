import plotly.graph_objects as go

def format_layout(fig: go.Figure, title: str, x_axis_title: str = None, y_axis_title: str = None) -> go.Figure:
    """
    Applies deterministic layout rules to a Plotly figure to ensure consistency and quality.
    - generate axis labels
    - generate chart titles
    - rotate long categorical labels
    - increase margins when labels overlap
    - dynamically adjust figure width
    - intelligently format large numbers (K, M, etc.)
    - sort comparison charts where appropriate
    - display value labels when useful
    """
    layout_update = {
        "title": {
            "text": title,
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 20, "family": "Inter, sans-serif"}
        },
        "plot_bgcolor": "white",
        "paper_bgcolor": "white",
        "margin": dict(t=80, l=60, r=40, b=80),
        "font": {"family": "Inter, sans-serif"},
        "colorway": ["#2563eb", "#db2777", "#16a34a", "#ca8a04", "#9333ea", "#0ea5e9"] # Modern Tailwind colors
    }
    
    fig.update_layout(**layout_update)

    # X-Axis formatting
    xaxis_update = {
        "showgrid": False,
        "showline": True,
        "linewidth": 1,
        "linecolor": "lightgray",
        "title": {"text": x_axis_title} if x_axis_title else None,
        "automargin": True, # automatically increase margins when labels overlap
    }
    fig.update_xaxes(**xaxis_update)
    
    # Y-Axis formatting
    yaxis_update = {
        "showgrid": True,
        "gridcolor": "whitesmoke",
        "showline": False,
        "title": {"text": y_axis_title} if y_axis_title else None,
        "automargin": True,
        "zeroline": True,
        "zerolinecolor": "lightgray"
    }
    fig.update_yaxes(**yaxis_update)

    # Apply data labels
    _apply_value_labels(fig, y_axis_title)

    return fig

def _apply_value_labels(fig: go.Figure, y_axis_title: str = None):
    """
    Applies deterministic value labels to traces based on chart type.
    """
    is_currency = False
    is_percent = False
    
    if y_axis_title:
        title_lower = y_axis_title.lower()
        if any(w in title_lower for w in ['sales', 'revenue', 'price', '$', 'amount', 'cost']):
            is_currency = True
        if any(w in title_lower for w in ['percent', 'rate', 'ratio', '%']):
            is_percent = True

    for trace in fig.data:
        # Determine number of data points
        length = 0
        if hasattr(trace, 'x') and trace.x is not None:
            length = len(trace.x)
        elif hasattr(trace, 'y') and trace.y is not None:
            length = len(trace.y)
        elif hasattr(trace, 'labels') and trace.labels is not None:
            length = len(trace.labels)
            
        if trace.type in ['bar', 'histogram']:
            if length <= 15:
                trace.textposition = 'auto'
                
                # Determine value axis
                is_horizontal = getattr(trace, 'orientation', 'v') == 'h'
                var = 'x' if is_horizontal else 'y'
                
                # Format: 4 sig figs, trim trailing zeroes
                base_format = f'%{{{var}:.4~s}}'
                if is_currency:
                    trace.texttemplate = f'$%{{{var}:.4~s}}'
                elif is_percent:
                    trace.texttemplate = f'%{{{var}:.4~s}}%'
                else:
                    trace.texttemplate = base_format
                    
        elif trace.type == 'pie':
            if length <= 10:
                trace.textinfo = 'label+percent'
            else:
                trace.textinfo = 'percent'
                
        elif trace.type == 'scatter':
            # For lines, area, scatter, avoid direct labels to prevent clutter.
            # Only use hover.
            pass
        elif trace.type == 'box':
            pass
