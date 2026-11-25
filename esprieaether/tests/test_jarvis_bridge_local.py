"""J88 — Jarvis doit parler au routeur local, avec un timeout unique et un retry prudent."""

import sys
import unittest
from pathlib import Path
from unittest import mock

import requests

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import jarvis_bridge as bridge  # noqa: E402


class FakeResponse:
    def __init__(self, status, payload, headers=None):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def json(self):
        return self._payload


def ok(text="مرحبا"):
    return FakeResponse(200, {"choices": [{"message": {"content": text}}]})


class JarvisBridgeLocalTest(unittest.TestCase):
    def test_defaults_point_to_the_local_router_without_a_key(self):
        self.assertEqual(bridge.DEFAULT_HOST.rstrip("/"), "http://127.0.0.1:31416")
        self.assertEqual(bridge.DEFAULT_MODEL, "dolphin3")
        self.assertEqual(bridge.REQUEST_TIMEOUT, 120)

    def test_ask_uses_the_openai_compatible_route(self):
        bot = bridge.JarvisBridge()
        with mock.patch.object(bridge.requests, "post", return_value=ok()) as post:
            self.assertEqual(bot.ask("مرحبا", system="sys", use_history=False), "مرحبا")
        args, kwargs = post.call_args
        self.assertEqual(args[0], "http://127.0.0.1:31416/v1/chat/completions")
        self.assertEqual(kwargs["timeout"], 120)
        self.assertNotIn("Authorization", kwargs.get("headers", {}))
        self.assertEqual(kwargs["json"]["model"], "dolphin3")

    def test_ask_retries_once_after_busy(self):
        bot = bridge.JarvisBridge()
        busy = FakeResponse(429, {"error": {"message": "busy"}}, {"Retry-After": "1"})
        with mock.patch.object(bridge.requests, "post", side_effect=[busy, ok("جاهز")]) as post, \
                mock.patch.object(bridge.time, "sleep") as sleep:
            self.assertEqual(bot.ask("hi", use_history=False), "جاهز")
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(1.0)

    def test_ask_never_invents_a_reply_when_still_busy(self):
        bot = bridge.JarvisBridge()
        busy = FakeResponse(429, {"error": {"message": "busy"}}, {"Retry-After": "1"})
        with mock.patch.object(bridge.requests, "post", side_effect=[busy, busy]) as post, \
                mock.patch.object(bridge.time, "sleep"):
            reply = bot.ask("hi", use_history=False)
        self.assertEqual(post.call_count, 2)
        self.assertIn("مشغول", reply)
        self.assertEqual(bot.history, [])

    def test_ping_uses_the_local_models_endpoint(self):
        bot = bridge.JarvisBridge()
        response = FakeResponse(200, {"data": [{"id": "dolphin3"}]})
        with mock.patch.object(bridge.requests, "get", return_value=response) as get:
            status = bot.ping()
        self.assertEqual(get.call_args.args[0], "http://127.0.0.1:31416/v1/models")
        self.assertEqual(status["status"], "online")
        self.assertTrue(status["model_ready"])


if __name__ == "__main__":
    unittest.main()
