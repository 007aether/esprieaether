"""J123 — TDD : le docteur applique aussi les correctifs de code autorisés."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import doctor_agent  # noqa: E402


class DoctorAutoFixTest(unittest.TestCase):
    def test_run_applique_un_correctif_de_code_blanc_liste_et_previent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = root / "allowed.py"
            code.write_text("VALUE=1\n", encoding="utf-8")
            state = root / "state"
            state.mkdir()
            finding = {"kind": "missing_severity", "source": "self_improve.py",
                       "detail": "severity absent", "severity": "urgent"}
            fix = {"id": "dtest", "kind": "missing_severity", "target": str(code),
                   "reason": "correctif local", "old": "VALUE=1", "new": "VALUE=2",
                   "severity": "urgent", "needs_restart": False}
            with patch.object(doctor_agent, "detect", return_value=[finding]), \
                 patch.object(doctor_agent, "propose", return_value=[fix]), \
                 patch.object(doctor_agent, "_CODE_ROOTS", frozenset({code.resolve()})):
                report = doctor_agent.run(state)

            self.assertEqual(code.read_text(encoding="utf-8"), "VALUE=2\n")
            self.assertGreaterEqual(report["fixed"], 1)
            self.assertGreaterEqual(report["codeFixed"], 1)
            notices = (state / "doctor_notices.jsonl").read_text(encoding="utf-8")
            self.assertIn("dtest", notices)
            self.assertFalse(report.get("needsRestart", False))
            self.assertIn("codeFixed", json.loads(
                (state / "doctor_selfcheck.json").read_text(encoding="utf-8")))

    def test_detect_voit_le_defaut_de_severity_dans_propose_fixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(doctor_agent, "_code_has_severity_bug", return_value=True):
                findings = doctor_agent.detect(Path(tmp))
            self.assertTrue(any(f["kind"] == "missing_severity" for f in findings))

    def test_run_corrige_le_defaut_reel_de_propose_fixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = root / "self_improve.py"
            code.write_text(doctor_agent._SEVERITY_OLD + "\n", encoding="utf-8")
            state = root / "state"
            state.mkdir()
            with patch.object(doctor_agent, "_code_has_severity_bug", return_value=True), \
                    patch.object(doctor_agent, "_CODE_ROOTS", frozenset({code.resolve()})), \
                    patch.object(doctor_agent, "_CODE_TARGET", str(code)):
                report = doctor_agent.run(state)
            self.assertIn("severity = item.get", code.read_text(encoding="utf-8"))
            self.assertGreaterEqual(report["codeFixed"], 1)
            notices = (state / "doctor_notices.jsonl").read_text(encoding="utf-8")
            self.assertIn("إصلاح آمن", notices)

    def test_aucun_correctif_ne_demande_redemarrage_ou_reseau(self) -> None:
        source = (SRC / "doctor_agent.py").read_text(encoding="utf-8")
        self.assertNotIn("import urllib", source)
        self.assertNotIn("import requests", source)
        self.assertNotIn("pkill" + "", source)
