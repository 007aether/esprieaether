"""J76/C1 — actions proposées, décision explicite unique et journal local."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))


class ActionRequestTest(unittest.TestCase):
    def setUp(self):
        import action_request

        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.store = action_request.ActionRequests(
            root / "action_requests.json", root / "action_audit.jsonl"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_transition_and_terminal_receipt(self):
        proposed = self.store.propose("run", target="scan", reason="demande locale")
        self.assertEqual(proposed["status"], "proposed")
        approved = self.store.decide(proposed["id"], "approved_once", decided_by="hud")
        self.assertEqual(approved["status"], "approved_once")
        done = self.store.finish(proposed["id"], "executed", receipt="local-run-1")
        self.assertEqual(done["status"], "executed")
        audit = [json.loads(line) for line in
                 (Path(self.tmp.name) / "action_audit.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([a["to"] for a in audit],
                         ["proposed", "approved_once", "executed"])

    def test_invalid_transitions_are_refused(self):
        proposed = self.store.propose("connect", target="127.0.0.1:31416")
        with self.assertRaises(ValueError):
            self.store.finish(proposed["id"], "executed")
        self.store.decide(proposed["id"], "denied", decided_by="hud")
        with self.assertRaises(ValueError):
            self.store.decide(proposed["id"], "approved_once", decided_by="hud")
        with self.assertRaises(ValueError):
            self.store.finish(proposed["id"], "executed")

    def test_approved_once_is_single_use(self):
        proposed = self.store.propose("write", target="state/note.txt")
        self.store.decide(proposed["id"], "approved_once", decided_by="hud")
        self.store.finish(proposed["id"], "failed", receipt="erreur locale")
        with self.assertRaises(ValueError):
            self.store.decide(proposed["id"], "approved_once", decided_by="hud")

    def test_public_payload_is_redacted_and_has_no_secret_field(self):
        proposed = self.store.propose("run", target="api_key=abc123 password=xyz")
        payload = json.dumps(self.store.public(), ensure_ascii=False).lower()
        self.assertNotIn("abc123", payload)
        self.assertNotIn("xyz", payload)
        for word in ("api_key", "token", "password", "authorization"):
            self.assertNotIn(word, payload)
        self.assertIn("[redacted]", payload)

    def test_public_list_is_bounded_and_honest_when_empty(self):
        self.assertEqual(self.store.public(), [])
        for i in range(30):
            self.store.propose("scan", target=f"cible-{i}")
        self.assertLessEqual(len(self.store.public()), 20)

    def test_default_store_bootstraps_empty_local_state(self):
        import action_request

        root = Path(self.tmp.name)
        state = root / "state" / "action_requests.json"
        audit = root / "state" / "action_audit.jsonl"
        with mock.patch.object(action_request, "STATE_PATH", str(state)), \
             mock.patch.object(action_request, "AUDIT_PATH", str(audit)):
            store = action_request.default_store()
        self.assertEqual(json.loads(state.read_text(encoding="utf-8")), [])
        self.assertTrue(audit.exists())
        self.assertEqual(store.public(), [])


if __name__ == "__main__":
    unittest.main()
