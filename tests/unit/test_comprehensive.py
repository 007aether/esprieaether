#!/usr/bin/env python3
"""
ESPRIEAETHER COMPREHENSIVE UNIT TEST SUITE
=====================================

Unit test suite for EsprieAether modules.
Run with: python -m pytest tests/unit/ -v

Covers:
- agent_kernel: Policy validation
- agent_mesh: Mesh communication
- ai_router: Brain routing
- autonome_evolve: Self-evolution
- orchestrator: Task orchestration
- web_interface: HTTP endpoints
"""

import sys
import os
import json
import unittest
from datetime import datetime
from pathlib import Path

# Ensure src is in path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

class TestAgentKernel(unittest.TestCase):
    """Test Agent Kernel policy validation."""

    def setUp(self):
        from src import agent_kernel
        self.kernel = agent_kernel

    def test_validate_action_monitor(self):
        allowed, msg = self.kernel.validate_action(
            "monitor", {"targets": ["agent_mesh"]}
        )
        self.assertTrue(allowed)
        self.assertIn("agent_mesh", msg)

    def test_validate_action_repair(self):
        allowed, msg = self.kernel.validate_action(
            "repair", {"targets": ["service_restart"]}
        )
        self.assertTrue(allowed)

    def test_validate_action_develop(self):
        allowed, msg = self.kernel.validate_action(
            "develop", {"targets": ["skills_add"]}
        )
        self.assertTrue(allowed)

    def test_validate_action_execute(self):
        allowed, msg = self.kernel.validate_action(
            "execute", {"targets": ["brain_query"]}
        )
        self.assertTrue(allowed)

    def test_validate_action_manage(self):
        allowed, msg = self.kernel.validate_action(
            "manage", {"targets": ["config_change"]}
        )
        self.assertTrue(allowed)

    def test_validate_action_denied(self):
        allowed, msg = self.kernel.validate_action(
            "unknown", {"targets": ["test"]}
        )
        self.assertFalse(allowed)
        self.assertIn("not permitted", msg)

    def test_log_action_format(self):
        from src import agent_kernel
        agent_kernel.log_action("monitor", "ALLOWED", "test")
        log_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "agent_kernel.log"
        )
        if os.path.exists(log_file):
            with open(log_file) as f:
                lines = f.readlines()
                self.assertGreater(len(lines), 0)
                entry = json.loads(lines[-1])
                self.assertEqual(entry["action"], "monitor")
                self.assertEqual(entry["result"], "ALLOWED")


class TestAgentMesh(unittest.TestCase):
    """Test Agent Mesh functionality."""

    def setUp(self):
        from src import agent_mesh
        self.mesh = agent_mesh

    def test_load_board(self):
        board = self.mesh.load_board()
        self.assertIsInstance(board, list)

    def test_save_board(self):
        board = self.mesh.load_board()
        self.mesh.save_board(board)
        board2 = self.mesh.load_board()
        self.assertEqual(board, board2)

    def test_post_message(self):
        msg = self.mesh.post_message("test_agent", "Test message")
        self.assertIn("id", msg)
        self.assertIn("agent", msg)
        self.assertEqual(msg["agent"], "test_agent")

    def test_propose_task(self):
        task = self.mesh.propose_task("test_agent", "Test task", "Test description")
        self.assertIn("title", task)
        self.assertEqual(task["agent"], "test_agent")


class TestAIRouter(unittest.TestCase):
    """Test AI Router."""

    def setUp(self):
        from src import ai_router
        self.router = ai_router

    def test_module_import(self):
        from src import ai_router
        self.assertTrue(hasattr(ai_router, '__name__'))
        self.assertTrue(hasattr(ai_router, 'app'))
        self.assertTrue(hasattr(ai_router, 'BRAINS'))

    def test_brains_exist(self):
        self.assertIn("ollama-local", self.router.BRAINS)
        self.assertIn("colibri-local", self.router.BRAINS)
        self.assertIn("llm7-fast", self.router.BRAINS)


class TestAutonomeEvolve(unittest.TestCase):
    """Test Autonome Evolve module."""

    def setUp(self):
        from src import autonome_evolve
        self.evolve = autonome_evolve

    def test_module_import(self):
        from src import autonome_evolve
        self.assertTrue(hasattr(autonome_evolve, '__name__'))


class TestOrchestrator(unittest.TestCase):
    """Test Orchestrator."""

    def setUp(self):
        from src import orchestrator
        self.orch = orchestrator

    def test_module_import(self):
        from src import orchestrator
        self.assertTrue(hasattr(orchestrator, '__name__'))


class TestWebInterface(unittest.TestCase):
    """Test Web Interface."""

    def setUp(self):
        from src import web_interface
        self.wi = web_interface

    def test_module_import(self):
        from src import web_interface
        self.assertTrue(hasattr(web_interface, '__name__'))


class TestSunnaIntegration(unittest.TestCase):
    """Test Sunna integration."""

    def test_sunna_api_import(self):
        from src import sunna_api
        self.assertTrue(hasattr(sunna_api, 'app'))

    def test_sunna_executor_import(self):
        from src import sunna_executor
        self.assertTrue(hasattr(sunna_executor, 'SunnaTaskExecutor'))


class TestPromptEngineering(unittest.TestCase):
    """Test Prompt Engineering module."""

    def setUp(self):
        from src import prompt_engineering
        self.pe = prompt_engineering.PromptEngine()

    def test_template_lookup(self):
        template = self.pe.suggest_template('technical')
        self.assertEqual(template, 'technical')

    def test_template_export(self):
        prompt = self.pe.format_prompt('technical', 'Test task')
        self.assertIn('تلميح', prompt)
        self.assertIn('Test task', prompt)

    def test_evaluate_prompt(self):
        result = self.pe.evaluate_prompt('Short prompt', 'Response')
        self.assertIn('score', result)
        self.assertIn('feedback', result)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 50)


class TestAcademicEvaluation(unittest.TestCase):
    """Test Academic Evaluation module."""

    def setUp(self):
        from src import academic_evaluator
        self.ae = academic_evaluator.AcademicEvaluator()

    def test_flexibility_evaluation(self):
        result = self.ae.evaluate_flexibility()
        self.assertIn('category', result)
        self.assertIn('items', result)
        self.assertIn('average', result)
        self.assertGreater(result['average'], 0)
        self.assertLessEqual(result['average'], 100)

    def test_performance_evaluation(self):
        result = self.ae.evaluate_performance()
        self.assertIn('category', result)
        self.assertIn('items', result)
        self.assertIn('average', result)

    def test_grade_calculation(self):
        flex = self.ae.evaluate_flexibility()
        perf = self.ae.evaluate_performance()
        caps = self.ae.evaluate_capabilities()
        grade_info = self.ae.calculate_grade([flex, perf, caps])
        self.assertIn('grade', grade_info)
        self.assertIn('overall_avg', grade_info)
        self.assertGreater(grade_info['overall_avg'], 0)


class TestStressTester(unittest.TestCase):
    """Test Stress Testing module."""

    def setUp(self):
        # Load stress module
        sys.path.insert(0, str(BASE_DIR / "tests"))
        import importlib
        import stress.stress_tester
        importlib.reload(stress.stress_tester)
        self.StressTester = stress.stress_tester.StressTester

    def test_init(self):
        tester = self.StressTester()
        self.assertIsInstance(tester, self.StressTester)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
