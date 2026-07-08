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
            "output_summary": {"chart_json": {"data": [{"x": [1], "y": [2]}]}},
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
        self.assertTrue(res["graceful_failure"])

if __name__ == "__main__":
    unittest.main()
