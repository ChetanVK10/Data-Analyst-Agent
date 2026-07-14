import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

def run_correlation(df: pd.DataFrame, columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """Calculates correlation matrix for numeric columns."""
    numeric_df = df.select_dtypes(include=[np.number])
    if columns:
        valid_cols = [c for c in columns if c in numeric_df.columns]
        numeric_df = numeric_df[valid_cols]
    corr_matrix = numeric_df.corr().to_dict()
    for col, stats in corr_matrix.items():
        for k, v in stats.items():
            if pd.isna(v):
                corr_matrix[col][k] = None
    return {"correlation_matrix": corr_matrix}

def run_outlier(df: pd.DataFrame, columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """Detects outlier counts and bounds for numeric columns."""
    numeric_df = df.select_dtypes(include=[np.number])
    if columns:
        valid_cols = [c for c in columns if c in numeric_df.columns]
        numeric_df = numeric_df[valid_cols]
    results = {}
    for col in numeric_df.columns:
        Q1 = numeric_df[col].quantile(0.25)
        Q3 = numeric_df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        outliers_count = int(((numeric_df[col] < lower) | (numeric_df[col] > upper)).sum())
        results[col] = {
            "outlier_count": outliers_count,
            "lower_bound": float(lower),
            "upper_bound": float(upper)
        }
    return {"outliers": results}
