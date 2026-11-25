#!/usr/bin/env python3
"""Test suite for Orchestrator module"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestOrchestrator(unittest.TestCase):
    """Test cases for Orchestrator"""
    
    def test_module_import(self):
        """Test module can be imported"""
        from src import orchestrator
        self.assertTrue(hasattr(orchestrator, '__name__'))

if __name__ == "__main__":
    unittest.main()
