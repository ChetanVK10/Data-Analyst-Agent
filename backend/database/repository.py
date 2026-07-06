import json
import logging
from datetime import date
from typing import Dict, List, Optional, Any
from backend.database.connection import get_db_connection

logger = logging.getLogger(__name__)

def create_session(session_id: str, dataset_id: str, dataset_name: Optional[str] = None, user_id: int = 1) -> Dict[str, Any]:
    """Creates a new user session mapping to a dataset."""
    query = """
        INSERT INTO sessions (id, user_id, dataset_id, dataset_name)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE 
        SET dataset_id = EXCLUDED.dataset_id, dataset_name = EXCLUDED.dataset_name
        RETURNING *;
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (session_id, user_id, dataset_id, dataset_name))
                return cur.fetchone()
    except Exception as e:
        logger.error(f"Failed to create session in Postgres: {e}")
        return {"id": session_id, "user_id": user_id, "dataset_id": dataset_id, "dataset_name": dataset_name}

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves session details by session_id."""
    query = "SELECT * FROM sessions WHERE id = %s;"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (session_id,))
                return cur.fetchone()
    except Exception as e:
        logger.error(f"Failed to get session from Postgres: {e}")
        return None

def save_report(
    session_id: str, 
    question: str, 
    narrative_summary: Optional[str], 
    chart_plotly_json: Optional[Dict], 
    pdf_file_path: Optional[str], 
    execution_time_ms: float, 
    success: bool
) -> Dict[str, Any]:
    """Saves the final generated report of an analysis run."""
    query = """
        INSERT INTO reports (session_id, question, narrative_summary, chart_plotly_json, pdf_file_path, execution_time_ms, success)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING *;
    """
    plotly_str = json.dumps(chart_plotly_json) if chart_plotly_json else None
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (session_id, question, narrative_summary, plotly_str, pdf_file_path, execution_time_ms, success))
                return cur.fetchone()
    except Exception as e:
        logger.error(f"Failed to save report in Postgres: {e}")
        return {
            "session_id": session_id,
            "question": question,
            "narrative_summary": narrative_summary,
            "chart_plotly_json": chart_plotly_json,
            "pdf_file_path": pdf_file_path,
            "execution_time_ms": execution_time_ms,
            "success": success
        }

def get_reports_by_session(session_id: str) -> List[Dict[str, Any]]:
    """Gets all historical reports for a given session."""
    query = "SELECT * FROM reports WHERE session_id = %s ORDER BY created_at DESC;"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (session_id,))
                return cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch reports for session {session_id}: {e}")
        return []

def record_execution_metrics(success_type: str, failure_type: Optional[str] = None):
    """
    Increments daily statistics for dashboard analytics.
    - success_type: 'first_try' | 'retry_success' | 'failed'
    - failure_type: 'runtime' | 'structural' | 'semantic' | 'timeout' | 'visualization'
    """
    today = date.today()
    
    # Base select query to see if today exists
    select_query = "SELECT id, common_failure_types FROM metrics WHERE execution_date = %s;"
    
    # Increments
    first_try_inc = 1 if success_type == "first_try" else 0
    retry_success_inc = 1 if success_type == "retry_success" else 0
    failed_inc = 1 if success_type == "failed" else 0
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(select_query, (today,))
                row = cur.fetchone()
                
                if row:
                    # Update existing day
                    common_failures = row.get("common_failure_types") or {}
                    if failure_type:
                        common_failures[failure_type] = common_failures.get(failure_type, 0) + 1
                    
                    update_query = """
                        UPDATE metrics 
                        SET total_executions = total_executions + 1,
                            first_try_success_count = first_try_success_count + %s,
                            retry_success_count = retry_success_count + %s,
                            failed_count = failed_count + %s,
                            common_failure_types = %s
                        WHERE id = %s;
                    """
                    cur.execute(update_query, (first_try_inc, retry_success_inc, failed_inc, json.dumps(common_failures), row["id"]))
                else:
                    # Insert new day
                    common_failures = {failure_type: 1} if failure_type else {}
                    insert_query = """
                        INSERT INTO metrics (execution_date, total_executions, first_try_success_count, retry_success_count, failed_count, common_failure_types)
                        VALUES (%s, 1, %s, %s, %s, %s);
                    """
                    cur.execute(insert_query, (today, first_try_inc, retry_success_inc, failed_inc, json.dumps(common_failures)))
    except Exception as e:
        logger.error(f"Failed to record execution metrics: {e}")

def get_metrics_summary() -> List[Dict[str, Any]]:
    """Gets historical metrics for the dashboard."""
    query = "SELECT * FROM metrics ORDER BY execution_date DESC LIMIT 30;"
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                return cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return []
