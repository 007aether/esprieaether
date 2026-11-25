"""O4/O8 : politique d'accès prudente et KPI dérivés du contrat réel."""

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


class PolicyAndKpiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(espria_system.app)

    def test_kpi_catalogue_uses_real_dashboard_contract_fields(self):
        body = self.client.get("/kpi/catalogue").json()
        self.assertGreaterEqual(body["count"], 8)
        sources = " ".join(item["source"] for item in body["catalogue"])
        for field in ("g-rate", "g-cons", "g-over", "g-margin"):
            self.assertIn(field, sources)

    def test_kpi_from_dashboard_reads_only_real_values(self):
        sample = {
            "fields": {"g-rate": "20", "g-cons": "7.5", "g-over": "", "g-margin": "30"},
            "products": [{"name": "p1"}, {"name": "p2"}],
            "inventory": [],
            "todo": {"a": False, "b": True},
        }
        with patch.object(espria_system, "_dashboard_state", return_value=sample):
            body = self.client.get("/kpi/from-dashboard").json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["values"]["g_rate"], "20")
        self.assertEqual(body["values"]["products_count"], 2)
        self.assertEqual(body["values"]["todo_open"], 1)

    def test_production_is_closed_by_default(self):
        body = self.client.get("/access/policy").json()
        self.assertEqual(body["signup_forced_role"], "user")
        self.assertEqual(body["role_escalation"], "impossible")
        self.assertFalse(body["production_enabled"])

    def test_production_requires_role_and_explicit_switch(self):
        user = espria_system.create_token(1, "u", "user")
        admin = espria_system.create_token(2, "a", "admin")
        h_user = {"Authorization": f"Bearer {user}"}
        h_admin = {"Authorization": f"Bearer {admin}"}
        with patch.object(espria_system, "PRODUCTION_ACCESS_ENABLED", False):
            self.assertEqual(self.client.get("/production/status", headers=h_admin).status_code, 403)
        with patch.object(espria_system, "PRODUCTION_ACCESS_ENABLED", True):
            self.assertEqual(self.client.get("/production/status", headers=h_user).status_code, 403)
            self.assertEqual(self.client.get("/production/status", headers=h_admin).status_code, 200)


if __name__ == "__main__":
    unittest.main()
