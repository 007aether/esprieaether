"""Le robot de surveillance vérifie de vrais endpoints et ne signale pas Ollama arrêté."""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "robots"))

import robot_engine  # noqa: E402


class _Resp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class RobotSentinelTest(unittest.TestCase):
    def test_sentinel_is_seeded_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "robots.db"
            with patch.object(robot_engine, "DB", str(db)):
                robot_engine.init_engine_db()
                robot_engine.init_engine_db()  # idempotent
                conn = sqlite3.connect(db)
                row = conn.execute(
                    "SELECT name, system, role, status FROM robots WHERE id='SYS_01'"
                ).fetchone()
                conn.close()
            self.assertEqual(row, ("SERVICE_SENTINEL", "monitoring", "service_health", "active"))

    def test_service_health_reports_real_down_endpoints(self):
        def fake_urlopen(url, timeout):
            return _Resp(503 if "5001" in url else 200)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = robot_engine.h_service_health("SYS_01")
        self.assertFalse(result["ok"])
        self.assertIn("up=9/10", result["summary"])
        self.assertEqual(result["detail"]["down"], ["gateway"])

    def test_embedder_ollama_down_is_degraded_not_error(self):
        import urllib.error

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            result = robot_engine.h_embed("AI_05")
        self.assertTrue(result["ok"])
        self.assertIn("Ollama", result["summary"])


if __name__ == "__main__":
    unittest.main()
