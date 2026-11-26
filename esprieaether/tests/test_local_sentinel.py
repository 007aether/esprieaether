"""Sentinel local : détection FreeLLMAPI / Claude Code et parts sans secret."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "local_sentinel", BASE_DIR / "scripts" / "local_sentinel.py"
)
local_sentinel = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(local_sentinel)


class LocalSentinelTest(unittest.TestCase):
    def test_freellmapi_process_is_detected(self):
        found = local_sentinel.match_command(
            r"C:\Users\aether\Downloads\FreeLLMAPI-0.16.37-win\FreeLLMAPI.exe"
        )
        self.assertIn("freellmapi", found)

    def test_claude_code_process_is_detected_but_desktop_is_not(self):
        code = local_sentinel.match_command(
            r"C:\Users\aether\AppData\Local\Claude-3p\claude-code\2.1.330\claude.exe "
            "--model claude-sonnet-4-5"
        )
        self.assertIn("claude", code)
        desktop = local_sentinel.match_command(
            r"C:\Program Files\WindowsApps\Claude_x\app\Claude.exe --restarted-by-app"
        )
        self.assertNotIn("claude", desktop)

    def test_share_comes_from_allowlisted_ledger_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "model_share.jsonl"
            ledger.write_text(
                "\n".join([
                    json.dumps({"consumer": "atulya", "ok": True}),
                    json.dumps({"consumer": "claude_code", "ok": True}),
                    json.dumps({"consumer": "claude_code", "ok": True}),
                    "{bad",
                    json.dumps({"consumer": "secret", "key": "nope", "ok": True}),
                ]) + "\n",
                encoding="utf-8",
            )
            with patch.object(local_sentinel, "SHARE_LEDGER", ledger):
                snap = local_sentinel.read_share()
        self.assertEqual(snap["counts"], {"atulya": 1, "claude_code": 2})
        self.assertEqual(snap["shares"]["claude_code"], 66.7)
        self.assertEqual(snap["total"], 3)

    def test_share_without_ledger_uses_target_ratio(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(local_sentinel, "SHARE_LEDGER", Path(tmp) / "absent.jsonl"):
                snap = local_sentinel.read_share()
        self.assertEqual(snap["shares"], {"atulya": 60, "claude_code": 40})


if __name__ == "__main__":
    unittest.main()
