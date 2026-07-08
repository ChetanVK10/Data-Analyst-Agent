import time
import logging
from typing import Dict, Any

from backend.agents.state import AgentState, SupervisorDecision
from backend.agents.capability_registry import get_enabled_capabilities, get_capability

logger = logging.getLogger(__name__)

import json
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import get_llm

def _get_llm_routing_decision(state: AgentState) -> SupervisorDecision:
    """
    Invokes the LLM to decide the next capability based on the current state.
    """
    logger.info("Supervisor LLM reasoning required for dynamic routing...")
    
    question = state.get("question", "")
    last_worker_result = state.get("last_worker_result", {})
    worker_name = last_worker_result.get("worker_name", "UNKNOWN")
    
    system_prompt = f"""You are the Supervisor Agent for an Autonomous Data Analyst.
Your job is to route the workflow to the correct capability.

AVAILABLE CAPABILITIES:
- SQL: Generates and executes SQL queries to answer questions about the data.
- ANALYSIS: Performs deterministic statistical analysis (correlation, descriptive, distribution, trend, outliers).
- VISUALIZATION: Generates Plotly charts.
- REPORT: Synthesizes findings into a final report.

The last worker to run was {worker_name}.

Analyze the user's question and decide the next logical capability.
If the question asks for statistical analysis like correlation, trend, distribution, or outliers, choose ANALYSIS.
If the question asks for data retrieval, grouping, or general querying, choose SQL.

Respond ONLY with a JSON object in this format:
{{
    "decision": "CONTINUE",
    "reasoning": "Explain why you chose this capability.",
    "selected_capability": "SQL"
}}
"""
    try:
        llm = get_llm(temperature=0.0)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Question: {question}")
        ])
        
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        decision_data = json.loads(content.strip())
        return {
            "decision": decision_data.get("decision", "CONTINUE"),
            "reasoning": decision_data.get("reasoning", "LLM decided fallback route."),
            "selected_capability": decision_data.get("selected_capability", "REPORT"),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Supervisor LLM error: {e}")
        return {
            "decision": "CONTINUE",
            "reasoning": "Fallback to SQL due to LLM error.",
            "selected_capability": "SQL",
            "timestamp": time.time()
        }

def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    The central orchestration node.
    Consumes the state (and last_worker_result) to decide the next capability.
    """
    node_name = "supervisor"
    start_time = time.time()
    
    logger.info(f"--- SUPERVISOR ACTIVATED ---")
    
    last_worker_result = state.get("last_worker_result")
    supervisor_history = list(state.get("supervisor_history") or [])
    schema_profile = state.get("schema_profile")
    
    decision = "CONTINUE"
    reasoning = ""
    selected_cap = None
    
    # 1. Deterministic Initialization
    if not schema_profile:
        reasoning = "Schema profile is missing. Routing to SCHEMA capability."
        selected_cap = "SCHEMA"
    
    # 2. Process Last Worker Result
    elif last_worker_result:
        worker_name = last_worker_result.get("worker_name")
        status = last_worker_result.get("status")
        hint = last_worker_result.get("routing_hint")
        
        logger.info(f"Supervisor reviewing {worker_name} result: {status} (Hint: {hint})")
        
        if status == "failed":
            if hint == "TERMINATE":
                decision = "TERMINATE"
                reasoning = f"Worker {worker_name} failed fatally. Terminating."
                selected_cap = None
            elif hint == "REPORT":
                decision = "CONTINUE"
                reasoning = f"Worker {worker_name} reached retry limit. Graceful degradation to REPORT."
                selected_cap = "REPORT"
            elif hint:
                decision = "RETRY"
                reasoning = f"Worker {worker_name} failed. Retrying capability: {hint}"
                selected_cap = hint
            else:
                decision = "TERMINATE"
                reasoning = "Unknown failure without routing hints. Terminating."
                selected_cap = None
                
        elif status == "success":
            # Deterministic success progression
            if worker_name == "SCHEMA":
                logger.info("Schema extracted successfully. Invoking LLM to decide between SQL and ANALYSIS...")
                llm_decision = _get_llm_routing_decision(state)
                decision = llm_decision["decision"]
                reasoning = llm_decision["reasoning"]
                selected_cap = llm_decision.get("selected_capability")
            elif worker_name == "SQL":
                reasoning = "SQL executed successfully. Proceeding to VISUALIZATION."
                selected_cap = "VISUALIZATION"
            elif worker_name == "ANALYSIS":
                hint = last_worker_result.get("routing_hint")
                if hint:
                    reasoning = f"Analysis completed. Following hint to {hint}."
                    selected_cap = hint
                else:
                    reasoning = "Analysis completed. Proceeding to REPORT."
                    selected_cap = "REPORT"
            elif worker_name == "VISUALIZATION":
                reasoning = "Visualization completed. Proceeding to REPORT."
                selected_cap = "REPORT"
            elif worker_name == "REPORT":
                decision = "TERMINATE"
                reasoning = "Report generated successfully. Workflow complete."
                selected_cap = None
            else:
                # Ambiguous state, invoke LLM
                llm_decision = _get_llm_routing_decision(state)
                decision = llm_decision["decision"]
                reasoning = llm_decision["reasoning"]
                selected_cap = llm_decision.get("selected_capability")
    
    else:
        # Fallback safety
        decision = "TERMINATE"
        reasoning = "No schema and no last worker result. Cannot proceed."
        selected_cap = None

    # Enforce Capability Registry validation
    if selected_cap:
        cap_def = get_capability(selected_cap)
        if not cap_def or not cap_def.enabled:
            logger.error(f"Supervisor selected invalid or disabled capability: {selected_cap}")
            decision = "TERMINATE"
            reasoning = f"Selected capability {selected_cap} is unavailable."
            selected_cap = None
            
    end_time = time.time()
    
    decision_obj: SupervisorDecision = {
        "decision": decision,
        "reasoning": reasoning,
        "selected_capability": selected_cap,
        "timestamp": end_time
    }
    
    supervisor_history.append(decision_obj)
    
    logger.info(f"Supervisor Decision: {decision} | Capability: {selected_cap} | Reason: {reasoning}")
    
    # Telemetry
    duration_ms = (end_time - start_time) * 1000
    node_metadata = {
        "node_name": node_name,
        "start_time": start_time,
        "end_time": end_time,
        "duration_ms": duration_ms,
        "status": "success",
        "retry_count": 0,
        "error_message": None
    }
    execution_metadata = list(state.get("execution_metadata") or [])
    execution_metadata.append(node_metadata)
    
    return {
        "supervisor_history": supervisor_history,
        "execution_metadata": execution_metadata
    }
