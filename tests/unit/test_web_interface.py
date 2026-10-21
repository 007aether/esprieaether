#!/usr/bin/env python3
"""Test suite for Web Interface module"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestWebInterface(unittest.TestCase):
    """Test cases for web interface"""
    
    def test_web_interface_import(self):
        """Test web interface import"""
        try:
            from src.web_interface import WebInterface
            self.assertIsNotNone(WebInterface)
        except Exception as e:
            self.fail(f"Import failed: {e}")

if __name__ == "__main__":
    unittest.main()
