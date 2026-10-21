#!/usr/bin/env python3
"""Test suite for Orchestrator module"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestOrchestrator(unittest.TestCase):
    """Test cases for orchestrator"""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        from src.orchestrator import Orchestrator
        orch = Orchestrator()
        self.assertIsNotNone(orch)
    
    def test_orchestrator_start(self):
        """Test orchestrator start"""
        from src.orchestrator import Orchestrator
        orch = Orchestrator()
        started = orch.start()
        self.assertTrue(started)

if __name__ == "__main__":
    unittest.main()
