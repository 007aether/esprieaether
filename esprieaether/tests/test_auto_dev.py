"""J152 — TDD : تطوير ذاتي بcommit/push تلقائي، محكوم بالاختبارات والمسارات."""

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import auto_dev  # noqa: E402


def proc(code=0, stdout=""):
    return types.SimpleNamespace(returncode=code, stdout=stdout, stderr="")


class AutoDevTest(unittest.TestCase):
    def test_protected_paths_block_every_commit(self) -> None:
        self.assertEqual(auto_dev.protected(["src/auto_dev.py"]), None)
        for path in (".env", "state/freellmapi.key", "touping.exe",
                     "esprieaether/state/secrets.enc", ".tools/git/cmd/git.exe"):
            self.assertIsNotNone(auto_dev.protected([path]), path)

    def test_no_changes_is_a_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            result = auto_dev.commit_and_push(
                Path(tmp), "git.exe", "J152: test", lambda *a, **k: calls.append(a) or proc(),
                status=[],
            )
            self.assertEqual(result["status"], "no_changes")
            self.assertEqual(calls, [])

    def test_red_tests_block_the_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                if "status" in cmd:
                    return proc(stdout="?? src/auto_dev.py\0")
                return proc(code=1, stdout="1 test failed")
            result = auto_dev.commit_and_push(
                Path(tmp), "git.exe", "J152: test", runner, status=["src/auto_dev.py"],
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["reason"], "tests_failed")
            self.assertFalse(any("commit" in cmd for cmd in calls))

    def test_green_tests_allow_commit_and_push(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            def runner(cmd, **kwargs):
                calls.append(cmd)
                return proc(stdout="ok")
            result = auto_dev.commit_and_push(
                Path(tmp), "git.exe", "J152: test", runner, status=["src/auto_dev.py"],
            )
            self.assertEqual(result["status"], "pushed")
            self.assertEqual(result["message"], "J152: test")
            git_calls = [cmd for cmd in calls if len(cmd) > 3 and cmd[1] == "-c"]
            verbs = [next(token for token in cmd[2:] if token in {"add", "commit", "push"})
                     for cmd in git_calls]
            self.assertEqual(verbs, ["add", "commit", "push"])

    def test_next_j_reads_git_subjects(self) -> None:
        runner = lambda cmd, **k: proc(stdout="J150: old\nJ151: newer\nrandom\n")
        self.assertEqual(auto_dev.next_j(Path("."), "git.exe", runner), 152)

    def test_autonomy_gate_disables_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state / "atulya").mkdir()
            (state / "atulya" / "autonomy.json").write_text(
                json.dumps({"auto_commit_push": False}), encoding="utf-8")
            result = auto_dev.maybe_commit_push(
                state_dir=state, root=Path(tmp), runner=lambda *a, **k: proc(), enabled=None,
            )
            self.assertEqual(result["status"], "disabled")

    def test_report_uses_only_allowed_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            report = auto_dev.write_report(state, {"status": "pushed"})
            self.assertEqual(json.loads((state / "auto_dev_state.json").read_text(encoding="utf-8")), report)
            self.assertIn(report["status"],
                          {"pushed", "failed", "blocked", "no_changes", "disabled"})


if __name__ == "__main__":
    unittest.main()
