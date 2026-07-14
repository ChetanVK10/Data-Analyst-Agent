import pytest
import pandas as pd
from backend.utils.analytical_roles import infer_analytical_roles
from backend.services.visualization.validator import is_result_chartable, validate_data_requirements
from backend.agents.schemas import ChartType, VisualizationSpec

def test_infer_analytical_roles():
    columns = ["order_id", "order_date", "customer_name", "sales_amount", "moving_average"]
    dtypes = {
        "order_id": "number",
        "order_date": "datetime",
        "customer_name": "string",
        "sales_amount": "number",
        "moving_average": "number"
    }
    
    roles = infer_analytical_roles(columns, dtypes)
    
    # 1. identifier-like numeric columns are not automatically treated as measures
    assert roles["order_id"] == "identifier"
    # 2. temporal works
    assert roles["order_date"] == "temporal"
    # 3. categorical fallback works
    assert roles["customer_name"] == "categorical"
    # 4. measure default for numeric works
    assert roles["sales_amount"] == "measure"
    # 5. derived_measure is recognized
    assert roles["moving_average"] == "derived_measure"

def test_is_result_chartable_temporal_measure():
    # temporal + measure result is chartable
    query_result = {
        "columns": ["month", "revenue"],
        "rows": [["Jan", 100], ["Feb", 120]],
        "analytical_roles": {"month": "temporal", "revenue": "measure"}
    }
    assert is_result_chartable(query_result) is True

def test_is_result_chartable_categorical_measure():
    # categorical + measure result is chartable
    query_result = {
        "columns": ["category", "sales"],
        "rows": [["A", 100], ["B", 120]],
        "analytical_roles": {"category": "categorical", "sales": "measure"}
    }
    assert is_result_chartable(query_result) is True

def test_is_result_chartable_two_measures():
    # two numeric measures are chartable
    query_result = {
        "columns": ["height", "weight"],
        "rows": [[170, 65], [180, 75]],
        "analytical_roles": {"height": "measure", "weight": "measure"}
    }
    assert is_result_chartable(query_result) is True
    
def test_is_result_chartable_non_chartable():
    # empty
    assert is_result_chartable({"columns": [], "rows": [], "analytical_roles": {}}) is False
    
    # single scalar
    query_result = {
        "columns": ["total_sales"],
        "rows": [[5000]],
        "analytical_roles": {"total_sales": "measure"}
    }
    assert is_result_chartable(query_result) is False
    
    # single text
    query_result = {
        "columns": ["message"],
        "rows": [["No data found"]],
        "analytical_roles": {"message": "categorical"}
    }
    assert is_result_chartable(query_result) is False

def test_validate_data_requirements_y_columns():
    df = pd.DataFrame({
        "date": ["2023-01", "2023-02"],
        "sales": [100, 110],
        "moving_average": [None, 105]
    })
    
    # 1. multi-series validation works
    spec_multi = VisualizationSpec(
        is_appropriate=True,
        chart_type=ChartType.LINE,
        x_column="date",
        y_columns=["sales", "moving_average"],
        title="Sales vs MA"
    )
    is_valid, err = validate_data_requirements(ChartType.LINE, spec_multi, df)
    assert is_valid is True, f"Multi-series failed: {err}"
    
    # 2. existing single-series validation remains backward compatible
    spec_single = VisualizationSpec(
        is_appropriate=True,
        chart_type=ChartType.LINE,
        x_column="date",
        y_column="sales",
        title="Sales"
    )
    is_valid, err = validate_data_requirements(ChartType.LINE, spec_single, df)
    assert is_valid is True, f"Single-series failed: {err}"

import json
from backend.services.visualization.templates import render_chart

def test_render_chart_y_columns_line_creates_two_traces():
    df = pd.DataFrame({
        "date": ["2023-01", "2023-02"],
        "sales": [100, 110],
        "moving_average": [None, 105]
    })
    spec = VisualizationSpec(
        is_appropriate=True,
        chart_type=ChartType.LINE,
        x_column="date",
        y_columns=["sales", "moving_average"],
        title="Sales vs MA"
    )
    fig_json = render_chart(ChartType.LINE, spec, df)
    
    # Line chart with 2 Y-columns should create 2 traces
    assert len(fig_json.get("data", [])) == 2

def test_render_chart_y_column_single_creates_one_trace():
    df = pd.DataFrame({
        "date": ["2023-01", "2023-02"],
        "sales": [100, 110]
    })
    spec = VisualizationSpec(
        is_appropriate=True,
        chart_type=ChartType.LINE,
        x_column="date",
        y_column="sales",
        title="Sales"
    )
    fig_json = render_chart(ChartType.LINE, spec, df)
    
    # Single Y-column should create 1 trace
    assert len(fig_json.get("data", [])) == 1

def test_multi_series_validation_and_rendering_agree():
    df = pd.DataFrame({
        "date": ["2023-01", "2023-02"],
        "sales": [100, 110],
        "moving_average": [None, 105]
    })
    spec = VisualizationSpec(
        is_appropriate=True,
        chart_type=ChartType.LINE,
        x_column="date",
        y_columns=["sales", "moving_average"],
        title="Sales vs MA"
    )
    
    is_valid, _ = validate_data_requirements(ChartType.LINE, spec, df)
    assert is_valid is True
    
    fig_json = render_chart(ChartType.LINE, spec, df)
    assert fig_json is not None

def test_render_chart_no_regression_existing_chart_types():
    df = pd.DataFrame({
        "category": ["A", "B"],
        "sales": [100, 110]
    })
    spec = VisualizationSpec(
        is_appropriate=True,
        chart_type=ChartType.BAR,
        x_column="category",
        y_column="sales",
        title="Sales"
    )
    fig_json = render_chart(ChartType.BAR, spec, df)
    
    # Bar chart with standard y_column should work
    assert len(fig_json.get("data", [])) == 1
    assert fig_json["data"][0]["type"] == "bar"

