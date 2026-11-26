"""J119 — TDD : trois nouveaux agents visibles dans le registre local."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

_STATE_TMP = tempfile.TemporaryDirectory()
os.environ["ESPRIA_STATE_DIR"] = _STATE_TMP.name
os.environ["WEB_SECRET_KEY"] = "test-secret-not-a-real-key"
os.environ["FREELLMAPI_KEY"] = "test-key-placeholder"

import espria_system  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class NewAgentsRegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(espria_system.app)
        self.state = Path(_STATE_TMP.name)
        patcher = patch.object(espria_system, "STATE_DIR", self.state)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_registry_publishes_doctor_rea_and_scout(self) -> None:
        registry = {row["id"]: row for row in self.client.get("/agents").json()}
        for agent_id in ("doctor", "rea", "github-scout"):
            self.assertIn(agent_id, registry)
            self.assertTrue(registry[agent_id]["mission"])

    def test_agent_reads_only_its_own_public_selfcheck(self) -> None:
        report = {"ok": True, "status": "live_verified", "checked_at": "2026-11-26T12:00:00+00:00",
                  "detected": 3, "fixed": 2, "next": "sans redémarrage"}
        (self.state / "doctor_selfcheck.json").write_text(
            json.dumps(report), encoding="utf-8")
        body = self.client.get("/agents/doctor/run").json()
        self.assertEqual(body["status"], "live_verified")
        self.assertEqual(body["summary"]["fixed"], 2)
        self.assertEqual(body["work"]["source"], "state/doctor_selfcheck.json")

    def test_missing_selfcheck_is_explicitly_no_data_source(self) -> None:
        body = self.client.get("/agents/rea/run").json()
        self.assertEqual(body["status"], "no_data_source")
        self.assertEqual(body["work"]["files_found"], 0)

    def test_system_agents_still_use_dashboard(self) -> None:
        body = self.client.get("/agents/A1/run").json()
        self.assertIn(body["status"], ("ok", "source_error"))
        self.assertEqual(body["work"]["scope"], "system")


if __name__ == "__main__":
    unittest.main()
