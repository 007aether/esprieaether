"""Gate tests for espria_system (O4 auth, O8 KPI, O20 LLM router, O11 readiness).

Run with: .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

_TMP = tempfile.TemporaryDirectory()
os.environ["ESPRIA_STATE_DIR"] = _TMP.name
os.environ["WEB_SECRET_KEY"] = "test-secret-not-a-real-key"
os.environ["FREELLMAPI_KEY"] = "test-key-placeholder"
os.environ["FREE_LLM_BASE_URL"] = "http://127.0.0.1:31415"
os.environ["LOCAL_BRAIN_PREFER"] = "0"  # test isolé : pas de routeur GGUF réel
os.environ.pop("GITHUB_PRIVATE_KEY", None)

espria_system = importlib.import_module("espria_system")

from fastapi.testclient import TestClient  # noqa: E402


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class EspriaSystemTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(espria_system.app)
        cls.client.__enter__()
        cls.token = None

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        _TMP.cleanup()

    def _signup(self, username):
        response = self.client.post(
            "/signup",
            json={"username": username, "password": "Motdepasse123!", "email": f"{username}@local.test"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_00_startup_creates_schema_idempotently(self):
        conn = espria_system.get_db()
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
        self.assertTrue({"users", "kpis", "modules"}.issubset(tables))
        espria_system.init_db()  # second call must not fail
        self.assertTrue(espria_system.DB_PATH.is_file())

    def test_01_auth_flow_and_role_cannot_be_escalated(self):
        created = self._signup("kamal")
        self.assertEqual(created["user"]["role"], "user")
        self.assertEqual(created["token_type"], "bearer")
        self.token = created["access_token"]

        login = self.client.post("/login", json={"username": "kamal", "password": "Motdepasse123!"})
        self.assertEqual(login.status_code, 200, login.text)
        self.assertTrue(login.json()["access_token"])

        me = self.client.get("/me", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["username"], "kamal")

        self.assertEqual(self.client.get("/me").status_code, 401)
        self.assertEqual(
            self.client.get("/me", headers={"Authorization": "Bearer tampered.token"}).status_code,
            401,
        )

        escalated = self.client.post(
            "/signup",
            json={"username": "admin_wannabe", "password": "Motdepasse123!", "role": "admin"},
        )
        self.assertEqual(escalated.json()["user"]["role"], "user")

    def test_02_kpi_record_get_all_and_path_compat(self):
        first = self.client.post("/kpi", json={"metric": "tasks_done", "value": 2, "window": "day"})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["status"], "recorded")

        second = self.client.post("/kpi/tasks_done", params={"value": 3})
        self.assertEqual(second.status_code, 200, second.text)

        got = self.client.get("/kpi/tasks_done")
        self.assertEqual(got.json()["count"], 2)
        self.assertEqual(got.json()["total"], 5)

        all_kpis = self.client.get("/kpi/all").json()
        self.assertTrue(any(row["metric"] == "tasks_done" for row in all_kpis))

        missing = self.client.post("/kpi", json={"metric": "bad"})
        self.assertEqual(missing.status_code, 422)

    def test_03_llm_router_uses_openai_compatible_api_without_secrets(self):
        payload = {
            "id": "chatcmpl-test",
            "model": "gemini-flash-lite-latest",
            "choices": [{"message": {"role": "assistant", "content": "PONG"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "_routed_via": {"platform": "google", "model": "gemini-flash-lite-latest"},
        }
        with patch.object(espria_system.llm, "_local_available", return_value=False), \
             patch.object(espria_system.llm, "_post", return_value=_FakeResponse(payload)) as post:
            reply = self.client.post("/chat/completions", json={"prompt": "ping"})
        self.assertEqual(reply.status_code, 200, reply.text)
        self.assertEqual(reply.json()["text"], "PONG")
        self.assertEqual(reply.json()["status"], "success")
        self.assertNotIn("test-key-placeholder", reply.text)
        request = post.call_args.args[0]
        self.assertEqual(request["model"], espria_system.FREELLMAPI_MODEL)
        self.assertEqual(request["messages"][-1]["content"], "ping")

        with patch.object(espria_system.llm, "_local_available", return_value=False), \
             patch.object(espria_system.llm, "api_key", ""):
            no_key = self.client.post("/chat/completions", json={"prompt": "ping"})
        self.assertEqual(no_key.json()["status"], "no_api_key")

        status = self.client.get("/llm/status").json()
        expected = "local-brain" if status["local_brain"]["available"] else "freellmapi-api"
        self.assertEqual(status["provider"], expected)
        self.assertNotIn("key", str(status.get("api_key_configured", "")))

    def test_04_github_readiness_never_pushes(self):
        response = self.client.get("/github/push-status")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["push_performed"])
        self.assertFalse(body["private_key_available"])
        self.assertIn("clé privée", body["message"])

    def test_05_agents_registry_and_reports_use_real_sources(self):
        state = {
            "version": 1,
            "fields": {"f-a": "2.75", "g-rate": "20", "g-margin": "30"},
            "products": [{"name": "فرن"}],
            "inventory": [{"item": "حديد"}],
            "todo": [{"id": 1, "text": "مراجعة السعر"}],
        }
        with patch.object(espria_system, "_dashboard_state", return_value=state):
            listing = self.client.get("/agents")
            self.assertEqual(listing.status_code, 200, listing.text)
            ids = {a["id"] for a in listing.json()}
            self.assertTrue({"A1", "A2", "A3", "A4", "M1", "L1", "L2", "director"}.issubset(ids))

            price = self.client.get("/agents/A2/run")
            self.assertEqual(price.status_code, 200, price.text)
            self.assertEqual(price.json()["status"], "ok")
            self.assertEqual(price.json()["summary"]["g_rate"], "20")

            plans = self.client.get("/agents/A3/run")
            self.assertEqual(plans.json()["summary"]["todo_count"], 1)

            no_source = self.client.get("/agents/A4/run")
            self.assertEqual(no_source.json()["status"], "no_data_source")

            director = self.client.get("/agents/director/run")
            self.assertEqual(director.json()["status"], "ok")
            self.assertIn("agents_total", director.json()["summary"])

        self.assertEqual(self.client.get("/agents/unknown/run").status_code, 404)

    def test_06_a3_run_accepts_the_real_dict_shaped_todo(self):
        """Régression live : DashboardState.todo est un objet, pas une liste (contract.mjs)."""
        state = {
            "version": 1,
            "fields": {},
            "products": [],
            "inventory": [],
            "todo": {f"c{i}": bool(i % 2) for i in range(1, 9)},
        }
        with patch.object(espria_system, "_dashboard_state", return_value=state):
            response = self.client.get("/agents/A3/run")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["summary"]["todo_count"], 8)
        self.assertIsInstance(body["summary"]["items"], list)
        self.assertEqual(len(body["summary"]["items"]), 8)


if __name__ == "__main__":
    unittest.main()
