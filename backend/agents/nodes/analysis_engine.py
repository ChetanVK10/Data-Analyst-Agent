import time
import logging
import traceback
from typing import Dict, Any, Tuple, List, Optional
import pandas as pd
import numpy as np
import math

from backend.agents.state import AgentState, get_effective_question
from backend.services.session_manager import session_manager

logger = logging.getLogger(__name__)

def _load_data(state: AgentState) -> pd.DataFrame:
    table_name = state.get("duckdb_table") or state.get("dataset_id")
    if not table_name:
        raise ValueError("No dataset specified in state.")
    from backend.mcp.data_access import is_csv_session
    is_csv_session(state["session_id"])
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
    from backend.services.statistics import run_correlation
    return run_correlation(df)

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
    from backend.services.statistics import run_outlier
    return run_outlier(df)

def select_aggregation_method(column_name: str) -> str:
    """
    Selects the safe deterministic aggregation method (SUM or MEAN) 
    based on the column name.
    """
    col_lower = column_name.lower()
    
    # List of terms that are additive
    additive_terms = [
        "sales", "revenue", "amount", "quantity", "units", "cost", "profit", "count", "sum"
    ]
    # List of terms indicating rates/ratios/averages
    rate_terms = [
        "price", "pct", "percent", "margin", "rate", "score", "average", "avg", "mean", "ratio", "temperature"
    ]
    
    if any(t in col_lower for t in rate_terms):
        return "MEAN"
    if any(t in col_lower for t in additive_terms):
        return "SUM"
    return "MEAN"

def _run_trend(df: pd.DataFrame, question: str, time_col: Optional[str] = None) -> Dict[str, Any]:
    # Find all numeric columns (excluding the time column itself)
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c != time_col]
    if not numeric_cols:
        return {"trend": "No numeric metric columns for trend analysis."}
        
    col = numeric_cols[0]
    agg_method = select_aggregation_method(col)
    
    # Determine the grain requested in the question
    q_lower = question.lower()
    grain = "general"
    if "month" in q_lower or "monthly" in q_lower:
        grain = "monthly"
    elif "year" in q_lower or "yearly" in q_lower or "annual" in q_lower:
        grain = "yearly"
    elif "quarter" in q_lower or "quarterly" in q_lower or "qtr" in q_lower:
        grain = "quarterly"
    elif "day" in q_lower or "daily" in q_lower:
        grain = "daily"
        
    # If we have a time column, attempt temporal aggregation
    if time_col and time_col in df.columns:
        df_clean = df[[col, time_col]].dropna().copy()
        
        # Ensure it is parsed as datetime
        if not pd.api.types.is_datetime64_any_dtype(df_clean[time_col]):
            try:
                df_clean[time_col] = pd.to_datetime(df_clean[time_col])
            except Exception:
                pass
                
        # Perform grain default selection if "general" trend was requested
        if pd.api.types.is_datetime64_any_dtype(df_clean[time_col]) and len(df_clean) > 0:
            min_date = df_clean[time_col].min()
            max_date = df_clean[time_col].max()
            delta_days = (max_date - min_date).days
            
            if grain == "general":
                if delta_days <= 31:
                    grain = "daily"
                elif delta_days <= 730:
                    grain = "monthly"
                else:
                    unique_ym = df_clean[time_col].dt.to_period('M').nunique()
                    if unique_ym <= 120:
                        grain = "monthly"
                    else:
                        grain = "yearly"
                        
        # Derive chronological period key
        if pd.api.types.is_datetime64_any_dtype(df_clean[time_col]):
            if grain == "daily":
                period_series = df_clean[time_col].dt.to_period('D')
            elif grain == "monthly":
                period_series = df_clean[time_col].dt.to_period('M')
            elif grain == "quarterly":
                period_series = df_clean[time_col].dt.to_period('Q')
            elif grain == "yearly":
                period_series = df_clean[time_col].dt.to_period('Y')
            else:
                period_series = df_clean[time_col].dt.to_period('M')
        else:
            # Fallback to direct group if datetime parsing failed
            period_series = df_clean[time_col]
            
        # Group and aggregate metric
        df_agg = df_clean.groupby(period_series)[col].agg(agg_method.lower()).reset_index()
        # Sort chronologically
        df_agg = df_agg.sort_values(by=time_col)
        
        y = df_agg[col].values
        if len(y) < 2:
            return {"trend": "Insufficient data points after temporal aggregation."}
            
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat"
        
        series_list = []
        for idx, row in df_agg.iterrows():
            series_list.append({
                "period": str(row[time_col]),
                "value": float(row[col]) if not pd.isna(row[col]) else None
            })
            
        return {
            "trend_analysis": {
                "column": col,
                "direction": direction,
                "slope": float(slope),
                "temporal_column": time_col,
                "grain": grain,
                "aggregation": agg_method,
                "period_count": len(y),
                "series": series_list
            }
        }
        
    # Fallback to raw row sequence trend if no time column is present
    y = df[col].dropna().values
    if len(y) < 2:
        return {"trend": "Insufficient data points for trend analysis."}
        
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat"
    
    return {
        "trend_analysis": {
            "column": col,
            "direction": direction,
            "slope": float(slope),
            "temporal_column": None,
            "grain": "raw_sequence",
            "aggregation": "NONE",
            "period_count": len(y),
            "series": []
        }
    }
def resolve_requested_columns(question: str, schema_columns: list) -> list:
    import re
    def clean_str(s: str) -> str:
        return re.sub(r'[^a-z0-9]', '', s.lower())
    q_clean = clean_str(question)
    q_words = [clean_str(w) for w in question.split() if clean_str(w)]
    resolved = []
    for col in schema_columns:
        col_clean = clean_str(col)
        if not col_clean:
            continue
        if len(col_clean) <= 3:
            if col_clean in q_words:
                resolved.append(col)
        else:
            if col_clean in q_clean:
                resolved.append(col)
    return resolved

def resolve_temporal_column(question: str, df: pd.DataFrame) -> Optional[str]:
    """
    Resolves the single primary temporal/time column from the dataframe generically
    based on the requested temporal grain and column types/names.
    """
    from typing import Optional
    q_lower = question.lower()
    
    # 1. Identify requested grain
    grain = "general"
    if "month" in q_lower or "monthly" in q_lower:
        grain = "monthly"
    elif "year" in q_lower or "yearly" in q_lower or "annual" in q_lower:
        grain = "yearly"
    elif "quarter" in q_lower or "quarterly" in q_lower or "qtr" in q_lower:
        grain = "quarterly"
    elif "day" in q_lower or "daily" in q_lower:
        grain = "daily"
        
    # 2. Find datetime columns and numeric/string column candidates
    datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    
    # Helper to check if name matches grain keywords
    def matches_grain(col_name: str, gr: str) -> bool:
        col_lower = col_name.lower()
        if gr == "monthly":
            return "month" in col_lower or "mon" in col_lower
        if gr == "yearly":
            return "year" in col_lower or "yr" in col_lower or "ann" in col_lower
        if gr == "quarterly":
            return "quarter" in col_lower or "qtr" in col_lower
        if gr == "daily":
            return "day" in col_lower or "date" in col_lower
        return "date" in col_lower or "time" in col_lower

    # 3. Preference logic
    # Monthly: prefer monthly-grain column. Datetime columns are preferred to avoid multi-year collapse risk.
    if grain == "monthly":
        month_cols = [c for c in df.columns if matches_grain(c, "monthly")]
        if month_cols:
            if datetime_cols:
                return datetime_cols[0]
            return month_cols[0]
            
    # Yearly: prefer yearly-grain column
    elif grain == "yearly":
        year_cols = [c for c in df.columns if matches_grain(c, "yearly")]
        if year_cols:
            if datetime_cols:
                return datetime_cols[0]
            return year_cols[0]
            
    # Quarterly: prefer quarterly-grain column
    elif grain == "quarterly":
        qtr_cols = [c for c in df.columns if matches_grain(c, "quarterly")]
        if qtr_cols:
            if datetime_cols:
                return datetime_cols[0]
            return qtr_cols[0]

    # For general trend, or if no grain-specific column was found:
    # Prefer datetime columns first
    if datetime_cols:
        return datetime_cols[0]
        
    # Fallback to any date/time column names
    for c in df.columns:
        if matches_grain(c, "general") or any(t in c.lower() for t in ["date", "time", "year", "month", "day", "qtr"]):
            return c
            
    return None

def analysis_engine_node(state: AgentState) -> Dict[str, Any]:
    node_name = "analysis_engine"
    start_time = time.time()
    logger.info("--- ANALYSIS ENGINE ACTIVATED ---")
    
    question = get_effective_question(state).lower()
    
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
        
        # Resolve requested columns
        schema = state.get("schema_profile", {}) or {}
        schema_cols = [c["name"] for c in schema.get("columns", [])]
        resolved_cols = resolve_requested_columns(question, schema_cols)
        
        # Resolve temporal column for trend
        time_col = None
        if analysis_type == "trend":
            time_col = resolve_temporal_column(question, df)
            
        # Build effective scope preserving original column order:
        # 1. Explicitly requested columns first (in original dataframe column order)
        # 2. Time dimension column next if doing trend
        effective_cols = []
        for col in df.columns:
            if col in resolved_cols and col not in effective_cols:
                effective_cols.append(col)
        if time_col and time_col not in effective_cols:
            effective_cols.append(time_col)
            
        # Slicing the dataframe
        if resolved_cols or time_col:
            logger.info(f"Analysis scope: resolved={resolved_cols}, time_col={time_col} -> effective={effective_cols}")
            existing_resolved = [c for c in effective_cols if c in df.columns]
            if existing_resolved:
                df = df[existing_resolved]
                
                # If doing trend, sort chronologically by the resolved time column
                if time_col and time_col in df.columns:
                    if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
                        try:
                            df[time_col] = pd.to_datetime(df[time_col])
                        except Exception as de:
                            logger.warning(f"Could not parse temporal column {time_col} to datetime: {de}")
                    df = df.sort_values(by=time_col)
                    logger.info(f"Sorted trend dataframe chronologically by {time_col}")
            else:
                logger.warning("None of the resolved columns exist in the dataframe. Keeping original data.")
        else:
            logger.info("No explicit column scope resolved. Operating on all eligible columns.")
        
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
                from backend.mcp.client import invoke_mcp_tool_sync
                session_id = state.get("session_id")
                dataset_id = state.get("dataset_id")
                mcp_args = {"session_id": session_id, "dataset_id": dataset_id}
                if resolved_cols:
                    mcp_args["columns"] = resolved_cols
                mcp_res = invoke_mcp_tool_sync("calculate_correlation", mcp_args) if session_id and dataset_id else None
                if mcp_res is not None and not mcp_res.get("error"):
                    artifacts = mcp_res
                    logger.info("Computed correlation via MCP tool.")
                else:
                    logger.warning("MCP correlation failed. Falling back to internal function.")
                    artifacts = _run_correlation(df)
            elif analysis_type == "distribution":
                artifacts = _run_distribution(df)
            elif analysis_type == "outlier":
                from backend.mcp.client import invoke_mcp_tool_sync
                session_id = state.get("session_id")
                dataset_id = state.get("dataset_id")
                mcp_args = {"session_id": session_id, "dataset_id": dataset_id}
                if resolved_cols:
                    mcp_args["columns"] = resolved_cols
                mcp_res = invoke_mcp_tool_sync("detect_outliers", mcp_args) if session_id and dataset_id else None
                if mcp_res is not None and not mcp_res.get("error"):
                    artifacts = mcp_res
                    logger.info("Computed outliers via MCP tool.")
                else:
                    logger.warning("MCP outliers failed. Falling back to internal function.")
                    artifacts = _run_outlier(df)
            elif analysis_type == "trend":
                artifacts = _run_trend(df, question, time_col)
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
