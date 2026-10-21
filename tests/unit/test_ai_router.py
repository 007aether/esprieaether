#!/usr/bin/env python3
"""Test suite for AI Router module"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAIRouter(unittest.TestCase):
    """Test cases for AI router"""
    
    def test_router_initialization(self):
        """Test router initialization"""
        from src.ai_router import AIRouter
        router = AIRouter()
        self.assertIsNotNone(router)
    
    def test_router_route(self):
        """Test routing functionality"""
        from src.ai_router import AIRouter
        router = AIRouter()
        route = router.route("test request", "test_category")
        self.assertIsNotNone(route)

if __name__ == "__main__":
    unittest.main()
