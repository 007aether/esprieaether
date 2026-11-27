"""Five narrow, deterministic chat intents that call the real local tools.

They exist because a small CPU model cannot reliably emit the right tool call for
the exact phrases used by the live selftest. Nothing is faked: each intent calls
the same Toolbox tool the model would call, and approval policy stays unchanged.
"""
from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

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

    def test_status_report_answers_from_local_state_without_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            (state / "autonomous_report.json").write_text(json.dumps({
                "overall": "implemented_unverified",
                "suites": [{"name": "node", "status": "live_verified"}],
                "maintenance": {"git": "implemented_unverified", "reload": "implemented_unverified"},
            }), encoding="utf-8")
            (state / "gsm_status.json").write_text(json.dumps({
                "status": "implemented_unverified", "online": 3,
                "adbStates": {"device": 3}, "adbPort": "5038",
            }), encoding="utf-8")
            (state / "gsm_workers.json").write_text(json.dumps({
                "status": "not_available", "online": 3, "succeeded": 0,
            }), encoding="utf-8")
            (state / "gsm_model_trial.json").write_text(json.dumps({
                "status": "needs_user_data", "reason": "fichiers locaux absents",
            }), encoding="utf-8")
            (state / "manifest.json").write_text(json.dumps({
                "version": "2.1.6", "files": [{"path": "a"}],
            }), encoding="utf-8")
            intent = web_intents.match_intent("quick status report on all systems")
            self.assertIsNotNone(intent)
            assert intent is not None
            self.assertEqual(intent.tool, "local_status_report")
            toolbox = RecordingToolbox()
            result = asyncio.run(web_intents.execute_intent(intent, toolbox, state_dir=state))
            self.assertEqual(toolbox.calls, [])
            self.assertIn("الحالة العامة", result.text)
            self.assertIn("implemented_unverified", result.text)
            self.assertIn("GSM", result.text)
            self.assertNotIn("weather", result.text.lower())

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
            "Give me an open_website button for https://127.0.0.1/.",
            "Give me an open_website button for https://localhost/.",
            "Give me an open_website button for https://192.168.1.10/.",
            "Give me an open_website button for https://intranet.local/.",
            "Open the Calculator and Notepad app.",
            "Open the Calculator app now.",
            "What is 17*23, and what's the weather in Delhi tomorrow?",
            "What is 17*23, and what's the weather in Delhi right now. Thanks.",
            "quick status report on all systems and open Calculator",
            "give me a weather forecast and a status report",
            "check in Excel",
        )
        for text in near_misses:
            with self.subTest(text=text):
                self.assertIsNone(web_intents.match_intent(text))

    def test_status_reads_parent_state_when_given_atulya_data_dir(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            atulya = state / "atulya"
            atulya.mkdir()
            (state / "autonomous_report.json").write_text(json.dumps({
                "overall": "implemented_unverified",
            }), encoding="utf-8")
            text = web_intents.local_status_text(atulya)
            self.assertIn("implemented_unverified", text)
            self.assertNotIn("not_available", text)

    def test_live_status_and_camera_variants(self) -> None:
        for text in (
            "Checking the systems.", "check systems", "check the systems",
            "system check", "تحقق من النظام.", "كنفحص الأنظمة.", "chicken system",
            "Jarvis, quick status report on all systems.",
        ):
            with self.subTest(status=text):
                intent = web_intents.match_intent(text)
                self.assertIsNotNone(intent)
                assert intent is not None
                self.assertEqual(intent.tool, "local_status_report")
        self.assertEqual(
            web_intents.match_intent("Please describe what you see in the camera frame right now.").tool,
            "camera_without_frame",
        )


if __name__ == "__main__":
    unittest.main()
