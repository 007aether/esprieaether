#!/usr/bin/env python3
"""Test suite for Agent Kernel module"""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAgentKernel(unittest.TestCase):
    """Test cases for Agent Kernel"""
    
    def test_validate_action(self):
        """Test action validation"""
        from src.agent_kernel import validate_action
        allowed, msg = validate_action("monitor", {"targets": ["agent_mesh"]})
        self.assertTrue(allowed)

if __name__ == "__main__":
    unittest.main()
