#!/usr/bin/env python3
"""Test suite for Agent Mesh module"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAgentMesh(unittest.TestCase):
    """Test cases for agent mesh"""
    
    def test_mesh_initialization(self):
        """Test mesh initialization"""
        from src.agent_mesh import AgentMesh
        mesh = AgentMesh()
        self.assertIsNotNone(mesh)
    
    def test_mesh_connections(self):
        """Test mesh connections"""
        from src.agent_mesh import AgentMesh
        mesh = AgentMesh()
        connections = mesh.get_connections()
        self.assertIsInstance(connections, dict)

if __name__ == "__main__":
    unittest.main()
