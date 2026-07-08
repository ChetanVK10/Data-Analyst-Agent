import time
import logging
import traceback
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
import math

from backend.agents.state import AgentState
from backend.services.session_manager import session_manager

logger = logging.getLogger(__name__)

def _load_data(state: AgentState) -> pd.DataFrame:
    table_name = state.get("duckdb_table") or state.get("dataset_id")
    if not table_name:
        raise ValueError("No dataset specified in state.")
    conn = session_manager.get_session_connection(state["session_id"])
    query = f"SELECT * FROM {table_name}"
    df = conn.execute(query).df()
    return df

def _validate_capability(df: pd.DataFrame, analysis_type: str) -> Tuple[bool, str]:
    if len(df) < 5:
        return False, "Insufficient data rows (minimum 5 required)."
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if analysis_type in ["correlation", "descriptive", "outlier", "distribution"]:
        if len(numeric_cols) < 1:
            return False, "At least one numeric column is required."
        if analysis_type == "correlation" and len(numeric_cols) < 2:
            return False, "At least two numeric columns are required for correlation analysis."
            
    if analysis_type == "trend":
        # Check for date or datetime columns
        date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        if not date_cols and len(numeric_cols) < 2:
            return False, "Trend analysis requires a datetime column or at least two numeric columns for sequence regression."
            
    return True, "Validation passed."

def _compute_confidence(df: pd.DataFrame) -> float:
    # A simple metric: proportion of non-null values
    total_cells = df.size
    if total_cells == 0:
        return 0.0
    null_cells = df.isna().sum().sum()
    confidence = 1.0 - (null_cells / total_cells)
    return round(max(0.1, min(1.0, float(confidence))), 2)

# --- Statistical Implementations ---
def _run_descriptive(df: pd.DataFrame) -> Dict[str, Any]:
    desc = df.describe(include='all').to_dict()
    # clean nan values for json serialization
    for col, stats in desc.items():
        for k, v in stats.items():
            if isinstance(v, float) and math.isnan(v):
                desc[col][k] = None
    return {"descriptive_stats": desc}

def _run_correlation(df: pd.DataFrame) -> Dict[str, Any]:
    numeric_df = df.select_dtypes(include=[np.number])
    corr_matrix = numeric_df.corr().to_dict()
    for col, stats in corr_matrix.items():
        for k, v in stats.items():
            if pd.isna(v):
                corr_matrix[col][k] = None
    return {"correlation_matrix": corr_matrix}

def _run_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    numeric_df = df.select_dtypes(include=[np.number])
    results = {}
    for col in numeric_df.columns:
        skew = float(numeric_df[col].skew())
        kurt = float(numeric_df[col].kurt())
        results[col] = {
            "skewness": skew if not pd.isna(skew) else None,
            "kurtosis": kurt if not pd.isna(kurt) else None
        }
    return {"distributions": results}

def _run_outlier(df: pd.DataFrame) -> Dict[str, Any]:
    numeric_df = df.select_dtypes(include=[np.number])
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

def _run_trend(df: pd.DataFrame) -> Dict[str, Any]:
    # Very basic linear trend on first numeric column
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.empty:
        return {"trend": "No numeric columns for trend"}
    
    col = numeric_df.columns[0]
    y = numeric_df[col].dropna().values
    if len(y) < 2:
        return {"trend": "Insufficient data points"}
        
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat"
    
    return {
        "trend_analysis": {
            "column": col,
            "direction": direction,
            "slope": float(slope)
        }
    }

def analysis_engine_node(state: AgentState) -> Dict[str, Any]:
    node_name = "analysis_engine"
    start_time = time.time()
    logger.info("--- ANALYSIS ENGINE ACTIVATED ---")
    
    question = state.get("question", "").lower()
    
    # 1. Dispatcher Logic
    if "correlat" in question or "relationship" in question:
        analysis_type = "correlation"
    elif "distribut" in question or "spread" in question:
        analysis_type = "distribution"
    elif "outlier" in question or "anomal" in question:
        analysis_type = "outlier"
    elif "trend" in question or "over time" in question:
        analysis_type = "trend"
    else:
        analysis_type = "descriptive"
        
    logger.info(f"Dispatcher selected analysis_type: {analysis_type}")
    
    status = "success"
    summary = f"Completed {analysis_type} analysis."
    artifacts = {}
    confidence = 0.0
    
    try:
        df = _load_data(state)
        
        # 2. Capability Validation
        is_valid, validation_msg = _validate_capability(df, analysis_type)
        if not is_valid:
            status = "failed"
            summary = f"Capability Validation Failed: {validation_msg}"
            logger.warning(summary)
            artifacts = {"validation_error": validation_msg, "suggested_alternative": "Review dataset schema for applicable capabilities."}
        else:
            # 3. Execution
            confidence = _compute_confidence(df)
            
            if analysis_type == "correlation":
                artifacts = _run_correlation(df)
            elif analysis_type == "distribution":
                artifacts = _run_distribution(df)
            elif analysis_type == "outlier":
                artifacts = _run_outlier(df)
            elif analysis_type == "trend":
                artifacts = _run_trend(df)
            else:
                artifacts = _run_descriptive(df)
                
    except Exception as e:
        status = "failed"
        summary = f"Analysis Engine execution crashed: {str(e)}"
        logger.error(summary)
        logger.error(traceback.format_exc())
        artifacts = {"error": str(e)}
        
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000
    
    worker_result = {
        "worker_name": "ANALYSIS",
        "status": status,
        "confidence": confidence,
        "summary": summary,
        "routing_hint": "REPORT", # Route directly to report for generic stats presentation
        "analysis_type": analysis_type,
        "duration_ms": duration_ms
    }
    
    node_metadata = {
        "node_name": node_name,
        "start_time": start_time,
        "end_time": end_time,
        "duration_ms": duration_ms,
        "status": status,
        "retry_count": 0,
        "error_message": summary if status == "failed" else None
    }
    
    execution_metadata = list(state.get("execution_metadata") or [])
    execution_metadata.append(node_metadata)
    
    return {
        "analysis_artifacts": artifacts,
        "last_worker_result": worker_result,
        "execution_metadata": execution_metadata
    }
