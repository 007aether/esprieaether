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

    def test_learn_retient_les_comptages_reels_de_la_veille(self) -> None:
        """Le rapport réel stocke topics/languages comme dicts de comptages."""
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state / "github_scout_report.json").write_text(json.dumps({
                "ok": True,
                "status": "live_verified",
                "scanned": 1000,
                "topics": {"agent": 169, "ai": 338, "llm": 240,
                           "ai-agents": 231, "mcp": 115},
                "languages": {"Python": 463, "Go": 46, "TypeScript": 149},
            }), encoding="utf-8")
            report = learning_agent.learn(state_dir=state, vault_dir=None)
            details = " ".join(str(row["detail"]) for row in report["lessons"])
            self.assertIn("topic=ai:338", details)
            self.assertIn("topic=llm:240", details)
            self.assertIn("language=Python:463", details)
            self.assertNotIn("topic=agent:169", details)  # seulement le top 3
            memory = (state / "learning_memory.jsonl").read_text(encoding="utf-8")
            self.assertIn("topic=ai:338", memory)
            self.assertNotIn("token=", memory.lower())

    def test_learn_inclut_la_fenetre_github_7_jours(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state / "github_week_report.json").write_text(json.dumps({
                "checkedAt": "2026-11-26T05:55:20Z",
                "since": "2026-11-19",
                "target": "https://api.github.com",
                "queries": ["ai agent"],
                "items": [
                    {"name": "owner/old", "createdAt": "2026-11-20T00:00:00Z"},
                    {"name": "owner/new", "createdAt": "2026-11-26T05:50:12Z"},
                ],
                "errors": [],
                "latestCreated": {"name": "owner/new", "createdAt": "2026-11-26T05:50:12Z"},
                "latestPushed": {"name": "owner/push", "pushedAt": "2026-11-26T05:55:27Z"},
                "digest": "abc123",
            }), encoding="utf-8")
            report = learning_agent.learn(state_dir=state, vault_dir=None)
            self.assertTrue(report["ok"])
            self.assertIn("github_week_report.json", report["sources"])
            details = " ".join(str(row["detail"]) for row in report["lessons"])
            self.assertIn("fenêtre depuis=2026-11-19", details)
            self.assertIn("owner/new", details)
            self.assertIn("owner/push", details)
            memory = (state / "learning_memory.jsonl").read_text(encoding="utf-8")
            self.assertIn("github_week_report.json", memory)
            self.assertNotIn("token=", memory.lower())

    def test_fenetre_avec_erreurs_najoute_pas_de_lecon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state / "github_week_report.json").write_text(json.dumps({
                "since": "2026-11-19", "items": [{"name": "owner/repo"}],
                "errors": ["boom"], "digest": "abc123",
            }), encoding="utf-8")
            report = learning_agent.learn(state_dir=state, vault_dir=None)
            self.assertNotIn("github_week_report.json", report["sources"])

    def test_veille_vide_najoute_pas_de_lecon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            (state / "github_scout_report.json").write_text(json.dumps({
                "ok": False, "status": "no_data_source", "scanned": 0,
                "topics": [], "languages": [],
            }), encoding="utf-8")
            report = learning_agent.learn(state_dir=state, vault_dir=None)
            self.assertNotIn("github_scout_report.json", report["sources"])
