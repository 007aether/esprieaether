"""Somnia opt-in, entrées chat bornées, sources réelles et santé honnête."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))
_TMP_ENV = tempfile.TemporaryDirectory()
os.environ["ESPRIA_STATE_DIR"] = _TMP_ENV.name
os.environ.setdefault("WEB_SECRET_KEY", "test-secret-not-a-real-key")
os.environ.setdefault("LOCAL_BRAIN_PREFER", "0")

import espria_system  # noqa: E402
import web_interface  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from src import local_task_sources as sources  # noqa: E402

LOCAL_REPORT = {
    "router_health": {"active": "dolphin3", "count": 3, "available": ["dolphin3"]},
    "gateway_status": {"provider": "local-brain"},
    "gateway_completion": {"routed_via": "local-brain"},
    "checked_at": "2026-11-23T00:33:23+00:00",
}


class HonestEdgesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        (self.dir / "local_brain_verification.json").write_text(json.dumps(LOCAL_REPORT), encoding="utf-8")
        self.client = web_interface.app.test_client()
        self.gateway = TestClient(espria_system.app)

    def tearDown(self):
        self._tmp.cleanup()

    # ── Somnia : aucun appel réseau par défaut ────────────────────────────────
    def test_somnia_is_opt_in_and_never_calls_network_without_rpc(self):
        with patch.dict(os.environ, {"SOMNIA_RPC": ""}), \
             patch.object(web_interface.urllib.request, "urlopen", side_effect=AssertionError("network!")):
            body = self.client.get("/api/somnia").get_json()
        self.assertEqual(body["status"], "ok")
        self.assertFalse(body["network"]["connected"])
        self.assertEqual(body["network"]["reason"], "not configured")

    def test_somnia_uses_configured_rpc_and_reports_real_block(self):
        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"result": "0x10"}'

        with patch.dict(os.environ, {"SOMNIA_RPC": "http://127.0.0.1:9/rpc"}), \
             patch.object(web_interface.urllib.request, "urlopen", return_value=_Resp()) as call:
            body = self.client.get("/api/somnia").get_json()
        self.assertTrue(body["network"]["connected"])
        self.assertEqual(body["network"]["block"], 16)
        call.assert_called_once()

    # ── Chat : bornes strictes ────────────────────────────────────────────────
    def test_chat_rejects_oversized_prompt_and_max_tokens(self):
        with patch.object(espria_system.llm, "complete", return_value={"status": "success"}) as complete:
            big = self.gateway.post("/chat/completions", json={"prompt": "x" * 20000})
            bad_tokens = self.gateway.post("/chat/completions", json={"prompt": "ping", "max_tokens": 10_000_000})
            bad_system = self.gateway.post("/chat/completions", json={"prompt": "ping", "system": "y" * 20000})
        self.assertEqual(big.status_code, 422, big.text)
        self.assertEqual(bad_tokens.status_code, 422, bad_tokens.text)
        self.assertEqual(bad_system.status_code, 422, bad_system.text)
        complete.assert_not_called()

    def test_chat_accepts_a_valid_bounded_request(self):
        with patch.object(espria_system.llm, "complete", return_value={"status": "success", "text": "PONG"}):
            response = self.gateway.post("/chat/completions", json={"prompt": "ping", "max_tokens": 64})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["text"], "PONG")

    def test_flask_chat_routes_reject_oversized_prompts(self):
        for route in ("/api/jarvis", "/api/hermes"):
            response = self.client.post(route, json={"prompt": "x" * 9000})
            self.assertEqual(response.status_code, 413, response.text)
            self.assertEqual(response.get_json()["error"], "prompt too long")

    # ── Sources réelles : plus de faux zéros ─────────────────────────────────
    def test_missing_modules_report_unavailable_instead_of_zero(self):
        with patch.object(sources, "module_status", return_value={"status": "unavailable", "reason": "module not installed"}):
            analytics = sources.analytics_snapshot()
            guardian = sources.guardian_snapshot()
        self.assertEqual(analytics["status"], "unavailable")
        self.assertNotIn("total_events", analytics)
        self.assertEqual(guardian["status"], "unavailable")
        self.assertNotIn("blocked", guardian)

    def test_semantic_memory_uses_the_real_vector_memory(self):
        snapshot = sources.semantic_memory_snapshot()
        self.assertEqual(snapshot["source"], "vector_memory_agent")
        self.assertIn(snapshot["status"], ("ok", "unavailable"))
        if snapshot["status"] == "ok":
            self.assertIsInstance(snapshot["total"], int)

    def test_analytics_page_never_fabricates_zero_counts(self):
        with patch.object(web_interface, "analytics_snapshot", return_value={"status": "unavailable"}), \
             patch.object(web_interface, "guardian_snapshot", return_value={"status": "unavailable"}), \
             patch.object(web_interface, "semantic_memory_snapshot", return_value={"status": "ok", "total": 7}):
            response = self.client.get("/analytics")
        self.assertEqual(response.status_code, 200)
        self.assertIn("غير متاح", response.text)
        self.assertNotIn(">0</b>", response.text)
        self.assertIn(">7</b>", response.text)

    # ── Santé : service distinct du backend, fraîcheur explicite ─────────────
    def test_health_splits_web_from_backend_and_marks_stale_autonomous_state(self):
        stale = self.dir / "autonomous_state.json"
        stale.write_text(json.dumps({"cycles": 1353, "last_run": {"health_check": "2026-10-20T23:17:17"}}), encoding="utf-8")
        with patch.object(web_interface, "REPORT_DIR", self.dir), \
             patch.object(web_interface, "AUTONOMOUS_STATE_FILE", stale), \
             patch.object(web_interface, "get_ollama_status", return_value={"status": "offline"}):
            body = self.client.get("/api/health").get_json()
        self.assertEqual(body["services"]["web"], "active")
        self.assertEqual(body["services"]["jarvis_backend"], "active")
        self.assertEqual(body["services"]["jarvis_backend_provider"], "local-brain")
        self.assertEqual(body["services"]["jarvis_backend_status"], "active")
        self.assertEqual(body["services"]["ollama"], "inactive")
        self.assertIn("احتياطي", body["services"]["ollama_reason"])
        self.assertNotIn("fallback", body["services"]["ollama_reason"])
        self.assertNotIn("11434", body["services"]["ollama_reason"])
        self.assertEqual(body["services"]["jarvis"], "active")

    def test_health_marks_ollama_reason_active_when_engine_online(self):
        with patch.object(web_interface, "get_ollama_status", return_value={"status": "online"}):
            body = self.client.get("/api/health").get_json()
        self.assertEqual(body["services"]["ollama"], "active")
        self.assertEqual(body["services"]["ollama_reason"], "active")
        self.assertEqual(body["services"]["jarvis_backend"], "active")
        self.assertTrue(body["autonomous"]["stale"])
        self.assertGreater(body["autonomous"]["last_run_age_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
