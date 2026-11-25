"""Gate tests for espria_bot (dry-run only, no Telegram network calls)."""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

_TMP = tempfile.TemporaryDirectory()
_fake_env = Path(_TMP.name) / "bot.env"
_fake_env.write_text(
    "TELEGRAM_BOT_TOKEN=dummy-token-not-real\nTELEGRAM_CHAT_ID=12345\nBOT_NAME=test-bot\n",
    encoding="utf-8",
)
os.environ["BOT_ENV_FILE"] = str(_fake_env)
os.environ["TELEGRAM_LIVE"] = "0"

espria_bot = importlib.import_module("espria_bot")


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class EspriaBotTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        _TMP.cleanup()

    def test_dry_run_report_never_contacts_telegram_or_logs_token(self):
        director = {
            "agent": "director",
            "status": "ok",
            "summary": {"agents_total": 8, "products_count": 2, "todo_count": 3, "kpis": [{"metric": "x", "count": 1}]},
        }
        kpis = [{"metric": "tasks_done", "count": 4}]
        bot = espria_bot.BotRunner()

        with patch.object(bot, "_get_json", side_effect=[director, kpis]) as getter:
            report = bot.build_report()
        self.assertIn("8", report)
        self.assertIn("tasks_done", report)
        self.assertEqual(getter.call_count, 2)

        with patch.object(espria_bot.httpx, "post") as post:
            result = bot.send(report)
        post.assert_not_called()
        self.assertEqual(result["mode"], "dry_run")
        self.assertFalse(result["delivered"])

        log_text = Path(result["log"]).read_text(encoding="utf-8")
        self.assertIn("tasks_done", log_text)
        self.assertNotIn("dummy-token-not-real", log_text)

    def test_live_flag_is_explicit(self):
        os.environ["TELEGRAM_LIVE"] = "0"
        self.assertFalse(espria_bot.BotRunner().live)
        os.environ["TELEGRAM_LIVE"] = "1"
        try:
            self.assertTrue(espria_bot.BotRunner().live)
        finally:
            os.environ["TELEGRAM_LIVE"] = "0"

    def test_live_error_never_leaks_token(self):
        request = espria_bot.httpx.Request("POST", "https://api.telegram.org/botSECRET_TOKEN/sendMessage")
        response = espria_bot.httpx.Response(401)
        error = espria_bot.httpx.HTTPStatusError("401", request=request, response=response)
        os.environ["TELEGRAM_LIVE"] = "1"
        try:
            bot = espria_bot.BotRunner()
            with patch.object(espria_bot.httpx, "post", side_effect=error):
                result = bot.send("test")
        finally:
            os.environ["TELEGRAM_LIVE"] = "0"
        self.assertFalse(result["delivered"])
        self.assertNotIn("SECRET_TOKEN", result["error"])
        self.assertIn("401", result["error"])


if __name__ == "__main__":
    unittest.main()
