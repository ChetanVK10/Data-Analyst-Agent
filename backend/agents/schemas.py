"""
schemas.py — Canonical Pydantic models for the AnalysisResponse contract.

Every layer of the system (report_agent, /analyze endpoint, PDF generator,
frontend types) derives from these models.  There is ONE representation of
each concept — no duplicate fields across the response tree.
"""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


# ─────────────────────────────────────────────
# Enumerated value types
# ─────────────────────────────────────────────

class ConfidenceLevel(str, Enum):
    HIGH   = "High"
    MEDIUM = "Medium"
    LOW    = "Low"


class ChartType(str, Enum):
    BAR        = "bar"
    LINE       = "line"
    PIE        = "pie"
    SCATTER    = "scatter"
    HISTOGRAM  = "histogram"
    AREA       = "area"
    HEATMAP    = "heatmap"
    OTHER      = "other"


# ─────────────────────────────────────────────
# Report sub-models
# ─────────────────────────────────────────────

class ExecutiveSummary(BaseModel):
    """The highest-priority visual block.  Always rendered first."""
    headline:   str = Field(..., description="One-sentence direct answer to the question")
    summary:    str = Field(..., description="2-3 paragraph business narrative with key findings")
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH


class TableResult(BaseModel):
    """A fully self-contained result table.  No separate tableData field."""
    title:   str        = Field(..., description="Descriptive table title")
    columns: List[str]  = Field(..., description="Column header labels")
    rows:    List[List[Any]] = Field(default_factory=list, description="All result rows as arrays")


class ChartSpec(BaseModel):
    """
    Plotly chart specification.  This is the ONE place charts are stored —
    there is no separate chartJson field anywhere in the system.
    """
    title:       str       = Field(..., description="Chart title shown above the plot")
    type:        ChartType = Field(ChartType.BAR, description="Chart family for icon/labelling")
    plotly_json: dict      = Field(..., description="Complete Plotly figure JSON (data + layout)")


class Insight(BaseModel):
    """A single key finding extracted from the data."""
    title: str = Field(..., description="4-6 word summary of the insight")
    body:  str = Field(..., description="Full insight paragraph with evidence")


class Recommendation(BaseModel):
    """A single actionable recommendation derived from the findings."""
    title: str = Field(..., description="4-6 word action title")
    body:  str = Field(..., description="Full recommendation with rationale")


# ─────────────────────────────────────────────
# Top-level envelope sections
# ─────────────────────────────────────────────

class DatasetInfo(BaseModel):
    """
    Dataset context embedded in every response so downstream consumers
    (PDF, analytics, history cards) never need an extra API call.
    """
    name:    str = Field(..., description="Dataset identifier / filename")
    rows:    int = Field(..., description="Total row count")
    columns: int = Field(..., description="Total column count")


class QueryInfo(BaseModel):
    """Execution provenance — who, when, how many retries."""
    question:         str            = Field(..., description="Original user question")
    execution_time_ms: float         = Field(0.0, description="Wall-clock time in milliseconds")
    execution_id:     Optional[int]  = Field(None, description="Postgres report row ID for PDF link")
    provider:         str            = Field("Groq",                    description="LLM provider name")
    model:            str            = Field("llama-3.3-70b-versatile", description="Model identifier")
    retry_count:      int            = Field(0,   description="Number of agent retries")


class ReportSection(BaseModel):
    """
    The full analytical report.  Every data artefact lives here —
    tables, charts, insights, recommendations.
    """
    title:             str                    = Field(..., description="Auto-generated report title")
    executive_summary: ExecutiveSummary
    tables:            List[TableResult]      = Field(default_factory=list)
    charts:            List[ChartSpec]        = Field(default_factory=list)
    insights:          List[Insight]          = Field(default_factory=list)
    recommendations:   List[Recommendation]   = Field(default_factory=list)


class DebugInfo(BaseModel):
    """
    Developer/debug block.  Named 'debug' not 'technical' so it can grow
    to include prompt, tokens, latency breakdown, retry chain, etc.
    """
    generated_sql:  Optional[str] = Field(None, description="Final SQL statement executed")
    execution_plan: Optional[str] = Field(None, description="Planner steps as a readable string")
    llm_reasoning:  Optional[str] = Field(None, description="LLM explanation of its approach")


# ─────────────────────────────────────────────
# Root response model
# ─────────────────────────────────────────────

class AnalysisResponse(BaseModel):
    """
    Root object returned by POST /analyze.

    Single source of truth — no field is duplicated between sections.
    - Charts   → report.charts[].plotly_json  (not a separate chartJson)
    - Tables   → report.tables[].rows         (not a separate tableData)
    - SQL      → debug.generated_sql          (not in report)
    - Dataset  → dataset.*                    (self-contained, no extra call needed)
    """
    success: bool
    dataset: DatasetInfo
    query:   QueryInfo
    report:  ReportSection
    debug:   DebugInfo


# ─────────────────────────────────────────────
# Failure envelope (graceful degradation)
# ─────────────────────────────────────────────

class FailureResponse(BaseModel):
    """
    Returned when the agent exhausts retries without producing a valid result.
    Matches the same top-level shape so the frontend can use a single type guard.
    """
    success:      bool          = False
    dataset:      DatasetInfo
    query:        QueryInfo
    error_title:  str           = "Analysis Failed"
    error_detail: str           = "The agent could not resolve a correct answer within the retry budget."
    debug:        DebugInfo


# ─────────────────────────────────────────────
# LLM JSON output model (internal only)
# ─────────────────────────────────────────────

class LLMReportOutput(BaseModel):
    """
    What the report_agent LLM is asked to produce.
    Intentionally smaller than the full AnalysisResponse —
    the envelope fields (dataset, query, debug) are injected by the
    node/endpoint, not by the LLM.
    """
    title:             str
    executive_summary: ExecutiveSummary
    insights:          List[Insight]          = Field(default_factory=list)
    recommendations:   List[Recommendation]   = Field(default_factory=list)
    llm_reasoning:     Optional[str]          = Field(None, description="Optional: LLM's reasoning chain")
