#!/usr/bin/env python3
"""Test suite for Web Interface module"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestWebInterface(unittest.TestCase):
    """Test cases for Web Interface"""
    
    def test_module_import(self):
        """Test module can be imported"""
        from src import web_interface
        self.assertTrue(hasattr(web_interface, '__name__'))

if __name__ == "__main__":
    unittest.main()
