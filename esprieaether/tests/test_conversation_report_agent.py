"""J141 — وكيل التقارير المحلي: تقرير صادق + رسالة Atulya + مقترحات معلّقة."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "esprieaether" / "src"
VENDOR = ROOT / "GITHUB_IMPORT" / "Atulya-Tantra"
for _path in (SRC, VENDOR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
ALLOWED = {"live_verified", "implemented_unverified", "not_available", "needs_user_data"}


class ConversationReportAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.state = root / "state"
        self.atulya = root / "atulya"
        self.state.mkdir()
        self.atulya.mkdir()
        self._write("autonomous_report.json", {
            "generatedAt": "2026-11-26T11:00:00Z",
            "overall": "implemented_unverified",
            "maintenance": {"git": "implemented_unverified", "reload": "implemented_unverified"},
            "missing": [{"name": "gsm-model-trial", "status": "needs_user_data"}],
        })
        self._write("gsm_status.json", {
            "status": "implemented_unverified", "online": 3,
            "adbStates": {"device": 3, "offline": 0, "unauthorized": 0},
            "readOnly": True, "checkedAt": "2026-11-26T11:00:00Z",
        })
        self._write("gsm_workers.json", {
            "status": "not_available", "online": 3, "succeeded": 0, "errors": ["timeout"],
            "checkedAt": "2026-11-26T11:00:00Z",
        })
        self._write("gsm_model_trial.json", {
            "status": "needs_user_data",
            "reason": "binaire llama.cpp arm64 ELF local absent; GGUF local <= 600 Mo absent",
        })
        self._write("manifest.json", {"version": "2.1.6", "files": [{"path": "a"}]})
        self._write("secret.json", {"api_key": "supersecretvalue"})

    def _write(self, name: str, data: object) -> None:
        (self.state / name).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_build_collecte_les_sources_sans_secret(self) -> None:
        from conversation_report_agent import build
        report = build(self.state, now=NOW)
        self.assertIn(report["overall"], ALLOWED)
        self.assertEqual(report["gsm"]["scan"]["online"], 3)
        self.assertEqual(report["gsm"]["probe"]["status"], "not_available")
        self.assertEqual(report["manifest"]["version"], "2.1.6")
        text = report["text"]
        self.assertNotIn("supersecretvalue", text)
        self.assertIn("الحالة العامة", text)
        self.assertIn("GSM", text)

    def test_run_ecrit_un_message_et_des_propositions_sans_executer(self) -> None:
        from atulya.history import ConversationHistory
        from conversation_report_agent import CONVERSATION_ID, run
        result = run(self.state, atulya_data_dir=self.atulya, now=NOW, force=True)
        self.assertTrue(result["ok"])
        history = ConversationHistory(self.atulya)
        rows = history.read(CONVERSATION_ID, user_id="admin")
        self.assertEqual(rows[0]["role"], "user")
        self.assertIn("تقرير الوكيل", rows[0]["content"])
        self.assertTrue(all(row["role"] == "assistant" for row in rows[1:]))
        self.assertTrue(all(0 < len(row["content"]) <= 20_000 for row in rows))
        proposals = json.loads((self.state / "action_requests.json").read_text(encoding="utf-8"))
        self.assertTrue(proposals)
        self.assertTrue(all(row["status"] == "proposed" for row in proposals))
        self.assertTrue(all(row["source"] == "wakil_report" for row in proposals))
        audit = (self.state / "action_audit.jsonl").read_text(encoding="utf-8")
        self.assertIn('"to": "proposed"', audit)
        self.assertNotIn('"to": "executed"', audit)

    def test_run_ne_duplique_pas_avant_vingt_quatre_heures(self) -> None:
        from conversation_report_agent import CONVERSATION_ID, run
        first = run(self.state, atulya_data_dir=self.atulya, now=NOW, force=True)
        self.assertTrue(first["ok"])
        self.assertTrue(first["ran"])
        second = run(self.state, atulya_data_dir=self.atulya,
                     now=NOW + timedelta(hours=2))
        self.assertFalse(second["ran"])
        self.assertEqual(second["messages"], 0)

    def test_les_status_inconnus_sont_degrades_sans_inventer(self) -> None:
        from conversation_report_agent import normalize_status
        self.assertEqual(normalize_status("fantome"), "not_available")
        self.assertEqual(normalize_status(None), "not_available")
        self.assertEqual(normalize_status("live_verified"), "live_verified")

    def test_les_propositions_connues_ne_sont_pas_reajoutees(self) -> None:
        from conversation_report_agent import propose_suggestions
        from action_request import ActionRequests
        store = ActionRequests(
            str(self.state / "action_requests.json"),
            str(self.state / "action_audit.jsonl"),
        )
        suggestions = [
            {"action": "demo_action", "target": "local", "reason": "test"},
            {"action": "demo_action", "target": "local", "reason": "test"},
        ]
        first = propose_suggestions(store, suggestions, source="wakil_report")
        second = propose_suggestions(store, suggestions, source="wakil_report")
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])


if __name__ == "__main__":
    unittest.main()
