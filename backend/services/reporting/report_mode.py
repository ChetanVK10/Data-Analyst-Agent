"""
report_mode.py — Determines the complexity of the report to generate.
"""
from enum import Enum
from typing import Dict, Any

class ReportMode(str, Enum):
    QUICK = "Quick"
    STANDARD = "Standard"
    ANALYTICAL = "Analytical"
    RESEARCH = "Research"

def determine_report_mode(
    question: str,
    last_worker_result: Dict[str, Any],
    query_result: Dict[str, Any],
    analysis_artifacts: Dict[str, Any]
) -> ReportMode:
    """
    Evaluates the state context to determine how verbose the LLM report should be.
    """
    worker = last_worker_result.get("worker_name", "")
    q_lower = question.lower()
    
    # 1. Explicit Research requests
    if any(k in q_lower for k in ["research", "deep dive", "comprehensive report", "full report"]):
        return ReportMode.RESEARCH
        
    # 2. Advanced Analysis capability triggers Analytical mode
    if worker == "ANALYSIS" or analysis_artifacts:
        return ReportMode.ANALYTICAL
        
    # 3. Keyword heuristics for analysis
    if any(k in q_lower for k in ["analyze", "why", "trend", "compare", "correlat"]):
        return ReportMode.ANALYTICAL
        
    # 4. Determine based on SQL result set size
    rows = query_result.get("rows", [])
    cols = query_result.get("columns", [])
    
    if len(rows) <= 1 and len(cols) <= 2:
        # Single scalar answer like "What is the total revenue?"
        return ReportMode.QUICK
        
    if any(k in q_lower for k in ["highest", "lowest", "how many", "what is"]):
        if len(rows) <= 10:
            return ReportMode.QUICK
            
    return ReportMode.STANDARD
