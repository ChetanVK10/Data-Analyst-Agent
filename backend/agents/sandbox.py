import os
import sys
import subprocess
import shutil
import logging
import json
import duckdb
from typing import Dict, Any, Tuple
from backend.services.session_manager import session_manager
from backend.config import SANDBOX_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# Base scratch directory in workspace
SCRATCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scratch"))

def prepare_scratch_directory(session_id: str, dataset_id: str) -> str:
    """
    Prepares a clean scratch directory for the session and exports the active table to CSV.
    """
    session_dir = os.path.join(SCRATCH_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    csv_path = os.path.join(session_dir, f"{dataset_id}.csv")
    
    # If the CSV doesn't exist in the scratch dir yet, export it from DuckDB
    if not os.path.exists(csv_path):
        logger.info(f"Exporting in-memory DuckDB table {dataset_id} to {csv_path} for Python execution...")
        try:
            conn = session_manager.get_session_connection(session_id)
            # Export table to CSV
            conn.execute(f"COPY {dataset_id} TO '{csv_path.replace(os.sep, '/')}' (HEADER, DELIMITER ',');")
        except Exception as e:
            logger.error(f"Failed to export table to CSV for sandbox: {e}")
            raise
            
    return session_dir

def run_python_in_sandbox(session_id: str, dataset_id: str, code: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Runs Python code inside a restricted subprocess sandbox.
    Returns: (success, error_message, outputs_dict)
    """
    try:
        session_dir = prepare_scratch_directory(session_id, dataset_id)
    except Exception as e:
        return False, f"Failed to initialize sandbox directory: {e}", {}

    script_path = os.path.join(session_dir, "sandbox_run.py")
    
    # Write the generated code to a file
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(code)

    logger.info(f"Executing Python script in sandbox process. Timeout: {SANDBOX_TIMEOUT_SECONDS}s")
    
    # Determine the python executable to use (matching our virtualenv if active)
    python_exe = sys.executable
    
    try:
        # Run subprocess with timeout
        result = subprocess.run(
            [python_exe, "sandbox_run.py"],
            cwd=session_dir,
            capture_output=True,
            text=True,
            timeout=SANDBOX_TIMEOUT_SECONDS
        )
        
        # Check execution status
        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"Process exited with code {result.returncode}"
            logger.warning(f"Sandbox execution failed: {error_msg}")
            return False, error_msg, {}

        # Success - check for generated files (chart.json, report.pdf)
        outputs = {}
        
        chart_path = os.path.join(session_dir, "chart.json")
        if os.path.exists(chart_path):
            try:
                with open(chart_path, "r") as f:
                    outputs["chart_json"] = json.load(f)
                logger.info("Found generated chart.json in sandbox.")
            except Exception as e:
                logger.error(f"Failed to read chart.json from sandbox: {e}")
                return False, f"Generated chart.json was malformed: {e}", {}
                
        pdf_path = os.path.join(session_dir, "report.pdf")
        if os.path.exists(pdf_path):
            # Move PDF to a more permanent location or keep in scratch and return path
            # We will keep in scratch for download
            outputs["pdf_path"] = pdf_path
            logger.info("Found generated report.pdf in sandbox.")

        return True, "", outputs

    except subprocess.TimeoutExpired:
        logger.warning(f"Sandbox execution timed out after {SANDBOX_TIMEOUT_SECONDS}s")
        return False, f"Execution Timeout: Code execution took longer than {SANDBOX_TIMEOUT_SECONDS} seconds.", {}
    except Exception as e:
        logger.error(f"Exception during sandbox execution: {e}")
        return False, str(e), {}
    finally:
        # Clean up code file, but keep output files for retrieval
        try:
            if os.path.exists(script_path):
                os.remove(script_path)
        except Exception:
            pass
