#!/usr/bin/env python3
"""Test suite for Agent Mesh module"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAgentMesh(unittest.TestCase):
    """Test cases for Agent Mesh"""
    
    def test_module_import(self):
        """Test module can be imported"""
        from src import agent_mesh
        self.assertTrue(hasattr(agent_mesh, '__name__'))

if __name__ == "__main__":
    unittest.main()
