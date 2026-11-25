"""J68 — h_ai_think: chaîne 100% locale, sans cloud."""
import unittest
from unittest.mock import patch

from robots import robot_engine


class RobotEngineLocalChainTest(unittest.TestCase):
    def test_local_brain_first_then_freeLLMAPI_then_ollama(self):
        calls = []

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"choices":[{"message":{"content":"OK"}}]}'

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            return FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = robot_engine.h_ai_think("test")

        self.assertTrue(result["ok"])
        self.assertIn("local-brain:dolphin3", result["summary"])
        self.assertEqual(len(calls), 1)
        self.assertIn(":31416", calls[0])

    def test_no_cloud_engine_in_chain(self):
        with open(robot_engine.__file__, encoding="utf-8") as handle:
            source = handle.read()
        start = source.index("def h_ai_think")
        end = source.index("def h_git_status")
        body = source[start:end]
        for forbidden in ("hermes_bridge", "llm7", "groq", "minimax"):
            self.assertNotIn(forbidden, body)


if __name__ == "__main__":
    unittest.main()
