#!/usr/bin/env python3
"""Test suite for Agent Kernel module"""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAgentKernel(unittest.TestCase):
    """Test cases for agent kernel"""
    
    def test_kernel_response(self):
        """Test kernel gives proper responses"""
        from src.agent_kernel import AgentKernel
        kernel = AgentKernel()
        response = kernel.process("test")
        self.assertIsNotNone(response)
    
    def test_kernel_init(self):
        """Test kernel initialization"""
        from src.agent_kernel import AgentKernel
        kernel = AgentKernel()
        self.assertIsNotNone(kernel)
    
if __name__ == "__main__":
    unittest.main()
