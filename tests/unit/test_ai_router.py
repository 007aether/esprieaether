#!/usr/bin/env python3
"""Test suite for AI Router module"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAIRouter(unittest.TestCase):
    """Test cases for AI Router"""
    
    def test_module_import(self):
        """Test module can be imported"""
        from src import ai_router
        self.assertTrue(hasattr(ai_router, '__name__'))

if __name__ == "__main__":
    unittest.main()
