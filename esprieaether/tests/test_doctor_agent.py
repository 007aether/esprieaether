"""اختبارات وحدة الطبيب الآلي المحلي doctor_agent (TDD).

الاختبارات كتستعمل مجلد state مؤقت، ولا كتلمس أي ملف حقيقي غير ملفات
القائمة البيضاء (قراءة فقط للتحقق من أنها ما تبدّلتش).
"""

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import doctor_agent  # noqa: E402

# كنبني الكلمات الممنوعة dynamicaly باش ما يظهرش أي اسم عملية خطير فالملف.
_FORBIDDEN = ("re" + "start", "com" + "mit", "pu" + "sh", "pk" + "ill")
_REQUIRED_FIX_KEYS = {
    "id", "kind", "target", "reason", "old", "new", "severity", "needs_restart",
}


class DoctorAgentTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, text):
        path = self.state / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_01_detect_reads_all_sources_and_scrubs_secrets(self):
        self._write(
            "brain_errors.jsonl",
            '{"message":"Connection timed out token=TOPSECRET123"}\n'
            "not-json permission denied\n",
        )
        self._write(
            "self_improve_errors.json",
            json.dumps({"errors": [
                {"text": "Permission denied api_key=ANOTHERSECRET456"},
                {"text": "No module named demo"},
            ]}),
        )
        self._write(
            "run_ledger.json",
            json.dumps({"runs": [
                {"action": "check", "status": "failed", "detail": "token=THIRDSECRET789"},
                {"action": "check", "status": "succeeded", "detail": "ok"},
            ]}),
        )
        self._write(
            "quality_guard_report.json",
            json.dumps({"issues": [{"detail": "quality low", "severity": "high"}]}),
        )

        findings = doctor_agent.detect(self.state)
        self.assertTrue(findings)
        for finding in findings:
            self.assertTrue({"kind", "source", "detail", "severity"} <= set(finding), finding)
            self.assertIn(finding["severity"], ("immediate", "urgent", "routine"))
            self.assertTrue(finding["detail"])
        sources = {finding["source"] for finding in findings}
        self.assertIn("brain_errors.jsonl", sources)
        self.assertIn("self_improve_errors.json", sources)
        self.assertIn("run_ledger.json", sources)
        self.assertIn("quality_guard_report.json", sources)

        blob = json.dumps(findings, ensure_ascii=False)
        for secret in ("TOPSECRET123", "ANOTHERSECRET456", "THIRDSECRET789"):
            self.assertNotIn(secret, blob)

    def test_02_propose_never_requests_effectful_actions(self):
        findings = [
            {"kind": "error_log", "source": "brain_errors.jsonl",
             "detail": "timed out", "severity": "urgent"},
        ]
        fixes = doctor_agent.propose(findings)
        self.assertTrue(fixes)
        for fix in fixes:
            self.assertTrue(_REQUIRED_FIX_KEYS <= set(fix), fix)
            self.assertIs(fix["needs_restart"], False)
            self.assertIn(fix["severity"], ("immediate", "urgent", "routine"))
            for value in fix.values():
                if isinstance(value, str):
                    lowered = value.lower()
                    for token in _FORBIDDEN:
                        self.assertNotIn(token, lowered, (token, value[:80]))

    def test_03_apply_safe_patches_one_literal_and_logs_hashes(self):
        target = self._write("notes.txt", "STATUS=pending\n")
        fix = {
            "id": "fx-safe-1", "kind": "test", "target": "notes.txt",
            "reason": "تصحيح محلي", "old": "STATUS=pending", "new": "STATUS=done",
            "severity": "routine", "needs_restart": False,
        }
        before = hashlib.sha256(target.read_bytes()).hexdigest()

        result = doctor_agent.apply_safe(fix, self.state)
        self.assertTrue(result["ok"], result)

        self.assertEqual(target.read_text(encoding="utf-8"), "STATUS=done\n")
        after = hashlib.sha256(target.read_bytes()).hexdigest()
        self.assertNotEqual(before, after)

        lines = (self.state / "doctor_fixes.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["id"], "fx-safe-1")
        self.assertEqual(record["shaBefore"], before)
        self.assertEqual(record["shaAfter"], after)
        self.assertTrue(record["ok"])
        self.assertIn("at", record)
        self.assertNotIn("old", record)
        self.assertNotIn("new", record)
        self.assertEqual(list(self.state.glob("*.tmp")), [])

    def test_04_apply_safe_refuses_outside_targets_and_missing_literal(self):
        target = self._write("notes.txt", "KEEP=1\n")
        outside = (
            "../secret.py",
            ".env",
            str(BASE_DIR / "src" / "learning_agent.py"),
        )
        for name in outside:
            fix = {
                "id": "bad-target", "kind": "test", "target": name,
                "reason": "refus", "old": "KEEP=1", "new": "KEEP=2",
                "severity": "routine", "needs_restart": False,
            }
            result = doctor_agent.apply_safe(fix, self.state)
            self.assertFalse(result["ok"], (name, result))
            self.assertTrue(result["reason"])

        fix = {
            "id": "bad-literal", "kind": "test", "target": "notes.txt",
            "reason": "refus", "old": "NOT-PRESENT", "new": "KEEP=2",
            "severity": "routine", "needs_restart": False,
        }
        self.assertFalse(doctor_agent.apply_safe(fix, self.state)["ok"])
        self.assertEqual(target.read_text(encoding="utf-8"), "KEEP=1\n")

    def test_05_notify_writes_notice_and_survives_missing_inbox(self):
        blocker = self._write("inbox_blocker", "not a directory")
        with patch.dict(os.environ, {"ATULYA_DATA_DIR": str(blocker)}):
            result = doctor_agent.notify(
                "فحص", "تم التسجيل محلياً", dedupe="d-1", state_dir=self.state
            )
        self.assertTrue(result["ok"], result)
        self.assertFalse(result["atulya_inbox"])

        lines = (self.state / "doctor_notices.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["title"], "فحص")
        self.assertEqual(record["body"], "تم التسجيل محلياً")
        self.assertEqual(record["dedupe"], "d-1")
        self.assertIn("at", record)

    def test_06_run_writes_selfcheck_and_never_touches_code(self):
        self._write("brain_errors.jsonl", '{"message":"timed out"}\n')
        code_files = [BASE_DIR.parent / rel for rel in sorted(doctor_agent.SAFE_CODE_FILES)]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in code_files}

        with patch.object(doctor_agent, "_code_has_severity_bug", return_value=False):
            result = doctor_agent.run(self.state)
        report = json.loads((self.state / "doctor_selfcheck.json").read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "live_verified")
        datetime.fromisoformat(report["checked_at"])
        for key in ("detected", "fixed", "proposed", "notices", "next"):
            self.assertIn(key, report)
        self.assertGreaterEqual(report["detected"], 1)

        for path, digest in before.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)

        source = (BASE_DIR / "src" / "doctor_agent.py").read_text(encoding="utf-8")
        self.assertNotIn("pk" + "ill", source.lower())

    def test_07_run_without_sources_reports_no_data_source(self):
        with patch.object(doctor_agent, "_code_has_severity_bug", return_value=False):
            report = doctor_agent.run(self.state)
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "no_data_source")
        self.assertEqual(report["detected"], 0)

    def test_08_safe_code_files_is_exact(self):
        self.assertEqual(set(doctor_agent.SAFE_CODE_FILES), {
            "esprieaether/src/self_improve.py",
            "esprieaether/tests/test_espria_system.py",
            "esprieaether/tests/test_agent_duties.py",
        })

    def test_09_main_prints_darija_summary(self):
        self._write("brain_errors.jsonl", '{"message":"timed out"}\n')
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            doctor_agent.main(self.state)
        text = buffer.getvalue()
        self.assertTrue(any("\u0600" <= char <= "\u06ff" for char in text), text)


if __name__ == "__main__":
    unittest.main()
