"""
recommendation_engine.py — Generates contextual follow-up analyses based on question and schema.
"""
from typing import Dict, Any, List

def generate_recommendations(
    question: str, 
    schema_profile: Dict[str, Any]
) -> List[Dict[str, str]]:
    """
    Produces deterministic, contextual follow-up recommendations.
    Ensures recommendations are tied to the user's current question and 
    the platform's capabilities (SQL, stats, visualization).
    """
    recs = []
    q_lower = question.lower()
    cols = schema_profile.get("columns", [])
    
    # Identify column types safely
    numeric_cols = [c["name"] for c in cols if c.get("type", "").lower() in ["integer", "double", "numeric", "float", "real"]]
    date_cols = [c["name"] for c in cols if "date" in c.get("type", "").lower() or "timestamp" in c.get("type", "").lower()]
    cat_cols = [c["name"] for c in cols if c.get("type", "").lower() in ["varchar", "text", "string"]]
    
    # 1. Relevance to "highest/lowest" questions
    if any(k in q_lower for k in ["highest", "lowest", "top", "bottom", "max", "min"]):
        if numeric_cols:
            col = numeric_cols[0]
            recs.append({
                "title": "Distribution Analysis",
                "body": f"Since you looked at extreme values, consider running a distribution analysis on '{col}' to see the overall spread and identify if this is a statistical outlier."
            })
            
    # 2. Relevance to "trend" or "over time" or if dates are involved
    if "trend" in q_lower or "time" in q_lower or "date" in q_lower or "month" in q_lower or "year" in q_lower:
        if date_cols and numeric_cols:
            d_col = date_cols[0]
            n_col = numeric_cols[0]
            recs.append({
                "title": "Monthly Growth Analysis",
                "body": f"Calculate the month-over-month growth rate for '{n_col}' using '{d_col}' to identify accelerating or decelerating trends."
            })
            
    # 3. Relevance to "compare" or "difference" or categories
    if "compare" in q_lower or "difference" in q_lower or "vs" in q_lower or "versus" in q_lower:
        if cat_cols and numeric_cols:
            recs.append({
                "title": "Correlation Analysis",
                "body": "Since you are comparing specific categories, run a correlation analysis between the numeric columns to see if there are underlying mathematical relationships driving these differences."
            })
            
    # 4. Relevance to counts and simple metrics
    if "how many" in q_lower or "count" in q_lower:
        if cat_cols:
            recs.append({
                "title": "Categorical Breakdown",
                "body": f"You found the total count. Consider grouping this count by '{cat_cols[0]}' to see which categories contribute the most."
            })
            
    # 5. Default contextual fallback if nothing specific matched
    if len(recs) == 0:
        if numeric_cols and cat_cols:
            recs.append({
                "title": "Cross-tabulation",
                "body": f"Ask to aggregate '{numeric_cols[0]}' grouped by '{cat_cols[0]}' to see how the metrics are distributed across categories."
            })
        elif date_cols:
            recs.append({
                "title": "Time Series Visualization",
                "body": f"Ask for a line chart of the data over '{date_cols[0]}' to visually spot seasonal patterns."
            })
            
    # Return a maximum of 2 highly relevant recommendations to keep the report concise
    return recs[:2]
