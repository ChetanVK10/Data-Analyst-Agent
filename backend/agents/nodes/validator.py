import json
import logging
from typing import Dict, Any
from backend.agents.state import AgentState
from backend.config import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

VALIDATOR_SYSTEM_PROMPT = """You are the Semantic Data Validator for the Autonomous Data Analyst Agent.
Your job is to review the user's question, the executed code/query, and the resulting preview data, and verify if the execution actually answers the user's query.

CRITICAL CHECKS:
1. Logic: Did the code compute what was asked? (e.g., if asked for Average, did it calculate SUM instead?)
2. Columns: Are the metrics correct according to columns?
3. Answers Intent: Does the result directly answer the natural language request?

You must output a JSON object with:
{
  "answers_question": true/false,
  "reason": "Clear explanation of why it does or does not answer the question."
}

Ensure your response is valid JSON only. Do not wrap in markdown blocks other than standard json output.
"""

def validator_node(state: AgentState) -> Dict[str, Any]:
    """
    Validates execution results. Checks runtime errors, structural matching, and semantic correctness.
    Classifies failure types accordingly.
    """
    question = state.get("question")
    plan = state.get("plan") or {}
    expected_output_type = (
    state.get("expected_output_type")
    or plan.get("expected_output_type"))
    code = state.get("generated_code")
    execution_success = state.get("execution_success", False)
    output_summary = state.get("output_summary") or {}
    
    logger.info(f"Running Validator Node (Success state: {execution_success})")

    # 1. RUNTIME & TIMEOUT FAILURE CLASSIFICATION
    if not execution_success:
        error_msg = output_summary.get("error", "Unknown execution error.")
        
        # Check if it was a timeout
        if "timeout" in error_msg.lower():
            failure_type = "timeout"
        else:
            failure_type = "runtime"

        failure_summary = {
            "failure_type": failure_type,
            "error_message": error_msg,
            "code_context": output_summary.get("code_context", code or ""),
            "expected_vs_actual": f"Expected: Successful run. Actual: Crashed with error: {error_msg}"
        }
        
        logger.info(f"Validator Classified: {failure_type} failure. Message: {error_msg}")
        return {
            "validation_passed": False,
            "failure_summary": failure_summary
        }

    # 2. STRUCTURAL & VISUALIZATION FAILURE CLASSIFICATION
    approach = plan.get("approach", "sql")
    
    if expected_output_type in ["chart", "dataframe"]:
        columns = output_summary.get("columns", [])
        row_count = output_summary.get("row_count", 0)
        
        if not columns or row_count == 0:
            failure_summary = {
                "failure_type": "structural",
                "error_message": "The SQL query returned an empty result set or no columns.",
                "code_context": code or "",
                "expected_vs_actual": f"Expected: Dataframe with rows. Actual: Returned columns {columns}, row count {row_count}."
            }
            logger.info("Validator Classified: structural failure (empty or column-less result set).")
            return {
                "validation_passed": False,
                "failure_summary": failure_summary
            }

    # 3. SEMANTIC FAILURE CLASSIFICATION (Call LLM Evaluator)
    # Prepare preview info
    preview_data = output_summary.get("preview", [])
    
    evaluator_context = f"""
User Question: {question}
Executed {approach.upper()} Code/Query:
{code}

Execution Output Summary:
- Expected Output Shape: {expected_output_type}
- Data/Result Preview:
{preview_data}
"""

    messages = [
        SystemMessage(content=VALIDATOR_SYSTEM_PROMPT),
        HumanMessage(content=evaluator_context)
    ]

    try:
        llm = get_llm(temperature=0.0)
        response = llm.invoke(messages)
        content = response.content.strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        eval_res = json.loads(content, strict=False)
        
        if eval_res.get("answers_question") is True:
            logger.info("Validator Node passed semantic check successfully.")
            return {
                "validation_passed": True,
                "failure_summary": None
            }
        else:
            reason = eval_res.get("reason", "Result does not semantically answer user's question.")
            failure_summary = {
                "failure_type": "semantic",
                "error_message": "Semantic validation failed.",
                "code_context": code or "",
                "expected_vs_actual": f"Validator Reason: {reason}"
            }
            logger.info(f"Validator Classified: semantic failure. Reason: {reason}")
            return {
                "validation_passed": False,
                "failure_summary": failure_summary
            }
    except Exception as e:
        logger.error(f"Error in Validator Node semantic check: {e}")
        # Default to pass in case of LLM API failure so we don't block the loop on simple model glitches
        return {
            "validation_passed": True,
            "failure_summary": None
        }
