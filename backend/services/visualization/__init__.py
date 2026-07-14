"""
Modular Visualization Service

This module handles deterministic Plotly chart generation based on structured specifications
returned by the Visualization Generator LLM.

Components:
- selector: Selects the most appropriate chart type.
- templates: Renders Plotly figures based on chart types and metadata.
- formatter: Applies consistent layout and styling rules.
- validator: Validates data requirements and layout parameters.
"""
