"""Les cerveaux GGUF locaux sont prioritaires ; la passerelle reste un fallback."""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

_STATE_TMP = tempfile.TemporaryDirectory()
os.environ["ESPRIA_STATE_DIR"] = _STATE_TMP.name
os.environ["WEB_SECRET_KEY"] = "test-secret-not-a-real-key"
os.environ["FREELLMAPI_KEY"] = "test-key-placeholder"

espria_system = importlib.import_module("espria_system")
hermes_bridge = importlib.import_module("hermes_bridge")


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _completion(text, model="dolphin3", routed=None):
    payload = {
        "model": model,
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }
    if routed:
        payload["_routed_via"] = routed
    return _FakeResponse(payload)


class LocalBrainRoutingTest(unittest.TestCase):
    def test_espria_llm_prefers_local_even_without_api_key(self):
        llm = espria_system.EspriaLLM(api_key="", local_enabled=True)
        with patch.object(llm, "_local_available", return_value=True), \
             patch.object(llm, "_post_local", return_value=_completion("LOCAL")) as local, \
             patch.object(llm, "_post") as cloud:
            result = llm.complete("salam")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["text"], "LOCAL")
        self.assertEqual(result["routed_via"], "local-brain")
        self.assertEqual(result["model"], "dolphin3")
        local.assert_called_once()
        cloud.assert_not_called()

    def test_espria_llm_uses_gateway_if_local_fails(self):
        llm = espria_system.EspriaLLM(api_key="test-key-placeholder", local_enabled=True)
        routed = {"platform": "google", "model": "gemini-flash-lite"}
        with patch.object(llm, "_local_available", return_value=True), \
             patch.object(llm, "_post_local", side_effect=RuntimeError("model busy")), \
             patch.object(llm, "_post", return_value=_completion("CLOUD", "gemini", routed)) as cloud:
            result = llm.complete("salam")
        self.assertEqual(result["text"], "CLOUD")
        self.assertEqual(result["routed_via"], routed)
        self.assertIn("local_error", result)
        cloud.assert_called_once()

    def test_hermes_asks_local_brain_before_gateway(self):
        bridge = hermes_bridge.HermesBridge()
        calls = []

        def fake_post(base_url, api_key, messages, model, timeout=None):
            calls.append((base_url, model))
            if "31416" in base_url:
                return "LOCAL"
            raise AssertionError("la passerelle ne doit pas etre appelee")

        with patch.object(hermes_bridge, "_load_config"), \
             patch.object(bridge, "_local_brain_available", return_value=True), \
             patch.object(bridge, "_post_openai", side_effect=fake_post):
            result = bridge.ask("salam", use_history=False)
        self.assertEqual(result, "LOCAL")
        self.assertEqual(calls, [("http://127.0.0.1:31416/v1", "dolphin3")])

    def test_hermes_status_marks_local_brain_as_active(self):
        bridge = hermes_bridge.HermesBridge()
        with patch.object(hermes_bridge, "_load_config"), \
             patch.object(bridge, "_local_brain_available", return_value=True), \
             patch.object(bridge, "_ollama_available", return_value=False):
            status = bridge.status()
        self.assertEqual(status["active_engine"], "local-brain")
        self.assertTrue(status["local_brain"]["available"])


if __name__ == "__main__":
    unittest.main()
