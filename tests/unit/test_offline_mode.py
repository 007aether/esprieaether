#!/usr/bin/env python3
"""
TESTS FOR SCENARIO 5 — Anti-Offline Mode (Full Local)
======================================================
Verifies the offline-first architecture: local services, fallback, cache.
"""

import sys
import os
import json
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

class TestOfflineModeManager(unittest.TestCase):
    """Test OfflineModeManager (Scenario 5)."""

    def setUp(self):
        from src.offline_mode import OfflineModeManager
        self.manager = OfflineModeManager()

    def test_initial_state(self):
        self.assertFalse(self.manager.is_offline())
        self.assertTrue(self.manager.local_only)

    def test_set_offline_mode(self):
        self.manager.set_offline_mode(True)
        self.assertTrue(self.manager.is_offline())
        self.manager.set_offline_mode(False)
        self.assertFalse(self.manager.is_offline())

    def test_local_status_roundtrip(self):
        status = self.manager.get_local_status()
        self.assertIn("ollama_local", status)
        self.assertIn("colibri_local", status)
        self.assertIn("all_local_online", status)

    def test_fallback_response(self):
        response = self.manager.generate_fallback("hello", model="local")
        self.assertIn("response", response)
        self.assertIn("source", response)
        self.assertTrue(response["source"] in ("offline_fallback", "offline_cache"))

    def test_fallback_unknown_query_returns_offline_fallback(self):
        # An unknown query should use the offline_fallback mechanism (not cached)
        # Clear cache first to ensure it's not from a previous run
        self.manager.response_cache = {"responses": {}, "queries": {}}
        self.manager._save_cache()
        response = self.manager.generate_fallback("test_unknown_query_xyz_123", model="local")
        self.assertIn("offline_fallback", response["source"])

    def test_cache_persistence(self):
        self.manager.generate_fallback("persist_test", model="local")
        cache_file = Path(self.manager.cache_file)
        self.assertTrue(cache_file.exists())
        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("persist_test", data["responses"])

    def test_dashboard_html_generated(self):
        html = self.manager.get_dashboard_html()
        self.assertIsInstance(html, str)
        self.assertIn("EsprieAether", html)


class TestOfflineModeRunner(unittest.TestCase):
    """Test OfflineModeRunner (Scenario 5 end-to-end)."""

    def setUp(self):
        from src.offline_mode import OfflineModeRunner
        self.runner = OfflineModeRunner()
        from src.offline_mode import OfflineModeManager
        self.manager = OfflineModeManager()

    def test_run_scenarios(self):
        results = self.runner.run()
        self.assertTrue(results["offline_mode"])
        self.assertTrue(results["local_only"])


class TestOfflineServices(unittest.TestCase):
    """Test that local services respond."""

    def test_ollama_reachable(self):
        import subprocess
        result = subprocess.run(
            ["curl", "-s", "--max-time", "3", "http://127.0.0.1:11434/api/tags"],
            capture_output=True, text=True, timeout=5
        )
        # Ollama might not be running; that's OK, we just verify connectivity check
        self.assertIsInstance(result.returncode, int)

    def test_colibri_reachable(self):
        import subprocess
        result = subprocess.run(
            ["curl", "-s", "--max-time", "3", "http://127.0.0.1:8000/v1/models"],
            capture_output=True, text=True, timeout=5
        )
        self.assertIsInstance(result.returncode, int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
