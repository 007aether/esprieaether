#!/usr/bin/env python3
"""Test suite for Autonome Evolve module"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAutonomeEvolve(unittest.TestCase):
    """Test cases for autonome evolve"""
    
    def test_module_import(self):
        """Test module can be imported"""
        from src import autonome_evolve
        self.assertTrue(hasattr(autonome_evolve, '__name__'))

if __name__ == "__main__":
    unittest.main()
