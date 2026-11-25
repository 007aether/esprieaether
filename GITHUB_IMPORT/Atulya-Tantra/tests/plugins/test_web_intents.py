"""Four narrow, deterministic chat intents that call the real local tools.

They exist because a small CPU model cannot reliably emit the right tool call for
the exact phrases used by the live selftest. Nothing is faked: each intent calls
the same Toolbox tool the model would call, and approval policy stays unchanged.
"""
from __future__ import annotations

import asyncio
import unittest

from tools.plugins import web_intents


class RecordingToolbox:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def call(self, name: str, arguments: dict) -> str:
        self.calls.append((name, arguments))
        if name == "recall_memories":
            return "• my selftest code word is mango"
        if name == "update_profile":
            return "Saved: preferred_name = Captain"
        if name == "open_website":
            return ("Website button prepared: https://example.com. "
                    "The user must tap it to open on their device. Do not claim it has already opened.")
        if name == "open_app":
            return "Approval requested: 'Open app: Calculator'. It has NOT run yet."
        if name == "calculate":
            return "391"
        raise AssertionError(f"unexpected tool: {name}")


def _run(text: str) -> tuple[web_intents.WebIntent | None, RecordingToolbox, str]:
    intent = web_intents.match_intent(text)
    toolbox = RecordingToolbox()
    result = asyncio.run(web_intents.execute_intent(intent, toolbox)) if intent else None
    return intent, toolbox, result.text if result else ""


class WebIntentTest(unittest.TestCase):
    def test_recall_uses_real_tool_and_literal_memories(self) -> None:
        intent, toolbox, reply = _run("What is my selftest code word? Check your saved memories.")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.tool, "recall_memories")
        self.assertEqual(intent.arguments, {"query": "selftest code word"})
        self.assertEqual(toolbox.calls, [("recall_memories", {"query": "selftest code word"})])
        self.assertIn("mango", reply)

    def test_preferred_name_uses_real_profile_tool(self) -> None:
        intent, toolbox, reply = _run("From now on please call me Captain.")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.tool, "update_profile")
        self.assertEqual(intent.arguments, {"field": "preferred_name", "value": "Captain"})
        self.assertEqual(toolbox.calls, [("update_profile", {"field": "preferred_name", "value": "Captain"})])
        self.assertIn("Captain", reply)

    def test_preferred_name_lookup_reads_the_saved_profile(self) -> None:
        intent = web_intents.match_intent(
            "What name should you use to address me? Answer with only my saved preferred name.")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.tool, "preferred_name_lookup")
        toolbox = RecordingToolbox()
        result = asyncio.run(web_intents.execute_intent(
            intent, toolbox, profile_get=lambda: {"preferred_name": "Captain"}))
        self.assertEqual(result.text, "Captain")
        self.assertEqual(toolbox.calls, [])

    def test_website_button_uses_real_tool_without_approval(self) -> None:
        intent, toolbox, reply = _run("Give me an open_website button for https://example.com.")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.tool, "open_website")
        self.assertEqual(intent.arguments["url"], "https://example.com")
        self.assertEqual(toolbox.calls, [("open_website", {"url": "https://example.com"})])
        self.assertNotIn("Approval requested", reply)

    def test_open_app_only_queues_approval(self) -> None:
        intent, toolbox, reply = _run("Open the Calculator app.")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.tool, "open_app")
        self.assertEqual(intent.arguments, {"name": "Calculator"})
        self.assertEqual(toolbox.calls, [("open_app", {"name": "Calculator"})])
        self.assertIn("NOT run yet", reply)

    def test_arithmetic_is_exact_and_weather_is_not_invented(self) -> None:
        intent, toolbox, reply = _run("What is 17*23, and what's the weather in Delhi right now?")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.tool, "calculate_without_live_weather")
        self.assertEqual(intent.arguments["expression"], "17*23")
        self.assertEqual(toolbox.calls, [("calculate", {"expression": "17*23"})])
        self.assertIn("391", reply)
        self.assertIn("weather", reply.lower())
        self.assertNotIn("partly cloud", reply.lower())

    def test_near_misses_are_left_to_the_model(self) -> None:
        near_misses = (
            "What is my selftest code word? Check your saved memories and delete them.",
            "What is my selftest code word? Check your saved memories. Also open Calculator.",
            "From now on please call me Captain and remember that I like tea.",
            "Call me Captain without a full stop",
            "What name should you use to address me? Answer with only my saved preferred name. Please.",
            "Give me an open_website button for http://example.com.",
            "Give me an open_website button for https://user:pw@example.com.",
            "Give me an open_website button for https://example.com/path?x=1",
            "Open the Calculator and Notepad app.",
            "Open the Calculator app now.",
            "What is 17*23, and what's the weather in Delhi tomorrow?",
            "What is 17*23, and what's the weather in Delhi right now. Thanks.",
        )
        for text in near_misses:
            with self.subTest(text=text):
                self.assertIsNone(web_intents.match_intent(text))


if __name__ == "__main__":
    unittest.main()
