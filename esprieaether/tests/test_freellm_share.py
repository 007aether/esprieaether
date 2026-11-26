"""Partage local des requêtes : journal sans secret et parts vérifiables."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import freellm_share


class FreeLLMShareTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = Path(self.tmp.name) / "model_share.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _record(self, consumer, model=None, ok=True):
        with patch.object(freellm_share, "LEDGER", self.ledger):
            return freellm_share.record(consumer, model, ok)

    def _snapshot(self):
        with patch.object(freellm_share, "LEDGER", self.ledger):
            return freellm_share.snapshot()

    def test_record_writes_only_allowlisted_fields(self):
        self.assertTrue(self._record("atulya", "gemini-flash-lite", True))
        line = json.loads(self.ledger.read_text(encoding="utf-8").strip())
        self.assertEqual(set(line), {"ts", "consumer", "model", "ok"})
        self.assertEqual(line["consumer"], "atulya")
        self.assertTrue(line["ok"])
        self.assertNotIn("key", line)
        self.assertNotIn("prompt", line)

    def test_record_sanitises_model_and_rejects_unknown_consumer(self):
        self.assertTrue(self._record("claude_code", "claude-sonnet-4-5\nBearer secret", False))
        line = json.loads(self.ledger.read_text(encoding="utf-8").strip())
        self.assertEqual(line["model"], "claude-sonnet-4-5 Bearer secret"[:80])
        self.assertNotIn("\n", line["model"])
        self.assertFalse(self._record("unknown", "x", True))
        self.assertEqual(len(self.ledger.read_text(encoding="utf-8").splitlines()), 1)

    def test_snapshot_computes_real_shares_and_ignores_bad_lines(self):
        self.ledger.write_text(
            "\n".join([
                json.dumps({"consumer": "atulya", "ok": True}),
                json.dumps({"consumer": "claude_code", "ok": False}),
                "{not json",
                json.dumps({"consumer": "intruder", "ok": True}),
                json.dumps({"consumer": "atulya", "ok": True, "model": "dolphin3"}),
            ]) + "\n",
            encoding="utf-8",
        )
        snap = self._snapshot()
        self.assertEqual(snap["counts"], {"atulya": 2, "claude_code": 1})
        self.assertEqual(snap["failed"], {"atulya": 0, "claude_code": 1})
        self.assertEqual(snap["total"], 3)
        self.assertEqual(snap["shares"]["atulya"], 66.7)
        self.assertEqual(snap["last_models"]["atulya"], "dolphin3")

    def test_snapshot_without_ledger_uses_target_ratio(self):
        snap = self._snapshot()
        self.assertEqual(snap["total"], 0)
        self.assertEqual(snap["shares"], {"atulya": 60, "claude_code": 40})

    def test_ratio_is_bounded(self):
        with patch.dict(os.environ, {"FREELLMAPI_SHARE_ATULYA": "500"}):
            self.assertEqual(freellm_share.ratio(), {"atulya": 100, "claude_code": 0})
        with patch.dict(os.environ, {"FREELLMAPI_SHARE_ATULYA": "abc"}):
            self.assertEqual(freellm_share.ratio(), {"atulya": 60, "claude_code": 40})

    def test_choose_favours_consumer_below_target(self):
        self.ledger.write_text(
            "\n".join([json.dumps({"consumer": "atulya", "ok": True})] * 9) + "\n",
            encoding="utf-8",
        )
        self.assertEqual(freellm_share.choose(self._snapshot()), "claude_code")


if __name__ == "__main__":
    unittest.main()
