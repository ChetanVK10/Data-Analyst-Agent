import pytest
from backend.agents.nodes.code_generator import code_generator_node
from backend.agents.nodes.validator import validator_node
from backend.agents.nodes.reflection import reflection_node
from unittest.mock import patch, MagicMock

def test_provider_429_skips_retries():
    # 1. code_generator fails with 429
    state = {
        "plan": {"approach": "sql", "steps": []},
        "retry_count": 0,
        "question": "test",
        "schema_profile": {},
        "dataset_id": "test_dataset"
    }
    
    with patch("backend.agents.nodes.code_generator.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("HTTP 429 Resource Exhausted")
        mock_get_llm.return_value = mock_llm
        
        cg_res = code_generator_node(state)
        
    assert cg_res["generated_code"] == ""
    assert "failure_summary" in cg_res
    assert cg_res["failure_summary"]["failure_type"] == "provider_error"
    
    # 2. update state
    state.update(cg_res)
    state["execution_success"] = False
    
    # 3. validator preserves it
    val_res = validator_node(state)
    assert not val_res["validation_passed"]
    assert val_res["failure_summary"]["failure_type"] == "provider_error"
    
    # 4. update state
    state.update(val_res)
    
    # 5. reflection skips retry
    ref_res = reflection_node(state)
    assert ref_res["graceful_failure"] is True
    assert ref_res["last_worker_result"]["routing_hint"] == "REPORT"

def test_invalid_sql_retries_normally():
    state = {
        "plan": {"approach": "sql"},
        "retry_count": 0,
        "generated_code": "SELECT * FROM t",
        "execution_success": False,
        "output_summary": {"error": "syntax error"},
        "expected_output_type": "dataframe"
    }
    
    val_res = validator_node(state)
    assert val_res["failure_summary"]["failure_type"] in ["runtime", "timeout"]
    
    state.update(val_res)
    ref_res = reflection_node(state)
    assert ref_res["graceful_failure"] is False
    assert ref_res["retry_count"] == 1
    assert ref_res["last_worker_result"]["routing_hint"] == "SQL"

def test_python_execution_failure_retries_normally():
    state = {
        "plan": {"approach": "python"},
        "retry_count": 0,
        "generated_code": "print(1/0)",
        "execution_success": False,
        "output_summary": {"error": "ZeroDivisionError"},
        "expected_output_type": "dataframe"
    }
    
    val_res = validator_node(state)
    assert val_res["failure_summary"]["failure_type"] in ["runtime", "timeout"]
    
    state.update(val_res)
    ref_res = reflection_node(state)
    assert ref_res["graceful_failure"] is False
    assert ref_res["retry_count"] == 1
    assert ref_res["last_worker_result"]["routing_hint"] == "PYTHON_ANALYSIS"
