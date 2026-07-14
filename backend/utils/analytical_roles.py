import re
from typing import Dict, List

def tokenize_column_name(col_name: str) -> List[str]:
    """
    Normalizes a column name into tokens for safe matching.
    Handles camelCase, PascalCase, snake_case, spaces, hyphens.
    """
    # Replace hyphens and spaces with underscores
    col_name = col_name.replace('-', '_').replace(' ', '_')
    # Handle camelCase / PascalCase by inserting an underscore before uppercase letters
    # but not if the string is fully uppercase
    if not col_name.isupper():
        col_name = re.sub(r'(?<!^)(?=[A-Z])', '_', col_name)
    
    col_name = col_name.lower()
    tokens = [t for t in col_name.split('_') if t]
    return tokens

def infer_analytical_roles(columns: List[str], dtypes: Dict[str, str]) -> Dict[str, str]:
    """
    Deterministically infers analytical roles based on column names and physical types.
    Roles: temporal, identifier, categorical, measure, derived_measure
    """
    roles = {}
    
    temporal_tokens = {'date', 'datetime', 'timestamp', 'time', 'month', 'year', 'quarter', 'week', 'day'}
    identifier_tokens = {'id', 'identifier', 'ordernumber', 'order_number', 'code', 'key'}
    derived_measure_tokens = {'moving_average', 'rolling', 'cumulative', 'percentage', 'percent', 'ratio', 'growth', 'forecast', 'prediction', 'score', 'rate'}
    
    for col in columns:
        dtype = dtypes.get(col, "unknown")
        tokens = tokenize_column_name(col)
        
        # 1. Temporal Check
        if dtype == "datetime":
            roles[col] = "temporal"
            continue
            
        if any(t in temporal_tokens for t in tokens):
            roles[col] = "temporal"
            continue
            
        # 2. Identifier Check
        # Check exact tokens or suffix (e.g., _id)
        if any(t in identifier_tokens for t in tokens):
            roles[col] = "identifier"
            continue
            
        # 3. Derived Measure Check
        # Some tokens might span multiple words (e.g., moving_average) - check raw string for those
        col_lower = col.lower()
        if any(t in derived_measure_tokens for t in tokens) or "moving_average" in col_lower or "rolling" in col_lower:
            roles[col] = "derived_measure"
            continue
            
        # 4. Defaults based on physical type
        if dtype == "number":
            roles[col] = "measure"
        else:
            roles[col] = "categorical"
            
    return roles
