"""J118/J141 — TDD : ordonnanceur local quotidien des cinq agents (sans réseau)."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)


class DailyOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name)
        self.calls: list[str] = []

    def _runners(self, fail: str | None = None) -> dict:
        def make(name: str) -> object:
            def runner(state_dir: Path) -> dict:
                self.calls.append(name)
                if name == fail:
                    raise RuntimeError("panne locale simulée")
                return {"ok": True, "status": "live_verified", "id": name}
            return runner
        return {name: make(name) for name in (
            "github-scout", "doctor", "rea", "learning", "conversation-report")}

    def test_run_once_appelle_les_cinq_agents_et_ecrit_le_rapport(self) -> None:
        from daily_orchestrator import run_once
        report = run_once(self.state, runners=self._runners(), now=NOW)
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "live_verified")
        self.assertEqual([t["id"] for t in report["tasks"]],
                         ["github-scout", "doctor", "rea", "learning", "conversation-report"])
        self.assertEqual(self.calls,
                         ["github-scout", "doctor", "rea", "learning", "conversation-report"])
        raw = (self.state / "daily_orchestrator_report.json").read_text(encoding="utf-8")
        saved = json.loads(raw)
        self.assertEqual(saved["checked_at"], "2026-11-26T12:00:00+00:00")
        self.assertNotIn("token", raw.lower())

    def test_un_agent_en_panne_ne_bloque_pas_les_autres(self) -> None:
        from daily_orchestrator import run_once
        report = run_once(self.state, runners=self._runners(fail="doctor"), now=NOW)
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "partial")
        rows = {t["id"]: t for t in report["tasks"]}
        self.assertFalse(rows["doctor"]["ok"])
        self.assertTrue(rows["rea"]["ok"])
        self.assertTrue(rows["learning"]["ok"])
        self.assertEqual(self.calls.count("rea"), 1)

    def test_due_sans_rapport_et_apres_24h(self) -> None:
        from daily_orchestrator import due
        self.assertTrue(due(self.state, now=NOW))
        path = self.state / "daily_orchestrator_report.json"
        path.write_text(json.dumps({"checked_at": "2026-11-26T12:00:00+00:00"}), encoding="utf-8")
        self.assertFalse(due(self.state, now=NOW + timedelta(hours=23)))
        self.assertTrue(due(self.state, now=NOW + timedelta(hours=25)))
        path.write_text("{invalid", encoding="utf-8")
        self.assertTrue(due(self.state, now=NOW))

    def test_run_due_sauted_une_seconde_journee(self) -> None:
        from daily_orchestrator import run_due
        first = run_due(self.state, runners=self._runners(), now=NOW)
        self.assertTrue(first["ran"])
        second = run_due(self.state, runners=self._runners(), now=NOW + timedelta(hours=2))
        self.assertFalse(second["ran"])
        self.assertEqual(second["report"]["status"], "live_verified")
        self.assertEqual(len(self.calls), 5)

    def test_liste_des_taches_est_locale_et_ordonee(self) -> None:
        from daily_orchestrator import TASKS
        self.assertEqual([t["id"] for t in TASKS],
                         ["github-scout", "doctor", "rea", "learning", "conversation-report"])
        for task in TASKS:
            self.assertTrue(task["module"].startswith("esprieaether.") or
                            task["module"] in {"github_scout", "doctor_agent",
                                               "rea_agent", "learning_agent",
                                               "conversation_report_agent"})
            self.assertNotIn("http", task["module"])

    def test_main_affiche_un_resume_par_arabe(self) -> None:
        from daily_orchestrator import main, run_due
        run_due(self.state, runners=self._runners(), now=NOW)
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(self.state, now=NOW)
        text = buf.getvalue()
        self.assertTrue(any("\u0600" <= ch <= "\u06ff" for ch in text))


if __name__ == "__main__":
    unittest.main()
