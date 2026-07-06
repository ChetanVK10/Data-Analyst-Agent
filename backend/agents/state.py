from typing import TypedDict, Optional, Dict, Any, List

class FailureSummary(TypedDict):
    failure_type: str        # 'runtime' | 'structural' | 'semantic' | 'timeout' | 'visualization'
    error_message: str       # Shortened, high-level summary of the error
    code_context: str        # Specific lines of code / SQL statement that failed
    expected_vs_actual: str  # Diff or mismatch description (e.g., expected 3 columns, got 1)

class AgentState(TypedDict):
    # Core Identification
    session_id: str
    dataset_id: str
    duckdb_table: str
    
    # Metadata & Inputs
    schema_profile: Dict[str, Any]
    question: str
    
    # Execution Plan & Intermediates
    plan: Optional[Dict[str, Any]]
    generated_code: Optional[str]         # Raw generated SQL or Python code
    expected_output_type: Optional[str]   # e.g., 'dataframe', 'scalar', 'chart'
    
    # Lightweight Execution Outputs (NO large DataFrames)
    execution_success: bool
    execution_time_ms: float
    output_summary: Optional[Dict[str, Any]] # e.g., {'columns': [...], 'row_count': 10, 'preview': [...]}
    
    # Complete SQL query result (stored for Python visualization generator)
    query_result: Optional[Dict[str, Any]]
    
    # Validation & Routing
    validation_passed: bool
    failure_summary: Optional[FailureSummary]
    retry_count: int
    retry_target: Optional[str]           # 'planner' | 'code_generator' | 'report_agent'
    graceful_failure: bool
    
    # History of failures for context context
    retry_history: List[FailureSummary]
    
    # Visualization specific routing & intermediates
    vis_generated_code: Optional[str]
    vis_retry_count: int
    vis_retry_history: List[FailureSummary]
    
    # Final Output Specs (Plotly JSON, Narrative markdown, PDF file path)
    final_report: Optional[Dict[str, Any]]
