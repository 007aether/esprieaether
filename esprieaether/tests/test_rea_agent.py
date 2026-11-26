""" REA المحلي: قراءة مرجعية آمنة، أدلة من الكود، blueprint، وتشغيل بلا تبديل. """

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
BASE_DIR = TESTS_DIR.parents[1]
sys.path.insert(0, str(BASE_DIR / "esprieaether" / "src"))

import rea_agent  # noqa: E402


class ReaAgentTest(unittest.TestCase):
    def test_load_reference_reads_skill_file(self) -> None:
        text = rea_agent.load_reference("safe-changes")
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 20)
        self.assertLessEqual(len(text), 20000)
        self.assertIn("Change an existing reconstruction", text)

    def test_load_reference_rejects_traversal_and_missing_files(self) -> None:
        for bad in ("../../.env", "../.env", "sub/../../.env", "..\\.env",
                    "/etc/passwd", "foo/bar", "", "does-not-exist"):
            with self.subTest(name=bad):
                self.assertEqual("", rea_agent.load_reference(bad))

    def test_analyze_collects_py_mjs_evidence_and_skips_excluded_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text(
                "def main():\n"
                "    # TODO: ربط الطلبات\n"
                "    try:\n"
                "        pass\n"
                "    except ValueError:\n"
                "        pass\n",
                encoding="utf-8",
            )
            (root / "server.mjs").write_text(
                "const app = {};\n"
                "app.post('/x', () => {});\n"
                "app.get('/y', () => {});\n"
                "// FIXME: تحديد المعدل\n"
                "const server = createServer(handler);\n"
                "try { server.listen(); } catch (error) {}\n",
                encoding="utf-8",
            )
            for excluded in (".venv", "node_modules", ".git", "__pycache__", "state"):
                folder = root / excluded
                folder.mkdir()
                (folder / "decoy.py").write_text(
                    "def main():\n# TODO decoy\ndef createServer(): pass\n",
                    encoding="utf-8",
                )
            (root / "notes.txt").write_text("def main() TODO decoy", encoding="utf-8")

            report = rea_agent.analyze(root)

            self.assertTrue(report["ok"])
            self.assertEqual(2, report["files"])
            self.assertEqual({".py": 1, ".mjs": 1}, report["by_ext"])
            datetime.fromisoformat(report["checked_at"])

            entrypoints = [str(item) for item in report["entrypoints"]]
            self.assertTrue(any("main" in item for item in entrypoints))
            self.assertTrue(any("post" in item for item in entrypoints))
            self.assertTrue(any("get" in item for item in entrypoints))
            self.assertTrue(any("createServer" in item for item in entrypoints))

            todos = [str(item) for item in report["todos"]]
            self.assertTrue(any("TODO" in item for item in todos))
            self.assertTrue(any("FIXME" in item for item in todos))

            self.assertTrue(
                any(item.get("field") == "error_pattern" for item in report["evidence"])
            )
            self.assertFalse(any("decoy" in item for item in entrypoints + todos))
            self.assertLessEqual(len(report["longest"]), 5)
            self.assertEqual(
                {"app.py", "server.mjs"}, {item["source"] for item in report["longest"]}
            )
            self.assertGreaterEqual(
                report["longest"][0]["lines"], report["longest"][-1]["lines"]
            )

            for item in report["evidence"]:
                self.assertEqual({"source", "field", "value"}, set(item))
                self.assertLessEqual(len(item["value"]), 200)
                self.assertNotIn(str(root), item["source"])
                self.assertNotIn(str(root), item["value"])

    def test_blueprint_has_no_absolute_paths_or_secrets(self) -> None:
        report = {
            "ok": True,
            "files": 3,
            "entrypoints": ["app.py:1: def main()"],
            "todos": ["app.py:2: TODO"],
            "evidence": [
                {
                    "source": "C:\\Users\\aether\\secret\\app.py",
                    "field": "note",
                    "value": "C:\\Users\\aether\\secret\\app.py password=hunter2 token=abc secret=xyz",
                },
                {
                    "source": "/home/aether/.env",
                    "field": "error_pattern",
                    "value": "token = sk-123 at /home/aether/.env",
                },
            ],
        }
        markdown = rea_agent.blueprint(report)

        self.assertIn("الملخص", markdown)
        self.assertIn("الأدلة", markdown)
        self.assertIn("شنو ناقص", markdown)
        self.assertLessEqual(len(markdown), 4000)
        lowered = markdown.casefold()
        for word in ("password", "token", "secret"):
            self.assertNotIn(word, lowered)
        for path_part in ("C:\\Users", "C:/Users", "/home/aether", "aether\\secret"):
            self.assertNotIn(path_part, markdown)

    def test_run_writes_blueprint_and_selfcheck_without_touching_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()
            (target / "app.py").write_text("def main():\n # TODO: test\n", encoding="utf-8")
            (target / "server.mjs").write_text("app.post('/x', handler);\n", encoding="utf-8")
            before = {
                path.relative_to(target).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in target.rglob("*") if path.is_file()
            }
            state_dir = root / "state"
            blueprint_dir = root / "docs" / "rea" / "esprieaether"

            with patch.object(rea_agent, "BLUEPRINT_DIR", blueprint_dir):
                result = rea_agent.run(state_dir=state_dir, target_dir=target)

            blueprint_path = blueprint_dir / "blueprint.md"
            self.assertTrue(blueprint_path.is_file())
            self.assertIn("شنو ناقص", blueprint_path.read_text(encoding="utf-8"))
            self.assertEqual([], list(blueprint_dir.glob("*.tmp")))

            selfcheck_path = state_dir / "rea_selfcheck.json"
            self.assertTrue(selfcheck_path.is_file())
            state = json.loads(selfcheck_path.read_text(encoding="utf-8"))
            self.assertEqual(state, result)
            self.assertTrue(state["ok"])
            self.assertEqual("live_verified", state["status"])
            datetime.fromisoformat(state["checked_at"])
            self.assertEqual(2, state["files"])
            self.assertTrue(state["entrypoints"])
            self.assertTrue(state["blueprintPath"].endswith("blueprint.md"))
            self.assertTrue(state["next"])

            after = {
                path.relative_to(target).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in target.rglob("*") if path.is_file()
            }
            self.assertEqual(before, after)

    def test_run_reports_no_data_source_for_empty_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "empty"
            target.mkdir()
            with patch.object(rea_agent, "BLUEPRINT_DIR", root / "docs" / "rea" / "esprieaether"):
                result = rea_agent.run(state_dir=root / "state", target_dir=target)

            self.assertTrue(result["ok"])
            self.assertEqual("no_data_source", result["status"])
            self.assertEqual(0, result["files"])


if __name__ == "__main__":
    unittest.main()
