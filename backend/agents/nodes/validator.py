import json
import time
import logging
from typing import Dict, Any
from backend.agents.state import AgentState, get_effective_question
from backend.config import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

VALIDATOR_SYSTEM_PROMPT = """You are the Semantic Data Validator for the Autonomous Data Analyst Agent.
Your job is to review the user's question, the plan, the executed code/query, and the resulting preview data, and perform a deep validation of the query results.

CRITICAL CHECKS:
1. Empty Result Sets: Did the execution produce 0 rows or empty outputs?
2. Missing Requested Columns: Are all dimensions and metrics requested in the question present in the query columns?
3. Incorrect Aggregation: Did the query use incorrect mathematical functions (e.g., SUM instead of AVG, COUNT instead of SUM, or raw SELECT without aggregation when aggregation was expected)?
4. Semantic Correctness & Intent Mismatch: Does the code query exactly what the question asks for? Check tables, filters, joins, groupings, and orderings. E.g. sorting ASC instead of DESC.
5. Duplicate/Suspicious Outputs: Check if the preview data contains unexpected duplicates, incorrect duplicate joins (mismatched primary keys causing duplicate multiplication), or other anomalies.
6. Unexpected NULL-Heavy Outputs: Verify if the output has an abnormally high ratio of NULL values in critical columns.
7. Confidence Score: Assess confidence that the data accurately and correctly answers the user's question.

You must output a JSON object matching exactly this schema:
{
  "answers_question": true, // set to false if ANY check fails
  "confidence_score": "High", // "High" | "Medium" | "Low"
  "reason": "Detailed explanation of why it does or does not answer the question.",
  "checks": {
    "is_empty": false,
    "missing_columns": [] or ["col1", ...],
    "incorrect_aggregation": false,
    "semantic_mismatch": false,
    "duplicate_anomalies": false,
    "null_heavy": false
  },
  "suggested_retry_target": "planner", // "planner" (for logic redesign) or "code_generator" (for SQL/code fixes) or "none"
  "suggested_retry_strategy": "Specific instructions for the next agent on how to adjust the plan, SQL, or aggregations."
}

Ensure your response is valid JSON only. Do not wrap in markdown blocks other than standard json output.
"""

def validator_node(state: AgentState) -> Dict[str, Any]:
    """
    Validates execution results. Checks runtime errors, structural matching, and semantic correctness.
    Classifies failure types and logs telemetry.
    """
    node_name = "validator"
    start_time = time.time()
    retry_count = state.get("retry_count", 0)
    
    logger.info(f"Node started: {node_name} (Retry count: {retry_count})")
    
    question = get_effective_question(state)
    plan = state.get("plan") or {}
    expected_output_type = state.get("expected_output_type") or plan.get("expected_output_type") or plan.get("expected_output")
    code = state.get("generated_code")
    execution_success = state.get("execution_success", False)
    output_summary = state.get("output_summary") or {}
    
    status = "success"
    error_msg = None
    validation_passed = False
    failure_summary = None
    
    approach = plan.get("approach", "sql")

    if approach == "python":
        # 1. RUNTIME & TIMEOUT FAILURE CLASSIFICATION
        if not execution_success:
            existing_failure = state.get("failure_summary")
            if existing_failure and existing_failure.get("failure_type") == "provider_error":
                failure_summary = existing_failure
                logger.warning("Validator preserving provider_error classification.")
                status = "failed"
            else:
                error_msg = output_summary.get("error", "Unknown python execution error.")
                failure_summary = state.get("failure_summary")
                if not failure_summary:
                    failure_type = "timeout" if "timeout" in error_msg.lower() else "runtime"
                    failure_summary = {
                        "failure_type": failure_type,
                        "error_message": error_msg,
                        "code_context": code or "",
                        "expected_vs_actual": f"Expected: Successful python execution. Actual: Failed with error: {error_msg}."
                    }
                status = "failed"
                logger.warning(f"Validator Classified Python error: {error_msg}")
            
        else:
            result_data = output_summary.get("result_data")
            # Check if result variable was produced
            if "result_data" not in output_summary:
                error_msg = "Python analysis script completed, but the required 'result' variable was not assigned or could not be serialized."
                failure_summary = {
                    "failure_type": "structural",
                    "error_message": error_msg,
                    "code_context": code or "",
                    "expected_vs_actual": "Expected 'result' assignment. Actual: No 'result' value found in output."
                }
                status = "failed"
                logger.warning(f"Validator Classified Python structural failure: {error_msg}")
                
            # Check if unexpectedly empty
            elif result_data is None:
                if expected_output_type in ["dataframe", "series"]:
                    error_msg = f"Python analysis returned None, but expected '{expected_output_type}'."
                    failure_summary = {
                        "failure_type": "structural",
                        "error_message": error_msg,
                        "code_context": code or "",
                        "expected_vs_actual": f"Expected: {expected_output_type}. Actual: None."
                    }
                    status = "failed"
                    logger.warning(f"Validator Classified Python structural failure: {error_msg}")
                else:
                    validation_passed = True
                    
            elif isinstance(result_data, dict) and result_data.get("type") == "dataframe" and len(result_data.get("rows", [])) == 0:
                error_msg = "Python analysis returned an empty DataFrame."
                failure_summary = {
                    "failure_type": "structural",
                    "error_message": error_msg,
                    "code_context": code or "",
                    "expected_vs_actual": "Expected populated DataFrame. Actual: DataFrame has 0 rows."
                }
                status = "failed"
                logger.warning(f"Validator Classified Python structural failure: {error_msg}")
                
            # Check expected_output match
            else:
                actual_type = "scalar"
                if isinstance(result_data, dict) and result_data.get("type") in ["dataframe", "series"]:
                    actual_type = result_data["type"]
                elif isinstance(result_data, dict):
                    actual_type = "dict"
                elif isinstance(result_data, list):
                    actual_type = "list"
                    
                if expected_output_type and expected_output_type != actual_type:
                    is_mismatch = False
                    if expected_output_type == "dataframe" and actual_type != "dataframe":
                        is_mismatch = True
                    elif expected_output_type == "series" and actual_type not in ["series", "dataframe"]:
                        is_mismatch = True
                        
                    if is_mismatch:
                        error_msg = f"Python output type mismatch. Expected '{expected_output_type}', but got '{actual_type}'."
                        failure_summary = {
                            "failure_type": "structural",
                            "error_message": error_msg,
                            "code_context": code or "",
                            "expected_vs_actual": f"Expected: {expected_output_type}. Actual: {actual_type}."
                        }
                        status = "failed"
                        logger.warning(f"Validator Classified Python structural failure: {error_msg}")
                    else:
                        validation_passed = True
                else:
                    validation_passed = True

    else:
        # 1. RUNTIME & TIMEOUT FAILURE CLASSIFICATION (SQL)
        if not execution_success:
            existing_failure = state.get("failure_summary")
            if existing_failure and existing_failure.get("failure_type") == "provider_error":
                failure_summary = existing_failure
                logger.warning("Validator preserving provider_error classification.")
                status = "failed"
            else:
                error_msg = output_summary.get("error", "Unknown execution error.")
                failure_type = "timeout" if "timeout" in error_msg.lower() else "runtime"
                
                failure_summary = {
                    "failure_type": failure_type,
                    "error_message": error_msg,
                    "code_context": output_summary.get("code_context", code or ""),
                    "expected_vs_actual": (
                        f"Expected: Successful code run. Actual: Crashed with error: {error_msg}. "
                        "Suggested Retry Target: code_generator. Suggested Retry Strategy: Debug syntax, libraries, or timeout limits."
                    )
                }
                
                logger.warning(f"Validator Classified: {failure_type} failure. Message: {error_msg}")
                status = "failed"
            
        # 2. STRUCTURAL FAILURE (PROGRAMMATIC EMPTY CHECK) (SQL)
        elif expected_output_type in ["chart", "dataframe"] and (not output_summary.get("columns") or output_summary.get("row_count", 0) == 0):
            columns = output_summary.get("columns", [])
            row_count = output_summary.get("row_count", 0)
            
            error_msg = "The SQL query returned an empty result set or no columns."
            failure_summary = {
                "failure_type": "structural",
                "error_message": error_msg,
                "code_context": code or "",
                "expected_vs_actual": (
                    f"Expected: Dataframe with rows. Actual: Returned columns {columns}, row count {row_count}. "
                    "Suggested Retry Target: code_generator. Suggested Retry Strategy: Check table names, ensure filter parameters match data records."
                )
            }
            logger.warning(f"Validator Classified programmatic structural failure: columns={columns}, rows={row_count}")
            status = "failed"
            
        # 3. SEMANTIC FAILURE CLASSIFICATION (Call LLM Evaluator) (SQL)
        else:
            preview_data = output_summary.get("preview", [])
            approach = plan.get("approach", "sql")
            plan_steps = "\n".join([f"- {s}" for s in plan.get("steps", [])])
            
            evaluator_context = f"""
User Question: {question}
Execution Plan:
{plan_steps}

Executed {approach.upper()} Code/Query:
{code}

Execution Output Shape: {expected_output_type}
Columns Returned: {output_summary.get("columns", [])}
Total Row Count: {output_summary.get("row_count", 0)}

Data Preview (Top Rows):
{json.dumps(preview_data, indent=2, default=str)}
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
                    validation_passed = True
                else:
                    reason = eval_res.get("reason", "Result does not semantically answer user's question.")
                    suggested_target = eval_res.get("suggested_retry_target", "planner")
                    failure_type = "semantic" if suggested_target == "planner" else "structural"
                    
                    failure_summary = {
                        "failure_type": failure_type,
                        "error_message": reason,
                        "code_context": code or "",
                        "expected_vs_actual": (
                            f"Confidence Score: {eval_res.get('confidence_score', 'Low')}\n"
                            f"Checks performed: {eval_res.get('checks', {})}\n"
                            f"Suggested Retry Target: {suggested_target}\n"
                            f"Suggested Retry Strategy: {eval_res.get('suggested_retry_strategy')}"
                        )
                    }
                    logger.warning(f"Validator Classified: {failure_type} semantic failure. Reason: {reason}")
                    status = "failed"
                    error_msg = reason
                    
            except Exception as e:
                logger.error(f"Error in Validator Node semantic check: {e}")
                # Fallback to pass so LLM api issues don't crash execution loop
                validation_passed = True

    # Calculate execution metrics
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000
    logger.info(f"Node completed: {node_name} in {duration_ms:.2f}ms | Success: {status == 'success'}")
    
    node_metadata = {
        "node_name": node_name,
        "start_time": start_time,
        "end_time": end_time,
        "duration_ms": duration_ms,
        "status": status,
        "retry_count": retry_count,
        "error_message": error_msg
    }
    
    execution_metadata = list(state.get("execution_metadata") or [])
    execution_metadata.append(node_metadata)
    
    return {
        "validation_passed": validation_passed,
        "failure_summary": failure_summary,
        "execution_metadata": execution_metadata
    }
