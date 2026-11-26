"""TDD J114 — agent d'apprentissage 100 % local, sans secret et sous policy_gate."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import learning_agent  # noqa: E402


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class LearningAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "state"
        self.state.mkdir()
        self.now = _now()

    def tearDown(self):
        self.tmp.cleanup()

    def _seed(self):
        (self.state / "run_ledger.json").write_text(json.dumps({
            "generatedAt": self.now,
            "available": True,
            "stats": {"total": 3, "succeeded": 2, "failed": 1},
            "runs": [
                {"id": 1, "action": "scan", "actor": "user", "status": "succeeded",
                 "createdAt": self.now},
                {"id": 2, "action": "run_robot", "actor": "user", "status": "failed",
                 "createdAt": self.now, "detail": "token=SUPERSECRETKEY"},
            ],
        }), encoding="utf-8")
        (self.state / "action_audit.jsonl").write_text("\n".join([
            json.dumps({"at": self.now, "id": "act-1", "from": "proposed",
                        "to": "approved_once", "actor": "hud"}),
            json.dumps({"at": self.now, "id": "act-2", "from": "proposed",
                        "to": "denied", "actor": "hud",
                        "detail": "api_key=ANOTHERSECRET"}),
        ]) + "\n", encoding="utf-8")
        (self.state / "voice_inbox.jsonl").write_text("\n".join([
            json.dumps({"ts": self.now, "reason": "barge_in", "ok": False}),
            json.dumps({"ts": self.now, "ok": True, "spoken": True,
                        "engine": "local-brain", "language": "ar-MA"}),
        ]) + "\n", encoding="utf-8")
        (self.state / "brain_errors.jsonl").write_text(json.dumps({
            "ts": self.now, "source": "router", "error": "timeout local",
        }) + "\n", encoding="utf-8")
        (self.state / "action_requests.json").write_text(json.dumps([
            {"id": "act-3", "action": "backup", "status": "executed",
             "reason": "password=HUNTER2SECRET"},
        ]), encoding="utf-8")

    def test_learn_reads_local_state_and_redacts_every_secret(self):
        self._seed()
        report = learning_agent.learn(self.state)
        self.assertTrue(report["ok"])
        self.assertEqual(report["engine"], "local_only")
        self.assertGreaterEqual(report["learnedCount"], 4)
        self.assertTrue(report["lessons"])
        self.assertIn("run_ledger.json", report["sources"])
        self.assertIn("action_audit.jsonl", report["sources"])
        payload = json.dumps(report, ensure_ascii=False)
        for secret in ("SUPERSECRETKEY", "ANOTHERSECRET", "HUNTER2SECRET"):
            self.assertNotIn(secret, payload)
        self.assertIn("<redacted>", payload)

    def test_empty_sources_are_honest_and_never_live_verified(self):
        report = learning_agent.learn(self.state)
        self.assertFalse(report["ok"])
        self.assertEqual(report["status"], "no_data_source")
        self.assertEqual(report["learnedCount"], 0)
        self.assertFalse(report["lessons"])

    def test_policy_gate_blocks_secrets_and_external_hosts(self):
        self.assertTrue(learning_agent.allowed(action="learn", path="state/notes.md")["allowed"])
        self.assertFalse(learning_agent.allowed(action="learn", path=".env")["allowed"])
        self.assertFalse(learning_agent.allowed(action="learn", host="example.com",
                                                internet=False)["allowed"])
        self.assertFalse(learning_agent.allowed(action="execute", internet=False)["allowed"])

    def test_no_network_capability_in_source(self):
        source = (BASE_DIR / "src" / "learning_agent.py").read_text(encoding="utf-8")
        for forbidden in ("import socket", "import requests", "urllib.request",
                          "http.client", "httpx", "aiohttp"):
            self.assertNotIn(forbidden, source)

    def test_vault_preference_is_local_and_ignores_hidden_notes(self):
        self._seed()
        vault = Path(self.tmp.name) / "vault"
        vault.mkdir()
        (vault / "preferences.md").write_text(
            "# Préférences\nL'utilisateur préfère les réponses courtes en darija.\n",
            encoding="utf-8")
        hidden = vault / ".obsidian"
        hidden.mkdir()
        (hidden / "private.md").write_text(
            "SECRETVAULT mot de passe violet", encoding="utf-8")
        report = learning_agent.learn(self.state, vault_dir=vault)
        self.assertEqual(report["topNote"], "preferences.md")
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("SECRETVAULT", payload)

    def test_memory_file_is_bounded_and_redacted(self):
        for index in range(learning_agent.MAX_LESSONS + 12):
            (self.state / "brain_errors.jsonl").write_text(json.dumps({
                "ts": self.now, "error": f"panic-{index}", "token": f"SECRET-{index}",
            }) + "\n", encoding="utf-8")
            learning_agent.learn(self.state)
        lines = (self.state / "learning_memory.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len(lines), learning_agent.MAX_LESSONS)
        self.assertNotIn("SECRET-", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
