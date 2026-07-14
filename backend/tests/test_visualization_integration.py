import pytest
import math
import pandas as pd
import numpy as np
import datetime
import json
from unittest.mock import patch, MagicMock

from backend.utils.json_sanitizer import sanitize_for_json
from backend.agents.nodes.visualization_executor import validate_chart_spec
from backend.agents.schemas import VisualizationSpec, ChartType
from backend.agents.nodes.sandbox_executor import sandbox_executor_node
from backend.agents.nodes.visualization_generator import visualization_generator_node

CUSTOM_ENCODER_CODE = """
import pandas as pd
import numpy as np
import json
import datetime

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
            dtypes_dict = {str(k): map_pd_dtype(v) for k, v in obj.dtypes.items()}
            safe_df = obj.replace({np.nan: None})
            return {"type": "dataframe", "columns": list(obj.columns), "dtypes": dtypes_dict, "rows": safe_df.to_dict(orient="records")}
        if hasattr(obj, "item"): return obj.item()
        if isinstance(obj, (datetime.date, datetime.datetime)): return obj.isoformat()
        return super().default(obj)
"""

# --- D. JSON Sanitization Tests ---

def test_json_sanitizer():
    # NaN and Infinity
    assert sanitize_for_json(float('nan')) is None
    assert sanitize_for_json(float('inf')) is None
    assert sanitize_for_json(float('-inf')) is None
    
    # Pandas NA types
    assert sanitize_for_json(pd.NA) is None
    assert sanitize_for_json(pd.NaT) is None
    
    # Numpy scalars
    assert isinstance(sanitize_for_json(np.int64(42)), int)
    assert sanitize_for_json(np.int64(42)) == 42
    assert isinstance(sanitize_for_json(np.float64(3.14)), float)
    assert sanitize_for_json(np.float64(3.14)) == 3.14
    assert isinstance(sanitize_for_json(np.bool_(True)), bool)
    assert sanitize_for_json(np.bool_(True)) is True
    assert sanitize_for_json(np.float64('nan')) is None
    
    # Nested structures
    complex_obj = {
        "a": float('nan'),
        "b": [1, pd.NA, {"c": float('inf'), "d": np.int32(5)}],
        "e": (pd.NaT, 2.5)
    }
    
    sanitized = sanitize_for_json(complex_obj)
    assert sanitized["a"] is None
    assert sanitized["b"][1] is None
    assert sanitized["b"][2]["c"] is None
    assert isinstance(sanitized["b"][2]["d"], int)
    assert sanitized["e"] == [None, 2.5] # tuples become lists in json
    
    # Plain Ndarray arrays
    arr = np.array([1, 2, np.nan, 4])
    sanitized_arr = sanitize_for_json(arr)
    assert sanitized_arr == [1, 2, None, 4]
    
    # Nested Ndarray
    nested_obj = {"x": np.array([1, 2]), "y": [np.array([3.14, np.inf])]}
    sanitized_nested = sanitize_for_json(nested_obj)
    assert sanitized_nested["x"] == [1, 2]
    assert sanitized_nested["y"][0] == [3.14, None]
    
    # Plotly bdata typed-array encoding (categorical + numeric)
    # Simulated from 5 customer labels and 5 numeric sales
    import base64
    arr = np.array([5000, 7000, 3000, 8000, 9000], dtype='i4')
    bdata_encoded = base64.b64encode(arr.tobytes()).decode('utf-8')
    plotly_obj = {
        "x": np.array(["Alice", "Bob", "Charlie", "Dave", "Eve"]),
        "y": {"dtype": "i4", "bdata": bdata_encoded}
    }
    sanitized_plotly = sanitize_for_json(plotly_obj)
    assert len(sanitized_plotly["x"]) == 5
    assert len(sanitized_plotly["y"]) == 5
    assert sanitized_plotly["x"] == ["Alice", "Bob", "Charlie", "Dave", "Eve"]
    assert sanitized_plotly["y"] == [5000, 7000, 3000, 8000, 9000]
    
    # Verify json.dumps succeeds
    import json
    assert json.dumps(sanitized_plotly) is not None
    assert json.dumps(sanitized_nested) is not None

# --- B. Visualization Spec Validation Tests ---

def test_visualization_spec_validation():
    # valid categorical x + numeric y passes
    spec = VisualizationSpec(is_appropriate=True, chart_type=ChartType.BAR, x_column="category", y_column="value")
    columns = ["category", "value"]
    dtypes = {"category": "string", "value": "number"}
    is_valid, err, is_no_vis = validate_chart_spec(spec, columns, dtypes, [{}])
    assert is_valid is True
    assert is_no_vis is False
    
    # nonexistent x_axis is rejected
    spec = VisualizationSpec(is_appropriate=True, chart_type=ChartType.BAR, x_column="missing", y_column="value")
    is_valid, err, is_no_vis = validate_chart_spec(spec, columns, dtypes, [{}])
    assert is_valid is False
    assert "does not exist" in err
    
    # string y_axis is rejected when numeric y is required
    spec = VisualizationSpec(is_appropriate=True, chart_type=ChartType.BAR, x_column="category", y_column="category")
    is_valid, err, is_no_vis = validate_chart_spec(spec, columns, dtypes, [{}])
    assert is_valid is False
    assert "must be numeric" in err
    
    # missing required axis is rejected
    spec = VisualizationSpec(is_appropriate=True, chart_type=ChartType.BAR, x_column="category")
    is_valid, err, is_no_vis = validate_chart_spec(spec, columns, dtypes, [{}])
    assert is_valid is False
    assert "Y-axis is required" in err
    
    # no_visualization is treated as a valid non-failure outcome (scalar)
    spec = VisualizationSpec(is_appropriate=True, chart_type=ChartType.BAR, x_column="value", y_column="value")
    is_valid, err, is_no_vis = validate_chart_spec(spec, ["value"], {"value": "number"}, [{"value": 42}])
    assert is_no_vis is True
    assert is_valid is False # It fails validation, but triggers the is_no_vis path

def test_visualization_spec_validation_multi_series():
    from backend.services.visualization.templates import render_chart
    
    spec = VisualizationSpec(
        is_appropriate=True,
        chart_type=ChartType.LINE,
        x_column="date",
        y_column=None,
        y_columns=["sales", "moving_average"],
        title="Sales vs MA"
    )
    columns = ["date", "sales", "moving_average"]
    dtypes = {"date": "datetime", "sales": "number", "moving_average": "number"}
    df = pd.DataFrame({
        "date": [datetime.date(2023, 1, 1), datetime.date(2023, 2, 1)],
        "sales": [100, 110],
        "moving_average": [None, 105]
    })
    
    # Assert validation passes
    is_valid, err, is_no_vis = validate_chart_spec(spec, columns, dtypes, df.to_dict(orient="records"))
    assert is_valid is True, f"Validation failed: {err}"
    assert is_no_vis is False
    
    # Assert line rendering produces exactly 2 Plotly traces
    fig_json = render_chart(ChartType.LINE, spec, df)
    assert fig_json is not None
    assert len(fig_json.get("data", [])) == 2

# --- A. Result Metadata Tests ---

def test_semantic_dtypes_python():
    # Python DataFrame dtypes map into the same semantic vocabulary
    # The CustomEncoder is a string in sandbox_executor.py, so we evaluate it locally
    code_eval = CUSTOM_ENCODER_CODE + """
df = pd.DataFrame({
    "A": [1, 2],
    "B": ["x", "y"],
    "C": [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")],
    "D": [True, False],
    "E": [np.nan, 2.5]
})
encoder = CustomEncoder()
encoded = json.loads(encoder.encode(df))
"""
    local_env = {}
    exec(code_eval, {"pd": pd, "np": np, "json": json, "datetime": datetime}, local_env)
    encoded = local_env["encoded"]
    
    dtypes = encoded["dtypes"]
    assert dtypes["A"] == "number"
    assert dtypes["B"] == "string"
    assert dtypes["C"] == "datetime"
    assert dtypes["D"] == "boolean"
    assert dtypes["E"] == "number"
    
    assert encoded["rows"][0]["E"] is None # NaN replaced with None

def test_dataframe_index_preservation():
    # default RangeIndex does not create an unnecessary index column
    df_range = pd.DataFrame({"A": [1, 2]})
    code_range = """
encoder = CustomEncoder()
encoded_range = json.loads(encoder.encode(df_range))
"""
    local_env_range = {"df_range": df_range}
    # Re-evaluating with the same CustomEncoder logic
    exec(CUSTOM_ENCODER_CODE + "\n" + code_range, {"pd": pd, "np": np, "json": json, "datetime": datetime}, local_env_range)
    assert "index" not in local_env_range["encoded_range"]["columns"]

    # meaningful named pivot index is preserved as a result column
    df_pivot = pd.DataFrame({"Value": [10, 20]}, index=pd.Index(["X", "Y"], name="Category"))
    code_pivot = """
encoder = CustomEncoder()
encoded_pivot = json.loads(encoder.encode(df_pivot))
"""
    local_env_pivot = {"df_pivot": df_pivot}
    exec(CUSTOM_ENCODER_CODE + "\n" + code_pivot, {"pd": pd, "np": np, "json": json, "datetime": datetime}, local_env_pivot)
    
    encoded_pivot = local_env_pivot["encoded_pivot"]
    assert "Category" in encoded_pivot["columns"]
    assert encoded_pivot["dtypes"]["Category"] == "string"
    assert encoded_pivot["rows"][0]["Category"] == "X"


# --- C. Sandbox Contract Tests ---

@patch("backend.agents.nodes.visualization_generator.get_llm")
def test_malformed_spec_handling(mock_get_llm):
    # Setup mock LLM to return malformed JSON
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="Invalid JSON ``` {")
    mock_get_llm.return_value = mock_llm
    
    state = {
        "question": "Show me a chart",
        "query_result": {"columns": ["a"], "dtypes": {"a": "number"}, "rows": [{"a": 1}]},
        "execution_metadata": []
    }
    
    updates = visualization_generator_node(state)
    
    # Verify malformed spec prevents execution
    assert updates["vis_spec"] is None
    assert updates["vis_generated_code"] is None
    assert "failure_summary" in updates
    assert updates["failure_summary"]["failure_type"] == "visualization"
    assert "Failed to parse" in updates["failure_summary"]["error_message"]
