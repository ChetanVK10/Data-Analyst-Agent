from typing import TypedDict, Optional, Dict, Any, List

class FailureSummary(TypedDict):
    failure_type: str        # 'runtime' | 'structural' | 'semantic' | 'timeout' | 'visualization'
    error_message: str       # Shortened, high-level summary of the error
    code_context: str        # Specific lines of code / SQL statement that failed
    expected_vs_actual: str  # Diff or mismatch description (e.g., expected 3 columns, got 1)

class WorkerResult(TypedDict, total=False):
    worker_name: str
    status: str              # 'success' or 'failed'
    confidence: float        # 0.0 to 1.0 confidence score
    summary: str             # Outcome summary or failure diagnostics
    routing_hint: Optional[str] # Hint to the Supervisor, e.g., 'SQL', 'VISUALIZATION', 'TERMINATE'
    analysis_type: Optional[str] # e.g. 'correlation', 'descriptive_stats', 'trend'
    duration_ms: Optional[float]
    token_usage: Optional[int]
    estimated_cost: Optional[float]

class SupervisorDecision(TypedDict, total=False):
    decision: str            # 'CONTINUE', 'RETRY', 'TERMINATE'
    reasoning: str           # Why the supervisor made this decision
    selected_capability: Optional[str] # E.g., 'SQL', 'VISUALIZATION', 'REPORT'
    timestamp: float         # When the decision was made
    is_follow_up: Optional[bool] # Whether the question is a follow-up to the previous context
    resolved_question: Optional[str] # The standalone resolved question if follow-up, or original question if new

class AgentState(TypedDict):
    # Core Identification
    session_id: str
    dataset_id: str
    duckdb_table: str
    
    # Metadata & Inputs
    schema_profile: Dict[str, Any]
    question: str
    resolved_question: Optional[str]
    conversational_context: Optional[Dict[str, Any]]
    
    # Execution Plan & Intermediates
    plan: Optional[Dict[str, Any]]
    generated_code: Optional[str]         # Raw generated SQL or Python code
    expected_output_type: Optional[str]   # e.g., 'dataframe', 'scalar', 'chart'
    
    # Lightweight Execution Outputs (NO large DataFrames)
    execution_success: bool
    execution_time_ms: float
    output_summary: Optional[Dict[str, Any]] # e.g., {'columns': [...], 'row_count': 10, 'preview': [...]}
    
    # Complete query result (stored for Python visualization generator)
    # Includes: columns, dtypes, rows, row_count, analytical_roles
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
    vis_spec: Optional[Dict[str, Any]]
    vis_generated_code: Optional[str]
    vis_retry_count: int
    vis_retry_history: List[FailureSummary]
    
    # Final Output Specs (Plotly JSON, Narrative markdown, PDF file path)
    final_report: Optional[Dict[str, Any]]
    
    # Telemetry and Execution Observability
    execution_metadata: Optional[List[Dict[str, Any]]]
    
    # Phase 2 Supervisor & Worker State
    last_worker_result: Optional[WorkerResult]
    supervisor_history: List[SupervisorDecision]
    overall_confidence: float
    
    # Phase 3 Generic Analysis State
    analysis_artifacts: Optional[Dict[str, Any]]

def get_effective_question(state: dict) -> str:
    """Returns the resolved standalone question if available, otherwise the original question."""
    resolved = state.get("resolved_question")
    if resolved and str(resolved).strip():
        return str(resolved).strip()
    return str(state.get("question", "")).strip()
