"""J52/J53 — autorité locale complète + journal d'exécution terminal.

TDD: ces tests sont écrits avant les modules src/policy_gate.py et src/run_store.py.
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))


class PolicyGateTest(unittest.TestCase):
    def test_full_local_authority_is_the_granted_default(self):
        from policy_gate import AuthorityMode, Decision, decide

        d = decide("inspect", mode=AuthorityMode.FULL_LOCAL)
        self.assertIsInstance(d, Decision)
        self.assertTrue(d.allowed)
        self.assertEqual(d.mode, "full_local")

    def test_read_only_mode_refuses_effectful_actions(self):
        from policy_gate import AuthorityMode, decide

        self.assertFalse(decide("write", mode=AuthorityMode.READ_ONLY).allowed)
        self.assertTrue(decide("inspect", mode=AuthorityMode.READ_ONLY).allowed)

    def test_unknown_action_is_denied_even_with_full_authority(self):
        from policy_gate import AuthorityMode, decide

        d = decide("drop_all_databases", mode=AuthorityMode.FULL_LOCAL)
        self.assertFalse(d.allowed)
        self.assertIn("not_allowlisted", d.reason)

    def test_secret_paths_are_always_refused(self):
        from policy_gate import AuthorityMode, decide

        for name in (".env", ".env.bot1", "id_rsa", "server.pem", "vault.key",
                     ".credentials.yaml", "cert.pfx", "key.p12"):
            with self.subTest(name=name):
                d = decide("read", path=f"C:\\Users\\aether\\{name}",
                           mode=AuthorityMode.FULL_LOCAL)
                self.assertFalse(d.allowed, name)
                self.assertEqual(d.reason, "protected_path")

    def test_project_path_is_allowed(self):
        from policy_gate import AuthorityMode, decide

        d = decide("write", path=str(BASE_DIR / "state" / "run_ledger.db"),
                   mode=AuthorityMode.FULL_LOCAL)
        self.assertTrue(d.allowed)
        self.assertEqual(d.reason, "allowlisted")

    def test_check_url_blocks_private_lan_and_unsupported_schemes(self):
        from policy_gate import check_url

        self.assertTrue(check_url("https://hnrss.org/frontpage").allowed)
        denied = check_url("http://192.168.0.113:3000/")
        self.assertFalse(denied.allowed)
        self.assertEqual(denied.reason, "private_network")
        bad = check_url("ftp://pypi.org/file")
        self.assertFalse(bad.allowed)
        self.assertEqual(bad.reason, "unsupported_scheme")

    def test_voice_chain_actions_are_allowlisted(self):
        from policy_gate import AuthorityMode, decide

        for action in ("listen", "brain_reply", "voice_turn"):
            with self.subTest(action=action):
                d = decide(action, mode=AuthorityMode.FULL_LOCAL)
                self.assertTrue(d.allowed)
                self.assertEqual(d.reason, "allowlisted")

    def test_loopback_private_network_and_internet_opt_in(self):
        from policy_gate import AuthorityMode, decide

        # Loopback : toujours autorisé.
        self.assertTrue(decide("connect", host="127.0.0.1:31416").allowed)
        self.assertTrue(decide("connect", host="localhost").allowed)

        # Réseau privé / LAN : refusé même avec l'autorité Internet (SSRF).
        for host in ("192.168.1.10", "10.0.0.5", "172.16.4.2",
                     "169.254.169.254", "127.0.0.1.evil.com"):
            with self.subTest(host=host):
                d = decide("connect", host=host, internet=True)
                self.assertFalse(d.allowed)
                self.assertEqual(d.reason, "private_network")

        # Internet public : autorisé quand l'utilisateur l'a accordé.
        for host in ("pypi.org", "8.8.8.8", "huggingface.co"):
            with self.subTest(host=host):
                d = decide("connect", host=host, internet=True)
                self.assertTrue(d.allowed)
                self.assertEqual(d.reason, "internet_allowed")

        # Sans l'opt-in, on reste en local strict.
        d = decide("connect", host="pypi.org", internet=False)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "external_network")

    def test_taint_is_recorded_and_marks_confirmation_without_blocking_reads(self):
        from policy_gate import AuthorityMode, decide

        read = decide("inspect", tainted=True, mode=AuthorityMode.FULL_LOCAL)
        self.assertTrue(read.allowed)
        self.assertTrue(read.tainted)
        self.assertFalse(read.requires_confirmation)

        act = decide("write", tainted=True, mode=AuthorityMode.FULL_LOCAL)
        self.assertTrue(act.allowed)
        self.assertTrue(act.requires_confirmation)

    def test_decision_serializes_without_secrets(self):
        import json

        from policy_gate import AuthorityMode, decide

        d = decide("inspect", mode=AuthorityMode.FULL_LOCAL)
        payload = json.dumps(d.to_dict())
        self.assertNotIn(".env", payload)
        self.assertIn("full_local", payload)


class RobotAuthorityIntegrationTest(unittest.TestCase):
    def test_run_robot_records_a_terminal_run_and_exports_public_json(self):
        import robot_engine
        from run_store import RunStore

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            db = tmpdir / "robots.db"
            ledger = tmpdir / "state" / "run_ledger.db"
            export = tmpdir / "state" / "run_ledger.json"
            with patch.object(robot_engine, "DB", str(db)):
                robot_engine.init_engine_db()
                conn = sqlite3.connect(str(db))
                conn.execute(
                    "INSERT INTO robots (id,name,role,status) VALUES (?,?,?,?)",
                    ("TEST_01", "TEST ROBOT", "inspect", "active"),
                )
                conn.commit()
                conn.close()
                fake = {"inspect": lambda rid: {"ok": True, "summary": "hello"}}
                with patch.dict(robot_engine.ROLE_HANDLERS, fake):
                    robot_engine.configure_authority(ledger, export_path=export)
                    result = robot_engine.RobotEngine().run_robot("TEST_01")
            self.assertEqual(result["status"], "ok")
            store = RunStore(ledger)
            runs = store.list_runs()
            self.assertEqual(len(runs), 1)
            self.assertIn(runs[0]["status"], ("succeeded", "failed", "timed_out", "cancelled"))
            self.assertEqual(runs[0]["action"], "inspect")
            payload = json.loads(export.read_text(encoding="utf-8"))
            self.assertTrue(payload["available"])
            self.assertEqual(payload["stats"]["total"], 1)
            self.assertNotIn("hello", json.dumps(payload["runs"]))

    def test_noop_robot_role_is_not_regressed_by_full_authority(self):
        """Les rôles historiques sans handler (tool_builder, api_proxy…) restent exécutables."""
        import robot_engine
        from run_store import RunStore

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            db = tmpdir / "robots.db"
            ledger = tmpdir / "ledger.db"
            with patch.object(robot_engine, "DB", str(db)):
                robot_engine.init_engine_db()
                conn = sqlite3.connect(str(db))
                conn.execute(
                    "INSERT INTO robots (id,name,role,status) VALUES (?,?,?,?)",
                    ("TEST_03", "NOOP", "tool_builder", "active"),
                )
                conn.commit()
                conn.close()
                robot_engine.configure_authority(ledger, export_path=tmpdir / "ledger.json")
                result = robot_engine.RobotEngine().run_robot("TEST_03")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(RunStore(ledger).list_runs()[0]["status"], "succeeded")
            self.assertNotIn("authority_denied", result["summary"])

    def test_denied_role_is_not_executed(self):
        import robot_engine
        from run_store import RunStore

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            db = tmpdir / "robots.db"
            ledger = tmpdir / "ledger.db"
            called = []
            with patch.object(robot_engine, "DB", str(db)):
                robot_engine.init_engine_db()
                conn = sqlite3.connect(str(db))
                conn.execute(
                    "INSERT INTO robots (id,name,role,status) VALUES (?,?,?,?)",
                    ("TEST_02", "DENIED", "forbidden_action", "active"),
                )
                conn.commit()
                conn.close()
                with patch.dict(robot_engine.ROLE_HANDLERS,
                                {"forbidden_action": lambda rid: called.append(rid)}):
                    with patch.object(robot_engine, "_authority_decide",
                                      side_effect=lambda role, mode: _Denied()):
                        robot_engine.configure_authority(
                            ledger, export_path=tmpdir / "state" / "run_ledger.json"
                        )
                        result = robot_engine.RobotEngine().run_robot("TEST_02")
            self.assertEqual(result["status"], "error")
            self.assertEqual(called, [])
            self.assertEqual(RunStore(ledger).list_runs()[0]["status"], "failed")


class _Denied:
    allowed = False
    reason = "not_allowlisted"
    tainted = False


class RunStoreTest(unittest.TestCase):
    def setUp(self):
        from run_store import RunStore

        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "state" / "run_ledger.db"
        self.store = RunStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_parent_directory_and_schema(self):
        self.assertTrue(self.db.exists())
        conn = sqlite3.connect(str(self.db))
        cols = {r[1] for r in conn.execute("PRAGMA table_info(runs)").fetchall()}
        conn.close()
        self.assertTrue({"id", "action", "actor", "status", "detail"}.issubset(cols))

    def test_record_returns_id_and_list_is_newest_first(self):
        first = self.store.record("inspect", actor="SYS_02", status="succeeded", detail="a")
        second = self.store.record("write", actor="SYS_01", status="succeeded", detail="b")
        rows = self.store.list_runs()
        self.assertEqual(rows[0]["id"], second)
        self.assertEqual(rows[1]["id"], first)
        self.assertEqual(rows[0]["action"], "write")

    def test_status_enum_is_closed(self):
        from run_store import TERMINAL_STATUSES

        self.assertEqual(
            set(TERMINAL_STATUSES),
            {"succeeded", "failed", "timed_out", "cancelled"},
        )
        with self.assertRaises(ValueError):
            self.store.record("x", actor="y", status="done")

    def test_reap_stale_marks_running_as_timed_out(self):
        run_id = self.store.record("scan", actor="SYS_04", status="running")
        self.assertEqual(self.store.get(run_id)["status"], "running")
        changed = self.store.reap_stale(timeout_seconds=0)
        self.assertGreaterEqual(changed, 1)
        self.assertEqual(self.store.get(run_id)["status"], "timed_out")

    def test_detail_is_redacted(self):
        run_id = self.store.record(
            "connect",
            actor="SYS_01",
            status="succeeded",
            detail="api_key=supersecret token=abc password=hunter2 host=127.0.0.1",
        )
        detail = self.store.get(run_id)["detail"]
        self.assertNotIn("supersecret", detail)
        self.assertNotIn("hunter2", detail)
        self.assertIn("127.0.0.1", detail)

    def test_stats_counts_terminal_states(self):
        self.store.record("a", actor="x", status="succeeded")
        self.store.record("b", actor="x", status="failed")
        self.store.record("c", actor="x", status="cancelled")
        stats = self.store.stats()
        self.assertEqual(stats["succeeded"], 1)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["cancelled"], 1)


if __name__ == "__main__":
    unittest.main()
