import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def split_top_level(text: str, sep: str = ',') -> List[str]:
    parts = []
    current = []
    depth = 0
    in_quote = False
    quote_char = None
    for char in text:
        if in_quote:
            if char == quote_char:
                in_quote = False
            current.append(char)
        elif char in ("'", '"'):
            in_quote = True
            quote_char = char
            current.append(char)
        elif char == '(':
            depth += 1
            current.append(char)
        elif char == ')':
            if depth > 0:
                depth -= 1
            current.append(char)
        elif char == sep and depth == 0:
            parts.append(''.join(current))
            current = []
        else:
            current.append(char)
    if current:
        parts.append(''.join(current))
    return parts

def validate_sql(query: str, schema: Dict[str, Any] = None, question: str = "") -> Dict[str, Any]:
    """
    Validates SQL query quality deterministically.
    Returns a dict with:
    {
        "is_valid": bool,
        "diagnostics": str,
        "critical_issues": List[str],
        "warnings": List[str]
    }
    """
    critical_issues = []
    warnings = []
    
    query_upper = query.upper()
    
    if not query_upper.strip().startswith("SELECT"):
        return {"is_valid": True, "diagnostics": "", "critical_issues": [], "warnings": []}

    # 1. Misuse of SELECT *
    if re.search(r"SELECT\s+\*\s+FROM", query_upper) or re.search(r"SELECT\s+.*,\s*\*\s+FROM", query_upper):
        critical_issues.append("Misuse of SELECT * when only a subset of fields is required.")

    # 2. Missing GROUP BY when required
    has_aggregate = bool(re.search(r"\b(MAX|MIN|AVG|SUM|COUNT)\s*\(", query_upper))
    if has_aggregate and "GROUP BY" not in query_upper:
        select_clause_match = re.search(r"SELECT\s+(.*?)\s+FROM", query, re.IGNORECASE | re.DOTALL)
        if select_clause_match:
            select_clause = select_clause_match.group(1)
            top_level_exprs = split_top_level(select_clause, ',')
            
            has_non_agg = False
            for expr in top_level_exprs:
                if not re.search(r"\b(MAX|MIN|AVG|SUM|COUNT)\s*\(", expr, flags=re.IGNORECASE):
                    # Clean the expression to see if it's just a literal
                    cleaned = re.sub(r"\bAS\s+(?:\"[^\"]*\"|'[^']*'|[\w]+)", "", expr, flags=re.IGNORECASE)
                    cleaned = re.sub(r"'[^']*'", "", cleaned)
                    cleaned = re.sub(r"\b\d+(\.\d+)?\b", "", cleaned)
                    cleaned = re.sub(r"\b(NULL|DISTINCT)\b", "", cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r"[\s,;+\-*/=<>]+", "", cleaned)
                    if cleaned:
                        has_non_agg = True
                        break
                        
            if has_non_agg:
                critical_issues.append("Missing GROUP BY when required: non-aggregated columns are selected alongside aggregates.")

    # 3. Missing LIMIT for Top/Bottom N queries
    question_lower = question.lower()
    if re.search(r"\b(top|bottom|first|last)\s+\d+\b", question_lower) or re.search(r"\b(highest|lowest)\b", question_lower):
        if "LIMIT" not in query_upper:
            critical_issues.append("Missing LIMIT for Top/Bottom N queries.")

    # 4. Incorrect ORDER BY direction
    if "ORDER BY" in query_upper:
        order_by_clause = query_upper.split("ORDER BY")[1]
        is_desc = "DESC" in order_by_clause
        if re.search(r"\b(highest|top|most|largest|max)\b", question_lower):
            if not is_desc:
                critical_issues.append("Incorrect ORDER BY direction: Expected DESC for 'highest'/'top' intent.")
        elif re.search(r"\b(lowest|bottom|least|smallest|min)\b", question_lower):
            if is_desc:
                critical_issues.append("Incorrect ORDER BY direction: Expected ASC for 'lowest'/'bottom' intent.")

    # 5. Invalid column references
    if schema and "columns" in schema:
        valid_columns = [col["name"].lower() for col in schema["columns"]]
        quoted_cols = re.findall(r'"([^"]+)"', query)
        for col in quoted_cols:
            if col.lower() not in valid_columns:
                critical_issues.append(f"Invalid column reference: \"{col}\"")

    # 6. Aggregate Alias (WARNING)
    select_clause_match = re.search(r"SELECT\s+(.*?)\s+FROM", query, re.IGNORECASE | re.DOTALL)
    if select_clause_match:
        select_clause = select_clause_match.group(1)
        top_level_exprs = split_top_level(select_clause, ',')
        for expr in top_level_exprs:
            if re.search(r"\b(MAX|MIN|AVG|SUM|COUNT)\s*\(", expr, flags=re.IGNORECASE):
                if not re.search(r"\bAS\s+", expr, flags=re.IGNORECASE):
                    warnings.append(f"Aggregate expression {expr.strip()} is missing a meaningful alias using AS.")

    # 7. Monetary Formatting (WARNING)
    monetary_keywords = ["amount", "price", "cost", "revenue", "salary", "balance", "billing"]
    for match in re.finditer(r"\b(MAX|MIN|AVG|SUM)\s*\(\s*(?:DISTINCT\s+)?([^)]+)\)", query_upper):
        col_name = match.group(2).lower()
        if any(kw in col_name for kw in monetary_keywords):
            if "ROUND" not in query_upper:
                warnings.append("When returning monetary values, automatically round to two decimal places where appropriate.")
                break

    is_valid = len(critical_issues) == 0
    diagnostics = ""
    if critical_issues:
        diagnostics += "CRITICAL ISSUES:\n- " + "\n- ".join(critical_issues) + "\n"
    if warnings:
        diagnostics += "WARNINGS:\n- " + "\n- ".join(warnings) + "\n"

    return {
        "is_valid": is_valid,
        "diagnostics": diagnostics.strip(),
        "critical_issues": critical_issues,
        "warnings": warnings
    }
