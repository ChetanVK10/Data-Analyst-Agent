import time
import logging
from typing import Dict, Any, Optional

from backend.agents.state import AgentState, SupervisorDecision
from backend.agents.capability_registry import get_enabled_capabilities, get_capability

logger = logging.getLogger(__name__)

import json
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import get_llm

def _get_deterministic_routing(question: str) -> Optional[str]:
    q_lower = question.lower()
    
    # 1. High-priority Python Analysis phrases
    python_phrases = [
        "moving average", "rolling average", "rolling window", "regex",
        "extract pattern", "fuzzy match", "fuzzy matching", "text cleaning",
        "normalize text", "pivot", "reshape", "feature engineering", "custom calculation"
    ]
    if any(phrase in q_lower for phrase in python_phrases):
        return "PYTHON_ANALYSIS"
        
    # 2. Deterministic statistical analysis keywords
    stats_keywords = [
        "correlation", "outlier", "anomaly", "distribution", "skew", "kurtosis", "descriptive", "trend"
    ]
    if any(keyword in q_lower for keyword in stats_keywords):
        return "ANALYSIS"
        
    # 3. Obvious SQL retrieval/aggregation keywords
    sql_keywords = [
        "average", "count", "sum", "top", "bottom", "group by", "order by", "limit"
    ]
    if any(keyword in q_lower for keyword in sql_keywords):
        return "SQL"
        
    return None

def _get_llm_routing_decision(state: AgentState) -> SupervisorDecision:
    """
    Invokes the LLM to decide the next capability based on the current state.
    """
    logger.info("Supervisor LLM reasoning required for dynamic routing...")
    
    question = state.get("question", "")
    last_worker_result = state.get("last_worker_result", {})
    worker_name = last_worker_result.get("worker_name", "UNKNOWN")
    
    context_str = ""
    conversational_context = state.get("conversational_context")
    if conversational_context:
        context_str = f"""
PREVIOUS CONVERSATIONAL CONTEXT:
The user previously asked: "{conversational_context.get('previous_resolved_question', conversational_context.get('previous_question', ''))}"
Capability used: {conversational_context.get('previous_capability')}
Result columns: {conversational_context.get('previous_result_columns', [])}

You must determine if the new user question is a FOLLOW-UP to this previous context, or a completely NEW INTENT.

CRITICAL INTENT RESOLUTION RULES:
- FOLLOW-UP: The current request depends on, modifies, filters, sorts, ranks, extends, compares with, or transforms the immediately relevant previous analytical result.
  Examples of FOLLOW-UP:
  * "Show only the top 5" (filters previous result)
  * "Sort descending" (sorts previous result)
  * "Add a moving average" (extends previous time-series result)
  * "Break that down by region" (splits previous metrics by a new dimension)
  * "Compare it with last year" (compares previous metrics)
  * "Use the same analysis for Europe" (filters previous metric on a new region)
  
- NEW INTENT: The current request is independently executable and introduces a new analytical objective, grouping, measure, dimension, or analysis that does not require or build on the previous result.
  * Dataset continuity alone does NOT make a request a follow-up.
  * Topic similarity (e.g. both asking about "sales") alone does NOT make a request a follow-up.
  * Sharing the same metric alone does NOT make a request a follow-up.
  * A new self-contained analytical request MUST NOT inherit stale ranking, filtering, grouping, top-N, sorting, or transformation constraints from previous turns.
  Examples of NEW INTENT:
  * Previous: "Show total sales by product line" -> Current: "Show monthly total sales over time" (This is a NEW INTENT: is_follow_up = false, resolved_question = "Show monthly total sales over time")
  * Previous: "Show revenue by region" -> Current: "Show customer count by country" (This is a NEW INTENT: is_follow_up = false, resolved_question = "Show customer count by country")

If it is a FOLLOW-UP, you must generate a `resolved_question` that combines the new request with the previous intent into a standalone, self-contained analytical question.
If it is a NEW INTENT, set `is_follow_up` to false and set `resolved_question` to the current question exactly.
"""

    system_prompt = f"""You are the Supervisor Agent for an Autonomous Data Analyst.
Your job is to route the workflow to the correct capability.

AVAILABLE CAPABILITIES:
- SQL: Generates and executes SQL queries to answer questions about the data (filtering, joins, aggregations, ranking, grouping).
- ANALYSIS: Performs deterministic statistical analysis (correlation, descriptive, distribution, trend, outliers).
- PYTHON_ANALYSIS: Executes custom calculations, rolling windows, feature engineering, regex pattern matching, text cleaning, reshaping, pivot logic, fuzzy matching, and complex transformations via Python.
- VISUALIZATION: Generates Plotly charts.
- REPORT: Synthesizes findings into a final report.

The last worker to run was {worker_name}.
{context_str}

Analyze the user's question and decide the next logical capability.
If the question requires custom mathematical manipulation, regex, fuzzy matching, or complex transformations not easily done in SQL, choose PYTHON_ANALYSIS.
If the question asks for statistical analysis like correlation, trend, distribution, or outliers, choose ANALYSIS.
If the question asks for data retrieval, grouping, or general querying, choose SQL.

Respond ONLY with a JSON object in this format:
{{
    "decision": "CONTINUE",
    "reasoning": "Explain why you chose this capability.",
    "selected_capability": "SQL" | "PYTHON_ANALYSIS" | "ANALYSIS",
    "is_follow_up": true or false,
    "resolved_question": "The standalone analytical question."
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
            "timestamp": time.time(),
            "is_follow_up": decision_data.get("is_follow_up", False),
            "resolved_question": decision_data.get("resolved_question", question)
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
    
    # 2. Start of turn with cached schema profile
    elif not last_worker_result:
        logger.info("Schema profile is already cached. Routing new question...")
        has_context = bool(state.get("conversational_context"))
        deterministic_cap = _get_deterministic_routing(state.get("question", ""))
        if deterministic_cap and not has_context:
            decision = "CONTINUE"
            reasoning = f"Deterministic routing matched question patterns: {deterministic_cap}"
            selected_cap = deterministic_cap
        else:
            if has_context:
                logger.info("Conversational context present. Forcing LLM routing to resolve intent.")
            llm_decision = _get_llm_routing_decision(state)
            decision = llm_decision["decision"]
            reasoning = llm_decision["reasoning"]
            selected_cap = llm_decision.get("selected_capability")

    # 3. Process Last Worker Result
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
                logger.info("Schema extracted successfully. Checking deterministic routing first...")
                has_context = bool(state.get("conversational_context"))
                deterministic_cap = _get_deterministic_routing(state.get("question", ""))
                if deterministic_cap and not has_context:
                    decision = "CONTINUE"
                    reasoning = f"Deterministic routing matched question patterns: {deterministic_cap}"
                    selected_cap = deterministic_cap
                    logger.info(f"Deterministic routing matched: {selected_cap}")
                else:
                    if has_context:
                        logger.info("Conversational context present. Forcing LLM routing to resolve intent.")
                    llm_decision = _get_llm_routing_decision(state)
                    decision = llm_decision["decision"]
                    reasoning = llm_decision["reasoning"]
                    selected_cap = llm_decision.get("selected_capability")
            elif worker_name in ("SQL", "PYTHON_ANALYSIS"):
                from backend.services.visualization.validator import is_result_chartable
                query_res = state.get("query_result", {})
                if is_result_chartable(query_res):
                    reasoning = f"{worker_name} executed successfully. Result is chartable. Proceeding to VISUALIZATION."
                    selected_cap = "VISUALIZATION"
                else:
                    reasoning = f"{worker_name} executed successfully. Result is not chartable. Proceeding to REPORT."
                    selected_cap = "REPORT"
            elif worker_name == "ANALYSIS":
                hint = last_worker_result.get("routing_hint")
                if hint:
                    reasoning = f"Analysis completed. Following hint to {hint}."
                    selected_cap = hint
                else:
                    from backend.services.visualization.validator import is_result_chartable
                    query_res = state.get("query_result", {})
                    if is_result_chartable(query_res):
                        reasoning = "Analysis completed. Result is chartable. Proceeding to VISUALIZATION."
                        selected_cap = "VISUALIZATION"
                    else:
                        reasoning = "Analysis completed. Result is not chartable. Proceeding to REPORT."
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
    
    updates = {
        "supervisor_history": supervisor_history,
        "execution_metadata": execution_metadata
    }

    # If the LLM was invoked and returned a resolved question, propagate it.
    if 'llm_decision' in locals():
        is_follow_up = llm_decision.get("is_follow_up", False)
        resolved_question = llm_decision.get("resolved_question")
        
        updates["resolved_question"] = resolved_question

    return updates
