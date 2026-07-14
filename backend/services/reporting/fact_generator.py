"""
fact_generator.py — Generates deterministic, question-aware facts from query results.
"""
import pandas as pd
from typing import Dict, Any

def compute_derived_facts(query_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes derived statistical comparisons (highest, lowest, shares, gaps, ratios)
    from query result rows.
    """
    derived = {}
    rows = query_result.get("rows") or []
    cols = query_result.get("columns") or []
    dtypes = query_result.get("dtypes") or {}
    
    if not rows or not cols:
        return derived
        
    # Convert list of lists/tuples to list of dicts for uniform access
    normalized_rows = []
    for r in rows:
        if isinstance(r, dict):
            normalized_rows.append(r)
        elif isinstance(r, (list, tuple)):
            normalized_rows.append(dict(zip(cols, r)))
            
    # Infer analytical roles
    from backend.utils.analytical_roles import infer_analytical_roles
    roles = infer_analytical_roles(cols, dtypes)
    
    cat_cols = [c for c in cols if roles.get(c) == "categorical"]
    if not cat_cols:
        cat_cols = [c for c in cols if roles.get(c) in ("temporal", "identifier")]
        
    num_cols = [c for c in cols if roles.get(c) in ("measure", "derived_measure")]
    
    # Grouped stats for 1 categorical/key and 1 numeric column
    if len(cat_cols) == 1 and len(num_cols) == 1:
        cat_col = cat_cols[0]
        num_col = num_cols[0]
        
        valid_data = []
        for r in normalized_rows:
            cat_val = r.get(cat_col)
            num_val = r.get(num_col)
            if cat_val is not None and num_val is not None:
                try:
                    valid_data.append((str(cat_val), float(num_val)))
                except (ValueError, TypeError):
                    pass
                    
        if len(valid_data) >= 1:
            # Sort by numeric value descending
            valid_data.sort(key=lambda x: x[1], reverse=True)
            
            highest_cat, highest_val = valid_data[0]
            lowest_cat, lowest_val = valid_data[-1]
            
            derived["highest_category"] = {"column": cat_col, "value": highest_cat, "metric": num_col, "amount": highest_val}
            derived["lowest_category"] = {"column": cat_col, "value": lowest_cat, "metric": num_col, "amount": lowest_val}
            
            total_sum = sum(val for _, val in valid_data)
            if total_sum > 0:
                shares = []
                for cat, val in valid_data:
                    share = (val / total_sum) * 100
                    shares.append({"category": cat, "value": val, "share_percent": round(share, 2)})
                derived["category_shares"] = shares
                derived["top_category_share"] = shares[0]
                
            if len(valid_data) >= 2:
                sec_cat, sec_val = valid_data[1]
                diff = highest_val - lowest_val
                ratio = highest_val / lowest_val if lowest_val != 0 else float('inf')
                derived["highest_vs_lowest"] = {
                    "difference": round(diff, 4),
                    "ratio": round(ratio, 4)
                }
                
                top_diff = highest_val - sec_val
                top_ratio = highest_val / sec_val if sec_val != 0 else float('inf')
                derived["top_two_comparison"] = {
                    "first": highest_cat,
                    "second": sec_cat,
                    "difference": round(top_diff, 4),
                    "ratio": round(top_ratio, 4)
                }
                
    return derived

def generate_facts(question: str, query_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes deterministic statistical facts from the SQL query results.
    Avoids unnecessary computation by reading question intent.
    """
    facts = {}
    rows = query_result.get("rows", [])
    cols = query_result.get("columns", [])
    
    if not rows or not cols:
        return {"note": "No data returned from query."}
        
    facts["total_rows_returned"] = len(rows)
    facts["column_count"] = len(cols)
    
    # 1. Deterministic Scalar Output Representation
    if len(rows) == 1 and len(cols) == 1:
        val = rows[0]
        if isinstance(val, dict):
            val = val.get(cols[0])
        elif isinstance(val, (list, tuple)) and len(val) > 0:
            val = val[0]
        
        facts["result_type"] = "scalar"
        facts["metric_name"] = cols[0]
        facts["metric_value"] = val
        return facts

    # Provide data preview for small datasets so LLM gets visibility into rows
    if len(rows) <= 10:
        facts["data_preview"] = rows
        
    q_lower = question.lower()
    
    # Compute derived category summary stats (shares, ratios, top-two comparisons, etc.)
    derived = compute_derived_facts(query_result)
    if derived:
        facts["derived_comparisons"] = derived
    
    # If the result is very small and no explicit summary is requested, 
    # dimensions and preview are sufficient.
    if len(rows) <= 5 and not any(k in q_lower for k in ["average", "summary", "statistic"]):
        return facts
        
    try:
        # Convert to DataFrame for fast vectorized operations
        if isinstance(rows[0], dict):
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame(rows, columns=cols)
            
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        # Calculate summary stats if data is large or explicitly requested
        if len(rows) > 10 or any(k in q_lower for k in ["summary", "statistic", "average", "max", "min"]):
            stats = {}
            for col in numeric_cols:
                # Safely compute stats ignoring NaNs
                col_min = df[col].min()
                col_max = df[col].max()
                col_mean = df[col].mean()
                
                stats[col] = {
                    "min": float(col_min) if pd.notna(col_min) else None,
                    "max": float(col_max) if pd.notna(col_max) else None,
                    "mean": round(float(col_mean), 2) if pd.notna(col_mean) else None
                }
            if stats:
                facts["numeric_summary"] = stats
                
        # Compute specific metrics only if the question implies them
        if "missing" in q_lower or "null" in q_lower or "empty" in q_lower:
            facts["missing_values"] = df.isna().sum().to_dict()
            
        if "unique" in q_lower or "distinct" in q_lower or "category" in q_lower:
            cat_cols = df.select_dtypes(include=['object', 'string']).columns
            facts["unique_counts"] = {col: int(df[col].nunique()) for col in cat_cols}
            
        if "duplicate" in q_lower:
            facts["duplicate_rows"] = int(df.duplicated().sum())
            
    except Exception as e:
        facts["fact_generation_error"] = str(e)
        
    return facts
