import pytest
from backend.agents.nodes.report_agent import classify_result_family_strict, _get_dynamic_system_prompt
from backend.services.reporting.fact_generator import compute_derived_facts
from backend.services.reporting.report_mode import ReportMode

def test_classify_result_family_precedence():
    # Setup test variables
    last_worker_result = {}
    query_result = {
        "columns": ["DEALSIZE", "PCT_SALES"],
        "dtypes": {"DEALSIZE": "string", "PCT_SALES": "number"},
        "rows": [["Medium", 60.7], ["Small", 26.3], ["Large", 13.0]]
    }
    analysis_artifacts = {}
    state = {
        "generated_code": "SELECT DEALSIZE, SUM(SALES)*100.0/SUM(SUM(SALES)) OVER () as PCT_SALES FROM orders GROUP BY DEALSIZE"
    }

    # 1. Test CONTRIBUTION is matched over generic aggregation or ranking
    # The question mentions top 3 deal sizes by percentage contribution.
    # It resembles ranking (top 3) and contribution (percentage).
    # Since pct/percentage is present, CONTRIBUTION is the primary family.
    question = "Show top 3 deal sizes by percentage contribution"
    family = classify_result_family_strict(question, last_worker_result, query_result, analysis_artifacts, state)
    assert family == "CONTRIBUTION"

    # 2. Test RANKING is matched for top N query without contribution indicator
    question_rank = "Show the top 7 customers by total sales"
    query_result_rank = {
        "columns": ["CUSTOMERNAME", "TOTAL_SALES"],
        "dtypes": {"CUSTOMERNAME": "string", "TOTAL_SALES": "number"},
        "rows": [["A", 100], ["B", 90]]
    }
    state_rank = {"generated_code": "SELECT CUSTOMERNAME, SUM(SALES) as TOTAL_SALES FROM orders GROUP BY CUSTOMERNAME ORDER BY TOTAL_SALES DESC LIMIT 7"}
    family_rank = classify_result_family_strict(question_rank, last_worker_result, query_result_rank, {}, state_rank)
    assert family_rank == "RANKING"

    # 3. Test CORRELATION matches when artifact is present
    corr_artifacts = {"correlation_matrix": {"A": {"B": 0.5}, "B": {"A": 0.5}}}
    family_corr = classify_result_family_strict("Show relations", last_worker_result, {}, corr_artifacts, {})
    assert family_corr == "CORRELATION"

    # 4. Test TREND matches when datetime column + trend keyword is present
    query_result_trend = {
        "columns": ["ORDERDATE", "SALES"],
        "dtypes": {"ORDERDATE": "datetime", "SALES": "number"},
        "rows": []
    }
    family_trend = classify_result_family_strict("Show monthly total sales over time", last_worker_result, query_result_trend, {}, {})
    assert family_trend == "TREND"


def test_compute_derived_facts():
    # Grouped/percentage contribution query result
    query_result = {
        "columns": ["DEALSIZE", "PCT_SALES"],
        "dtypes": {"DEALSIZE": "string", "PCT_SALES": "number"},
        "rows": [["Medium", 60.7], ["Small", 26.3], ["Large", 13.0]]
    }
    
    derived = compute_derived_facts(query_result)
    assert derived["highest_category"]["value"] == "Medium"
    assert derived["highest_category"]["amount"] == 60.7
    assert derived["lowest_category"]["value"] == "Large"
    assert derived["lowest_category"]["amount"] == 13.0
    
    # Check top category share
    assert derived["top_category_share"]["category"] == "Medium"
    
    # Check ratio and difference calculations
    assert derived["highest_vs_lowest"]["difference"] == round(60.7 - 13.0, 4)
    assert derived["highest_vs_lowest"]["ratio"] == round(60.7 / 13.0, 4)


def test_semantic_prompt_instructions():
    # Verify that the semantic contract instructions for each family do not mix terminology
    prompt_grouped = _get_dynamic_system_prompt(ReportMode.STANDARD, "GROUPED_AGGREGATION")
    assert "correlation" not in prompt_grouped.lower() or "do not use correlation terms" in prompt_grouped.lower()
    assert "causal impact" not in prompt_grouped.lower() or "do not use" in prompt_grouped.lower()
    
    prompt_contribution = _get_dynamic_system_prompt(ReportMode.STANDARD, "CONTRIBUTION")
    assert "positive correlation" not in prompt_contribution.lower() or "do not call" in prompt_contribution.lower()
    assert "linear relationship" not in prompt_contribution.lower() or "do not use" in prompt_contribution.lower()
    
    prompt_corr = _get_dynamic_system_prompt(ReportMode.STANDARD, "CORRELATION")
    assert "moderate linear correlation" in prompt_corr.lower()
    assert "do not translate correlation coefficient" in prompt_corr.lower()
    assert "do not infer causality" in prompt_corr.lower()
