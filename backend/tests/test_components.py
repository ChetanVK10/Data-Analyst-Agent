import os
import unittest
import sys
import time
import duckdb

# Add workspace directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.session_manager import SessionManager, Session
from backend.agents.sandbox import prepare_scratch_directory
from backend.agents.nodes.validator import validator_node
from backend.agents.nodes.reflection import reflection_node
from backend.agents.nodes.visualization_reflection import visualization_reflection_node
from backend.agents.nodes.supervisor import supervisor_node

class TestSessionManager(unittest.TestCase):
    def setUp(self):
        # Create manager with short TTL for testing eviction
        self.manager = SessionManager(ttl_seconds=1)

    def test_session_creation_and_retrieval(self):
        session_id = "test-session-123"
        session = self.manager.get_session(session_id)
        
        self.assertIsNotNone(session)
        self.assertEqual(session.session_id, session_id)
        self.assertIn(session_id, self.manager.sessions)
        
        # Verify it touches accessed time
        prev_accessed = session.last_accessed
        time.sleep(0.1)
        session2 = self.manager.get_session(session_id)
        self.assertGreater(session2.last_accessed, prev_accessed)

    def test_session_eviction(self):
        session_id = "test-session-evict"
        self.manager.get_session(session_id)
        self.assertIn(session_id, self.manager.sessions)
        
        # Wait for TTL to expire
        time.sleep(1.2)
        self.manager.clean_expired_sessions()
        
        # Session should be removed from dict
        self.assertNotIn(session_id, self.manager.sessions)

class TestFailureClassification(unittest.TestCase):
    def test_runtime_failure_classification(self):
        # State simulating sandbox crash
        state = {
            "question": "Show total sales",
            "plan": {"approach": "sql"},
            "expected_output_type": "dataframe",
            "generated_code": "SELECT * FROM sales;",
            "execution_success": False,
            "output_summary": {"error": "Binder Error: column 'sales' not found", "code_context": "SELECT * FROM sales;"}
        }
        
        res = validator_node(state)
        self.assertFalse(res["validation_passed"])
        self.assertEqual(res["failure_summary"]["failure_type"], "runtime")
        self.assertIn("Binder Error", res["failure_summary"]["error_message"])

    def test_timeout_failure_classification(self):
        # State simulating execution timeout
        state = {
            "question": "Plot sales trend",
            "plan": {"approach": "python"},
            "expected_output_type": "chart",
            "generated_code": "import time; time.sleep(15)",
            "execution_success": False,
            "output_summary": {"error": "Execution Timeout: Code execution took longer than 10 seconds."}
        }
        
        res = validator_node(state)
        self.assertFalse(res["validation_passed"])
        self.assertEqual(res["failure_summary"]["failure_type"], "timeout")

    def test_structural_failure_classification(self):
        # Succeeded run, but returned empty structural columns
        state = {
            "question": "Average margins",
            "plan": {"approach": "sql"},
            "expected_output_type": "dataframe",
            "generated_code": "SELECT margin FROM data;",
            "execution_success": True,
            "output_summary": {"columns": [], "row_count": 0, "preview": []}
        }
        
        res = validator_node(state)
        self.assertFalse(res["validation_passed"])
        self.assertEqual(res["failure_summary"]["failure_type"], "structural")



class TestReflectionAndRouting(unittest.TestCase):
    def test_reflection_routing_to_code_generator(self):
        # Runtime error should route back to code_generator
        state = {
            "validation_passed": False,
            "failure_summary": {
                "failure_type": "runtime",
                "error_message": "ZeroDivisionError",
                "code_context": "x = 1/0",
                "expected_vs_actual": ""
            },
            "retry_count": 0,
            "retry_history": []
        }
        
        res = reflection_node(state)
        self.assertEqual(res["last_worker_result"]["routing_hint"], "SQL")
        self.assertEqual(res["retry_count"], 1)
        self.assertEqual(len(res["retry_history"]), 1)

    def test_reflection_routing_to_planner(self):
        # Semantic error should route back to planner
        state = {
            "validation_passed": False,
            "failure_summary": {
                "failure_type": "semantic",
                "error_message": "Answers sum instead of mean",
                "code_context": "SELECT SUM(x) FROM data;",
                "expected_vs_actual": ""
            },
            "retry_count": 1,
            "retry_history": []
        }
        
        res = reflection_node(state)
        self.assertEqual(res["last_worker_result"]["routing_hint"], "SQL")
        self.assertEqual(res["retry_count"], 2)

    def test_reflection_retry_limit_cutoff(self):
        # Reaching 3 retries should trigger graceful failure routing to report_agent
        state = {
            "validation_passed": False,
            "failure_summary": {
                "failure_type": "runtime",
                "error_message": "IndexError",
                "code_context": "arr[10]",
                "expected_vs_actual": ""
            },
            "retry_count": 3,
            "retry_history": []
        }
        
        res = reflection_node(state)
        self.assertEqual(res["last_worker_result"]["routing_hint"], "REPORT")
        self.assertTrue(res["graceful_failure"])

class TestVisualizationReflection(unittest.TestCase):
    def test_vis_reflection_success_routing(self):
        state = {
            "execution_success": True,
            "output_summary": {"chart_json": {"data": [{"x": [1], "y": [2]}], "layout": {"title": {"text": "Test Chart"}}}},
            "vis_retry_count": 0,
            "vis_retry_history": []
        }
        res = visualization_reflection_node(state)
        self.assertEqual(res["last_worker_result"]["routing_hint"], "REPORT")
        self.assertFalse(res.get("graceful_failure", False))

    def test_vis_reflection_retry_routing(self):
        state = {
            "execution_success": False,
            "failure_summary": {
                "failure_type": "visualization",
                "error_message": "Subprocess crash",
                "code_context": "",
                "expected_vs_actual": ""
            },
            "vis_retry_count": 1,
            "vis_retry_history": []
        }
        res = visualization_reflection_node(state)
        self.assertEqual(res["last_worker_result"]["routing_hint"], "VISUALIZATION")
        self.assertEqual(res["vis_retry_count"], 2)
        self.assertEqual(len(res["vis_retry_history"]), 1)

    def test_vis_reflection_cutoff_routing(self):
        state = {
            "execution_success": False,
            "failure_summary": {
                "failure_type": "visualization",
                "error_message": "Subprocess crash",
                "code_context": "",
                "expected_vs_actual": ""
            },
            "vis_retry_count": 3,
            "vis_retry_history": []
        }
        res = visualization_reflection_node(state)
        self.assertEqual(res["last_worker_result"]["routing_hint"], "REPORT")
        self.assertFalse(res["graceful_failure"])

class TestSupervisorRouting(unittest.TestCase):
    def test_routing_scenarios(self):
        from unittest.mock import patch
        
        def mock_llm_decision(state):
            q = state.get("question", "").lower()
            if "domain" in q:
                cap = "PYTHON_ANALYSIS"
            elif "normalize" in q:
                cap = "PYTHON_ANALYSIS"
            else:
                cap = "SQL"
            return {
                "decision": "CONTINUE",
                "reasoning": "Mocked LLM route",
                "selected_capability": cap,
                "timestamp": time.time()
            }

        with patch('backend.agents.nodes.supervisor._get_llm_routing_decision', side_effect=mock_llm_decision) as mock_llm:
            # 1. SQL Routing (Deterministic)
            state_sql = {
                "question": "Show the top 10 hospitals by revenue",
                "schema_profile": {"columns": []},
                "last_worker_result": {"worker_name": "SCHEMA", "status": "success"},
                "supervisor_history": [],
                "execution_metadata": []
            }
            res = supervisor_node(state_sql)
            decision = res["supervisor_history"][-1]
            self.assertEqual(decision["selected_capability"], "SQL")
            mock_llm.assert_not_called()

            # 2. Deterministic Analysis Routing
            state_analysis = {
                "question": "Calculate correlation between age and charges",
                "schema_profile": {"columns": []},
                "last_worker_result": {"worker_name": "SCHEMA", "status": "success"},
                "supervisor_history": [],
                "execution_metadata": []
            }
            res = supervisor_node(state_analysis)
            decision = res["supervisor_history"][-1]
            self.assertEqual(decision["selected_capability"], "ANALYSIS")
            mock_llm.assert_not_called()

            # 3. Python Analysis Routing cases (some deterministic, some fallback to LLM)
            # - "Extract domain names..." -> fallback (calls mock_llm)
            # - "Calculate a 30-day moving average..." -> deterministic (no mock call)
            # - "Normalize customer names..." -> fallback (calls mock_llm)
            # - "Create a pivot..." -> deterministic (no mock call)
            py_questions = [
                "Extract domain names from the email column",
                "Calculate a 30-day moving average of sales",
                "Normalize customer names and remove extra whitespace",
                "Create a pivot of monthly sales by region"
            ]
            for q in py_questions:
                state_py = {
                    "question": q,
                    "schema_profile": {"columns": []},
                    "last_worker_result": {"worker_name": "SCHEMA", "status": "success"},
                    "supervisor_history": [],
                    "execution_metadata": []
                }
                res = supervisor_node(state_py)
                decision = res["supervisor_history"][-1]
                self.assertEqual(decision["selected_capability"], "PYTHON_ANALYSIS", f"Failed for query: {q}")

    def test_ambiguous_routing_calls_llm(self):
        from unittest.mock import patch
        state_ambiguous = {
            "question": "Find unusual customer purchasing behaviour",
            "schema_profile": {"columns": []},
            "last_worker_result": {"worker_name": "SCHEMA", "status": "success"},
            "supervisor_history": [],
            "execution_metadata": []
        }
        with patch('backend.agents.nodes.supervisor._get_llm_routing_decision') as mock_llm_route:
            mock_llm_route.return_value = {
                "decision": "CONTINUE",
                "reasoning": "Mocked LLM route",
                "selected_capability": "SQL",
                "timestamp": time.time()
            }
            supervisor_node(state_ambiguous)
            mock_llm_route.assert_called_once()

from backend.services.python.python_quality_validator import validate_python_code
from backend.agents.nodes.sandbox_executor import sandbox_executor_node

class TestPythonAnalysisExecution(unittest.TestCase):
    def test_ast_validator(self):
        # Syntax Error
        code_syntax = "result = df['age' + "
        is_valid, err = validate_python_code(code_syntax)
        self.assertFalse(is_valid)
        self.assertIn("Syntax Error", err)

        # Forbidden Import
        code_import = "import os\nresult = os.getcwd()"
        is_valid, err = validate_python_code(code_import)
        self.assertFalse(is_valid)
        self.assertIn("Import Violation", err)

        # Dangerous Builtin
        code_eval = "result = eval('df.mean()')"
        is_valid, err = validate_python_code(code_eval)
        self.assertFalse(is_valid)
        self.assertIn("Security Violation", err)

        # Allowed Code
        code_ok = "import numpy as np\nresult = np.mean(df['age'])"
        is_valid, err = validate_python_code(code_ok)
        self.assertTrue(is_valid)

    def test_pre_execution_column_validator(self):
        # State simulating schema with required column missing
        state = {
            "session_id": "test-session",
            "dataset_id": "test-data",
            "schema_profile": {
                "columns": [{"name": "age", "dtype": "integer"}]
            },
            "plan": {
                "approach": "python",
                "required_columns": ["nonexistent_col"]
            },
            "generated_code": "result = df['nonexistent_col'] * 2",
            "execution_success": False,
            "retry_count": 0,
            "execution_metadata": []
        }
        res = sandbox_executor_node(state)
        self.assertFalse(res["execution_success"])
        self.assertEqual(res["failure_summary"]["failure_type"], "semantic")
        self.assertIn("Column Validation Error", res["output_summary"]["error"])

    def test_post_execution_validator(self):
        # 1. Produced result missing
        state_missing = {
            "plan": {"approach": "python", "expected_output": "dataframe"},
            "generated_code": "x = 5",
            "execution_success": True,
            "output_summary": {"error": None}, # Missing result_data
            "retry_count": 0,
            "execution_metadata": []
        }
        res = validator_node(state_missing)
        self.assertFalse(res["validation_passed"])
        self.assertEqual(res["failure_summary"]["failure_type"], "structural")
        self.assertIn("required 'result' variable was not assigned", res["failure_summary"]["error_message"])

        # 2. Unexpectedly empty
        state_empty = {
            "plan": {"approach": "python", "expected_output": "dataframe"},
            "generated_code": "result = pd.DataFrame()",
            "execution_success": True,
            "output_summary": {"result_data": {"type": "dataframe", "columns": ["x"], "rows": []}},
            "retry_count": 0,
            "execution_metadata": []
        }
        res = validator_node(state_empty)
        self.assertFalse(res["validation_passed"])
        self.assertEqual(res["failure_summary"]["failure_type"], "structural")
        self.assertIn("empty DataFrame", res["failure_summary"]["error_message"])

        # 3. Expected vs Actual mismatch
        state_mismatch = {
            "plan": {"approach": "python", "expected_output": "dataframe"},
            "generated_code": "result = 5",
            "execution_success": True,
            "output_summary": {"result_data": 5},
            "retry_count": 0,
            "execution_metadata": []
        }
        res = validator_node(state_mismatch)
        self.assertFalse(res["validation_passed"])
        self.assertEqual(res["failure_summary"]["failure_type"], "structural")
        self.assertIn("output type mismatch", res["failure_summary"]["error_message"])

    def test_python_retry_routing(self):
        # Python capability reflection error should route to PYTHON_ANALYSIS
        state = {
            "validation_passed": False,
            "failure_summary": {
                "failure_type": "runtime",
                "error_message": "ZeroDivisionError",
                "code_context": "result = 1/0",
                "expected_vs_actual": ""
            },
            "plan": {"approach": "python"},
            "retry_count": 0,
            "retry_history": []
        }
        res = reflection_node(state)
        self.assertEqual(res["last_worker_result"]["routing_hint"], "PYTHON_ANALYSIS")
        self.assertEqual(res["last_worker_result"]["worker_name"], "PYTHON_ANALYSIS")
        self.assertEqual(res["retry_count"], 1)

if __name__ == "__main__":
    unittest.main()
