import logging
import json
from fastmcp import FastMCP
from typing import Dict, Any, List, Optional

# Ensure we have paths set up properly in case this is run as a subprocess
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.mcp.data_access import get_schema
from backend.services.statistics import run_correlation, run_outlier
from backend.services.visualization.validator import is_result_chartable as validator_is_result_chartable
from backend.services.session_manager import session_manager

logger = logging.getLogger(__name__)

mcp = FastMCP("DataAgentTools")

@mcp.tool()
def get_dataset_schema(session_id: str, dataset_id: str) -> str:
    """
    Exposes dataset and schema discovery through MCP.
    """
    try:
        profile = get_schema(session_id, dataset_id)
        return json.dumps(profile)
    except Exception as e:
        logger.error(f"Error in get_dataset_schema tool: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def calculate_correlation(session_id: str, dataset_id: str, columns: Optional[List[str]] = None) -> str:
    """
    Calculates the correlation matrix for numeric columns in the dataset.
    """
    try:
        # Load the data via the existing subprocess-safe data access layer
        from backend.mcp.data_access import is_csv_session
        is_csv_session(session_id)
        
        conn = session_manager.get_session_connection(session_id)
        # Fetch the data into a pandas dataframe
        import pandas as pd
        df = conn.execute(f"SELECT * FROM {dataset_id};").df()
        
        result = run_correlation(df, columns)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in calculate_correlation tool: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def detect_outliers(session_id: str, dataset_id: str, columns: Optional[List[str]] = None) -> str:
    """
    Detects outliers in the numeric columns of the dataset.
    """
    try:
        # Load the data via the existing subprocess-safe data access layer
        from backend.mcp.data_access import is_csv_session
        is_csv_session(session_id)
        
        conn = session_manager.get_session_connection(session_id)
        # Fetch the data into a pandas dataframe
        import pandas as pd
        df = conn.execute(f"SELECT * FROM {dataset_id};").df()
        
        result = run_outlier(df, columns)
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error in detect_outliers tool: {e}")
        return json.dumps({"error": str(e)})

@mcp.tool()
def is_result_chartable(query_metadata_json: str) -> str:
    """
    Determines if a query result is structurally chartable.
    Input must be a JSON string of query_metadata.
    """
    try:
        if isinstance(query_metadata_json, str):
            query_metadata = json.loads(query_metadata_json)
        else:
            query_metadata = query_metadata_json
        result = validator_is_result_chartable(query_metadata)
        return json.dumps({"is_chartable": result})
    except Exception as e:
        logger.error(f"Error in is_chartable tool: {e}")
        return json.dumps({"error": str(e), "is_chartable": False})

if __name__ == "__main__":
    mcp.run(transport="stdio")
