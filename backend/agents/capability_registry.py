"""
capability_registry.py — Registry for dynamic Supervisor capability routing.

Defines the available logical capabilities the Supervisor can orchestrate, hiding
the internal LangGraph node topology.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class CapabilityDefinition(BaseModel):
    name: str = Field(..., description="Unique capability identifier.")
    entry_node: str = Field(..., description="LangGraph node acting as the entry point.")
    description: str = Field(..., description="What this capability achieves.")
    enabled: bool = Field(True, description="Whether this capability is currently active.")

# The Registry of capabilities
CAPABILITIES: Dict[str, CapabilityDefinition] = {
    "SCHEMA": CapabilityDefinition(
        name="SCHEMA",
        entry_node="schema_profiler",
        description="Extracts table structures, column definitions, and primary keys from the database.",
        enabled=True
    ),
    "SQL": CapabilityDefinition(
        name="SQL",
        entry_node="planner",
        description="Generates and executes SQL queries against the dataset to extract analytical results.",
        enabled=True
    ),
    "ANALYSIS": CapabilityDefinition(
        name="ANALYSIS",
        entry_node="analysis_engine",
        description="Performs deterministic statistical analysis (correlation, descriptive, distribution, trend, outliers).",
        enabled=True
    ),
    "VISUALIZATION": CapabilityDefinition(
        name="VISUALIZATION",
        entry_node="visualization_generator",
        description="Generates Python Plotly charts based on SQL query results.",
        enabled=True
    ),
    "PYTHON_ANALYSIS": CapabilityDefinition(
        name="PYTHON_ANALYSIS",
        entry_node="python_analyst",
        description="Executes complex calculations, rolling windows, regex text cleaning, and fuzzy matching via Python.",
        enabled=True
    ),
    "REPORT": CapabilityDefinition(
        name="REPORT",
        entry_node="report_agent",
        description="Synthesizes findings into a final structured analysis report and PDF.",
        enabled=True
    )
}

def get_enabled_capabilities() -> List[CapabilityDefinition]:
    return [cap for cap in CAPABILITIES.values() if cap.enabled]

def get_capability(name: str) -> Optional[CapabilityDefinition]:
    return CAPABILITIES.get(name)
