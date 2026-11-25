"""J86: conversion locale offline pour alimenter l'Obsidian vault — zéro cloud."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
CONVERTER = ROOT / "esprieaether" / "scripts" / "local_converter.py"
VENDOR = ROOT / "GITHUB_IMPORT" / "Atulya-All-File-Converter"


def load_converter():
    spec = importlib.util.spec_from_file_location("esprie_local_converter", CONVERTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LocalConverterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_source_is_stdlib_only_and_never_mentions_update_or_cloud(self):
        source = CONVERTER.read_text(encoding="utf-8")
        imports = {m.group(1).split(".")[0] for m in re.finditer(
            r"^(?:import|from)\s+([A-Za-z_][\w.]*)", source, re.M)}
        self.assertTrue(imports <= {
            "__future__", "argparse", "json", "os", "subprocess",
            "sys", "tempfile", "pathlib",
        }, imports)
        for forbidden in ("urllib", "requests", "httpx", "webbrowser", "update",
                          "cloud", "api.github.com", "s3", "token"):
            self.assertNotIn(forbidden, source.lower())

    def test_uses_vendored_venv_without_update_command(self):
        mod = load_converter()
        source = self.dir / "in.csv"
        target = self.dir / "out.json"
        source.write_text("a,b\n1,2\n", encoding="utf-8")
        done = subprocess.CompletedProcess([], 0, "ok", "")
        with mock.patch.object(mod.subprocess, "run", return_value=done) as run:
            result = mod.convert_file(str(source), str(target))
        self.assertTrue(result["ok"])
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[0], str(mod.PYTHON))
        self.assertEqual(cmd[1:4], ["-m", "atulya_all_file_converter", "convert"])
        self.assertIn("-i", cmd)
        self.assertIn(str(source), cmd)
        self.assertIn("-o", cmd)
        self.assertIn(str(target), cmd)
        self.assertNotIn("update", cmd)
        self.assertEqual(run.call_args.kwargs["cwd"], str(VENDOR))
        self.assertLessEqual(run.call_args.kwargs["timeout"], 120)

    @unittest.skipUnless(VENDOR.exists(), "convertisseur local absent")
    def test_rejects_paths_outside_local_roots_and_missing_source(self):
        mod = load_converter()
        source = self.dir / "in.csv"
        source.write_text("a,b\n1,2\n", encoding="utf-8")
        outside = Path("C:/hors-racine-local.txt")
        result = mod.convert_file(str(source), str(outside))
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "PATH_REFUSED")
        result = mod.convert_file(str(self.dir / "absent.csv"), str(self.dir / "out.json"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "SOURCE_MISSING")

    @unittest.skipUnless(VENDOR.exists(), "convertisseur local absent")
    def test_real_csv_to_json_is_local_and_honest(self):
        mod = load_converter()
        self.assertTrue(mod.available())
        source = self.dir / "in.csv"
        target = self.dir / "out.json"
        source.write_text("name,age\nada,36\n", encoding="utf-8")
        result = mod.convert_file(str(source), str(target))
        self.assertTrue(result["ok"], result)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))[0]["name"], "ada")


if __name__ == "__main__":
    unittest.main()
