#!/usr/bin/env python3
"""Test suite for Autonome Evolve module"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAutonomeEvolve(unittest.TestCase):
    """Test cases for autonome evolve"""
    
    def test_autonome_initialization(self):
        """Test autonome initialization"""
        from src.autonome_evolve import run_cycle, diagnose_system
        self.assertTrue(callable(run_cycle))
        self.assertTrue(callable(diagnose_system))
    
    def test_system_status(self):
        """Test system status checking"""
        try:
            from src.autonome_evolve import get_all_services
            services = get_all_services()
            self.assertIsInstance(services, dict)
        except Exception as e:
            self.fail(f"Service check failed: {e}")

if __name__ == "__main__":
    unittest.main()
