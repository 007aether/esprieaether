"""J122 — TDD : le agent d'apprentissage retient aussi la veille GitHub."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import learning_agent  # noqa: E402


class LearningScoutTest(unittest.TestCase):
    def test_learn_include_les_sujets_de_la_veille_github(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state / "github_scout_report.json").write_text(json.dumps({
                "ok": True,
                "status": "live_verified",
                "scanned": 1000,
                "topics": ["local llm", "voice assistant"],
                "languages": ["Python", "TypeScript"],
                "sample": [{"name": "owner/repo"}],
            }), encoding="utf-8")
            report = learning_agent.learn(state_dir=state, vault_dir=None)
            self.assertTrue(report["ok"])
            self.assertIn("github_scout_report.json", report["sources"])
            details = " ".join(str(row["detail"]) for row in report["lessons"])
            self.assertIn("local llm", details)
            memory = (state / "learning_memory.jsonl").read_text(encoding="utf-8")
            self.assertIn("github_scout_report.json", memory)
            self.assertNotIn("token=", memory.lower())

    def test_veille_vide_najoute_pas_de_lecon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state / "github_scout_report.json").write_text(json.dumps({
                "ok": False, "status": "no_data_source", "scanned": 0,
                "topics": [], "languages": [],
            }), encoding="utf-8")
            report = learning_agent.learn(state_dir=state, vault_dir=None)
            self.assertNotIn("github_scout_report.json", report["sources"])
