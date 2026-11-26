"""Chaque agent a un rôle explicite et un travail vérifiable, même sans source documentaire."""

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
# Test isolé : les vraies sources documentaires peuvent exister sur la machine ;
# on pointe vers un dossier vide pour garder le scénario « aucune source ».
os.environ["AGENT_SOURCES_DIR"] = str(Path(_STATE_TMP.name) / "sources-empty")
os.environ["WEB_SECRET_KEY"] = "test-secret-not-a-real-key"
os.environ["FREELLMAPI_KEY"] = "test-key-placeholder"

import espria_system  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class AgentDutiesTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(espria_system.app)

    def test_registry_publishes_a_mission_for_every_agent(self):
        registry = self.client.get("/agents").json()
        self.assertTrue(registry)
        for item in registry:
            self.assertTrue(item.get("mission"), item["id"])
        missions = {item["id"]: item["mission"] for item in registry}
        self.assertIn("contrat", missions["A4"].lower())
        self.assertIn("fiscal", missions["L1"].lower())
        self.assertIn("travail", missions["L2"].lower())

    def test_source_agents_report_real_work_without_inventing_facts(self):
        for agent in ("A4", "L1", "L2"):
            body = self.client.get(f"/agents/{agent}/run").json()
            self.assertEqual(body["status"], "no_data_source")
            self.assertTrue(body["duty"])
            self.assertEqual(body["work"]["files_found"], 0)
            self.assertTrue(body["work"]["checked_dir"])
            self.assertIn("summary", body)

    def test_system_agents_report_their_work_scope(self):
        with patch.object(espria_system, "_all_kpis", return_value=[]):
            body = self.client.get("/agents/director/run").json()
        self.assertTrue(body["duty"])
        self.assertEqual(body["work"]["scope"], "system")


if __name__ == "__main__":
    unittest.main()
