"""Le bridge IA utilise la passerelle locale sans toucher à .env ni exposer la clé."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import hermes_bridge  # noqa: E402


class HermesBridgeConfigTest(unittest.TestCase):
    def test_local_override_is_applied_after_dotenv(self):
        hermes_bridge._load_config()
        self.assertEqual(
            __import__("os").getenv("HERMES_BASE_URL"),
            "http://127.0.0.1:31415/v1",
        )
        bridge = hermes_bridge.HermesBridge()
        self.assertEqual(bridge.base_url, "http://127.0.0.1:31415/v1")
        self.assertEqual(bridge.model, "auto")

    def test_fallback_model_used_when_gateway_cools_down(self):
        import os

        bridge = hermes_bridge.HermesBridge()
        calls = []

        def fake_ask(messages, model=None):
            calls.append(model)
            if model == "auto":
                raise RuntimeError("HTTP 429")
            return "PONG"

        with patch.object(hermes_bridge, "_load_config"), \
             patch.object(bridge, "_local_brain_available", return_value=False), \
             patch.dict(os.environ, {"HERMES_FALLBACK_MODELS": "auto,claude-haiku-4-5"}), \
             patch.object(bridge, "_ask_openai_compatible", side_effect=fake_ask):
            result = bridge.ask("test", use_history=False)
        self.assertEqual(result, "PONG")
        self.assertEqual(calls, ["auto", "claude-haiku-4-5"])

    def test_key_falls_back_to_local_file_without_being_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            key_file = Path(tmp) / "freellmapi.key"
            key_file.write_text("dummy-local-key\n", encoding="utf-8")
            with patch.object(hermes_bridge.os, "getenv", return_value="unused"), \
                 patch.object(hermes_bridge, "LOCAL_KEY", key_file):
                self.assertEqual(hermes_bridge._resolve_key(), "dummy-local-key")


if __name__ == "__main__":
    unittest.main()
