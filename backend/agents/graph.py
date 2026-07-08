import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

# Import state schema
from backend.agents.state import AgentState

# Import nodes
from backend.agents.nodes.schema_profiler import schema_profiler_node
from backend.agents.nodes.planner import planner_node
from backend.agents.nodes.code_generator import code_generator_node
from backend.agents.nodes.sandbox_executor import sandbox_executor_node
from backend.agents.nodes.validator import validator_node
from backend.agents.nodes.reflection import reflection_node
from backend.agents.nodes.report_agent import report_agent_node
from backend.agents.nodes.visualization_generator import visualization_generator_node
from backend.agents.nodes.visualization_executor import visualization_executor_node
from backend.agents.nodes.visualization_reflection import visualization_reflection_node
from backend.agents.nodes.analysis_engine import analysis_engine_node

logger = logging.getLogger(__name__)

from backend.agents.nodes.supervisor import supervisor_node
from backend.agents.capability_registry import CAPABILITIES

def route_supervisor(state: AgentState) -> str:
    """
    Dynamic router reading the Supervisor's latest decision.
    """
    history = state.get("supervisor_history")
    if not history:
        logger.warning("No supervisor history found. Terminating.")
        return END
    
    last_decision = history[-1]
    if last_decision.get("decision") == "TERMINATE":
        logger.info("Supervisor decided to TERMINATE workflow.")
        return END
        
    cap_name = last_decision.get("selected_capability")
    if not cap_name or cap_name not in CAPABILITIES:
        logger.warning(f"Supervisor selected invalid capability: {cap_name}. Terminating.")
        return END
        
    target_node = CAPABILITIES[cap_name].entry_node
    logger.info(f"Supervisor routing to capability {cap_name} (node: {target_node})")
    return target_node

def create_agent_graph(pool) -> Any:
    """
    Builds, configures, and compiles the LangGraph StateGraph with the Postgres checkpointer.
    """
    logger.info("Initializing LangGraph StateGraph workflow...")
    
    workflow = StateGraph(AgentState)
    
    # Register Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("schema_profiler", schema_profiler_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("code_generator", code_generator_node)
    workflow.add_node("sandbox_executor", sandbox_executor_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("analysis_engine", analysis_engine_node)
    workflow.add_node("visualization_generator", visualization_generator_node)
    workflow.add_node("visualization_executor", visualization_executor_node)
    workflow.add_node("visualization_reflection", visualization_reflection_node)
    workflow.add_node("report_agent", report_agent_node)
    
    # Configure Static Edges
    workflow.set_entry_point("supervisor")
    
    # All worker chains eventually return to the supervisor
    workflow.add_edge("schema_profiler", "supervisor")
    workflow.add_edge("reflection", "supervisor")
    workflow.add_edge("analysis_engine", "supervisor")
    workflow.add_edge("visualization_reflection", "supervisor")
    workflow.add_edge("report_agent", "supervisor")
    
    # SQL Capability internal chain
    workflow.add_edge("planner", "code_generator")
    workflow.add_edge("code_generator", "sandbox_executor")
    workflow.add_edge("sandbox_executor", "validator")
    workflow.add_edge("validator", "reflection")
    
    # Visualization Capability internal chain
    workflow.add_edge("visualization_generator", "visualization_executor")
    workflow.add_edge("visualization_executor", "visualization_reflection")
    
    # Configure Dynamic Routing from Supervisor
    # Map valid return node strings to themselves, and map END
    supervisor_route_map = {cap.entry_node: cap.entry_node for cap in CAPABILITIES.values()}
    supervisor_route_map[END] = END

    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        supervisor_route_map
    )
    
    # Configure Checkpointer
    logger.info("Setting up LangGraph PostgresSaver checkpointer...")
    from langgraph.checkpoint.base import JsonPlusSerializer
    from backend.agents.schemas import ConfidenceLevel, ChartType
    
    # Configure strict serializer allowlist using public builder methods
    serde = JsonPlusSerializer(allowed_msgpack_modules=None).with_msgpack_allowlist(
        [ConfidenceLevel, ChartType]
    )
    
    # Initialize checkpointer and run setup DDL to create tables if they do not exist
    checkpointer = PostgresSaver(pool, serde=serde)
    checkpointer.setup()
    
    # Compile graph
    compiled_graph = workflow.compile(checkpointer=checkpointer)
    logger.info("LangGraph agent workflow compiled successfully.")
    
    return compiled_graph
