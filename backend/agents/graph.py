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

logger = logging.getLogger(__name__)

def route_reflection(state: AgentState) -> str:
    """
    Conditional router function returning the target node determined in reflection.
    """
    target = state.get("retry_target", "report_agent")
    logger.info(f"Routing conditional edge: 'reflection' -> '{target}'")
    
    if target == "planner":
        return "planner"
    elif target == "code_generator":
        return "code_generator"
    elif target == "visualization_generator":
        return "visualization_generator"
    else:
        return "report_agent"

def route_visualization_reflection(state: AgentState) -> str:
    """
    Conditional router for visualization errors / recovery.
    """
    target = state.get("retry_target", "report_agent")
    logger.info(f"Routing conditional edge: 'visualization_reflection' -> '{target}'")
    
    if target == "visualization_generator":
        return "visualization_generator"
    else:
        return "report_agent"

def create_agent_graph(pool) -> Any:
    """
    Builds, configures, and compiles the LangGraph StateGraph with the Postgres checkpointer.
    """
    logger.info("Initializing LangGraph StateGraph workflow...")
    
    workflow = StateGraph(AgentState)
    
    # Register Nodes
    workflow.add_node("schema_profiler", schema_profiler_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("code_generator", code_generator_node)
    workflow.add_node("sandbox_executor", sandbox_executor_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("visualization_generator", visualization_generator_node)
    workflow.add_node("visualization_executor", visualization_executor_node)
    workflow.add_node("visualization_reflection", visualization_reflection_node)
    workflow.add_node("report_agent", report_agent_node)
    
    # Configure Static Edges
    workflow.set_entry_point("schema_profiler")
    workflow.add_edge("schema_profiler", "planner")
    workflow.add_edge("planner", "code_generator")
    workflow.add_edge("code_generator", "sandbox_executor")
    workflow.add_edge("sandbox_executor", "validator")
    workflow.add_edge("validator", "reflection")
    
    # Visualization path static edges
    workflow.add_edge("visualization_generator", "visualization_executor")
    workflow.add_edge("visualization_executor", "visualization_reflection")
    
    # Configure Conditional Routing
    workflow.add_conditional_edges(
        "reflection",
        route_reflection,
        {
            "planner": "planner",
            "code_generator": "code_generator",
            "visualization_generator": "visualization_generator",
            "report_agent": "report_agent"
        }
    )
    
    workflow.add_conditional_edges(
        "visualization_reflection",
        route_visualization_reflection,
        {
            "visualization_generator": "visualization_generator",
            "report_agent": "report_agent"
        }
    )
    
    # Finish workflow
    workflow.add_edge("report_agent", END)
    
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
