"""Les 3 nouveaux robots : gardien qualité, gardien Obsidian, éclaireur de backlog."""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "robots"))

import robot_engine  # noqa: E402


GOOD_JARVIS = (
    "# jarvis\n\nPort **5000** - http://localhost:5000/\n\n"
    "Statut : ✅ Vérifié\n- [[local-brain]]\n- [[router]]\n"
)

GOOD_GRAPH = (
    "<script>/* vis local */</script>\n"
    'const nodes=new vis.DataSet([{"id": "jarvis"}, {"id": "local-brain"}, '
    '{"id": "dolphin3"}]);\n'
    'const edges=new vis.DataSet([{"from": "jarvis", "to": "local-brain"}, '
    '{"from": "dolphin3", "to": "local-brain"}]);\n'
)


class RobotGuardiansTest(unittest.TestCase):
    def test_three_guardians_seeded_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "robots.db"
            with patch.object(robot_engine, "DB", str(db)):
                robot_engine.init_engine_db()
                robot_engine.init_engine_db()  # idempotent
                conn = sqlite3.connect(db)
                rows = conn.execute(
                    "SELECT id,name,role,status FROM robots WHERE id IN "
                    "('SYS_02','SYS_03','SYS_04') ORDER BY id"
                ).fetchall()
                conn.close()
        self.assertEqual(rows, [
            ("SYS_02", "QUALITY_GUARDIAN", "quality_guard", "active"),
            ("SYS_03", "VAULT_GUARDIAN", "vault_guard", "active"),
            ("SYS_04", "BACKLOG_SCOUT", "backlog_scout", "active"),
        ])

    def test_git_status_uses_bundled_git_without_global_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_git = Path(tmp) / "git.exe"
            fake_git.touch()
            done = SimpleNamespace(returncode=0, stdout="", stderr="")
            with patch.object(robot_engine, "GIT_EXE", fake_git), \
                 patch.object(robot_engine.shutil, "which", return_value=None), \
                 patch.object(robot_engine.subprocess, "run", return_value=done) as run:
                result = robot_engine.h_git_status("EXT_09")
        self.assertTrue(result["ok"])
        self.assertEqual(run.call_args.args[0][0], str(fake_git))

    def test_activate_all_enables_every_robot_and_deactivate_all_restores(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "robots.db"
            with patch.object(robot_engine, "DB", str(db)):
                robot_engine.init_engine_db()
                conn = sqlite3.connect(db)
                conn.execute(
                    "INSERT INTO robots (id,name,system,role,status) VALUES (?,?,?,?,?)",
                    ("EXT_02", "CRYPTO_TRADER", "financial", "trading", "idle"),
                )
                conn.commit()
                conn.close()
                engine = robot_engine.RobotEngine()
                engine.activate_all()
                conn = sqlite3.connect(db)
                on = dict(conn.execute("SELECT status, COUNT(*) FROM robots GROUP BY status").fetchall())
                conn.close()
                self.assertEqual(on, {"active": 6})
                engine.deactivate_all()
                conn = sqlite3.connect(db)
                off = dict(conn.execute("SELECT status, COUNT(*) FROM robots GROUP BY status").fetchall())
                conn.close()
                self.assertEqual(off, {"idle": 6})

    def test_roles_point_to_real_handlers(self):
        for role, name in (
            ("quality_guard", "h_quality_guard"),
            ("vault_guard", "h_vault_guard"),
            ("backlog_scout", "h_backlog_scout"),
        ):
            handler = robot_engine.ROLE_HANDLERS[role]
            self.assertIs(handler, getattr(robot_engine, name))
            self.assertIsNot(handler, robot_engine.h_noop)

    def test_env_hash_guard_detects_change(self):
        self.assertEqual(
            robot_engine.ENV_SHA256,
            "DE9449DD1DB4F3A7EAE2C78B887E280981503D4D0B76BFF70105D5CA9FE27A7E",
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "env"
            p.write_bytes(b"a=1\n")
            digest = robot_engine._sha256(p)
            self.assertEqual(len(digest), 64)
            self.assertEqual(digest, digest.upper())
            p.write_bytes(b"a=2\n")
            self.assertNotEqual(robot_engine._sha256(p), digest)

    def test_parsers_read_real_test_summaries(self):
        ran, ok = robot_engine._parse_python_tests("...\nRan 44 tests in 2.1s\n\nOK\n")
        self.assertEqual((ran, ok), (44, True))
        ran, ok = robot_engine._parse_python_tests("Ran 44 tests\nFAILED (failures=1)\n")
        self.assertEqual((ran, ok), (44, False))
        passed, failed = robot_engine._parse_node_tests("tests 3\npass 3\nfail 0\n")
        self.assertEqual((passed, failed), (3, 0))
        passed, failed = robot_engine._parse_node_tests("tests 3\npass 2\nfail 1\n")
        self.assertEqual((passed, failed), (2, 1))

    def test_vault_checks_detect_good_and_regressed_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "Services").mkdir()
            (vault / "Services" / "jarvis.md").write_text(GOOD_JARVIS, encoding="utf-8")
            (vault / "graph.html").write_text(GOOD_GRAPH, encoding="utf-8")
            good = robot_engine._vault_checks(vault)
            self.assertTrue(good["ok"], good)
            self.assertEqual((good["nodes"], good["edges"]), (3, 2))

            (vault / "Services" / "jarvis.md").write_text(
                "Port **8000** - Non vérifié", encoding="utf-8"
            )
            (vault / "graph.html").write_text(
                '<script src="https://cdn.example.com/vis.js"></script>\n'
                'const nodes=new vis.DataSet([{"id": "jarvis"}]);\n'
                'const edges=new vis.DataSet([]);\n',
                encoding="utf-8",
            )
            bad = robot_engine._vault_checks(vault)
            self.assertFalse(bad["ok"])
            self.assertFalse(bad["jarvis_port_5000"])
            self.assertFalse(bad["jarvis_verified"])
            self.assertFalse(bad["jarvis_links_brain"])
            self.assertFalse(bad["graph_jarvis_brain_edge"])
            self.assertFalse(bad["graph_no_cdn"])

    def test_backlog_scout_lists_only_open_items(self):
        text = "\n".join([
            "| O1 | Périmètre | **Fermés** |",
            "| O5 | Prix 50/200 | Ouvert — non interprétable |",
            "| O11 | Push GitHub | Ouvert — clé absente |",
            "| O13 | Four Amine | Ouvert — sens non tranché |",
            "| O20 | Chat | **Contourné** — via API |",
        ])
        self.assertEqual(
            [r["id"] for r in robot_engine._parse_backlog(text)],
            ["O5", "O11", "O13"],
        )

    def test_backlog_handler_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            pmap = tmpdir / "PROJECT_MAP.md"
            pmap.write_text("| O5 | x | Ouvert |", encoding="utf-8")
            with patch.object(robot_engine, "PROJECT_MAP", pmap), \
                 patch.object(robot_engine, "REPORT_DIR", tmpdir):
                result = robot_engine.h_backlog_scout("SYS_04")
            self.assertTrue(result["ok"])
            self.assertIn("open=1", result["summary"])
            report = json.loads((tmpdir / "backlog_scout_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["items"][0]["id"], "O5")

    def test_backlog_scout_ignores_templates_as_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "PROJECT_MAP.md").write_text("| O5 | x | Ouvert |", encoding="utf-8")
            sources = root / "data" / "sources"
            for name, template in (("legal", "_modele.md"), ("fiscal", "README.md"),
                                   ("travail", ".gitkeep")):
                (sources / name).mkdir(parents=True)
                (sources / name / template).write_text("à remplir", encoding="utf-8")
            with patch.object(robot_engine, "BASE_DIR", root), \
                 patch.object(robot_engine, "PROJECT_MAP", root / "PROJECT_MAP.md"), \
                 patch.object(robot_engine, "REPORT_DIR", root):
                result = robot_engine.h_backlog_scout("SYS_04")
            self.assertIn("no_data_source=legal,fiscal,travail", result["summary"])
            (sources / "travail" / "bareme.txt").write_text("TVA 20%", encoding="utf-8")
            with patch.object(robot_engine, "BASE_DIR", root), \
                 patch.object(robot_engine, "PROJECT_MAP", root / "PROJECT_MAP.md"), \
                 patch.object(robot_engine, "REPORT_DIR", root):
                result = robot_engine.h_backlog_scout("SYS_04")
            self.assertIn("no_data_source=legal,fiscal", result["summary"])

    def test_quality_guard_aggregates_all_checks(self):
        def fake_cmd(cmd, cwd, timeout):
            if "unittest" in cmd:
                return 0, "Ran 44 tests\n\nOK\n"
            return 0, "tests 3\npass 3\nfail 0\n"

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(robot_engine, "_run_checked_command", side_effect=fake_cmd), \
                 patch.object(robot_engine, "_sha256", return_value=robot_engine.ENV_SHA256), \
                 patch.object(robot_engine, "_vault_checks",
                              return_value={"ok": True, "nodes": 259, "edges": 493}), \
                 patch.object(robot_engine, "h_service_health",
                              return_value={"ok": True, "summary": "up=10/10 down=none"}), \
                 patch.object(robot_engine, "REPORT_DIR", Path(tmp)):
                result = robot_engine.h_quality_guard("SYS_02")
            self.assertTrue(result["ok"], result)
            for part in ("py=44/44", "dash=3/3", "env=ok", "endpoints=ok", "graph=ok"):
                self.assertIn(part, result["summary"])
            report = json.loads((Path(tmp) / "quality_guard_report.json").read_text(encoding="utf-8"))
            self.assertTrue(report["checks"]["env"])

    # ── SYS_05 : miroir local du journal d'audit (J-lignes) ─────────────────
    def test_parse_milestones_is_bounded_and_j_only(self):
        lines = [
            "| O5 | ouvert | Ouvert |",
            "| J35 | Audit A→E | " + "x" * 400 + " | **Fait** |",
            "| J36 | Queue | " + "y" * 400 + " | **Fait** |",
            "| J31-a | 3 robots | " + "z" * 400 + " | **Fait** |",
        ]
        items = robot_engine._parse_milestones("\n".join(lines), limit=2)
        self.assertEqual([item["id"] for item in items], ["J36", "J31-a"])
        self.assertTrue(all(len(item["detail"]) <= 240 for item in items))
        self.assertTrue(all(item["id"].startswith("J") for item in items))

    def test_agent_audit_handler_writes_bounded_report(self):
        text = "\n".join(f"| J{i} | étape {i} | **Fait** |" for i in range(30))
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            pmap = tmpdir / "PROJECT_MAP.md"
            pmap.write_text(text, encoding="utf-8")
            with patch.object(robot_engine, "PROJECT_MAP", pmap), \
                 patch.object(robot_engine, "REPORT_DIR", tmpdir):
                result = robot_engine.h_agent_audit("SYS_05")
            self.assertTrue(result["ok"])
            self.assertIn("milestones=20", result["summary"])
            self.assertIn("latest=J29", result["summary"])
            report = json.loads((tmpdir / "agent_audit_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["available"], True)
            self.assertEqual(report["source"], "PROJECT_MAP.md")
            self.assertEqual(len(report["items"]), 20)
            self.assertEqual(report["items"][-1]["id"], "J29")
            self.assertNotIn("urlopen", json.dumps(report))

    def test_agent_audit_missing_map_is_honest(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            with patch.object(robot_engine, "PROJECT_MAP", tmpdir / "nope.md"), \
                 patch.object(robot_engine, "REPORT_DIR", tmpdir):
                result = robot_engine.h_agent_audit("SYS_05")
            self.assertFalse(result["ok"])
            self.assertEqual(result["summary"], "no_data_source=project_map")
            report = json.loads((tmpdir / "agent_audit_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["available"], False)
            self.assertEqual(report["reason"], "no_data_source")
            self.assertEqual(report["items"], [])

    def test_agent_audit_is_registered_as_a_local_role(self):
        self.assertIn("agent_audit", robot_engine.ROLE_HANDLERS)
        self.assertIs(robot_engine.ROLE_HANDLERS["agent_audit"], robot_engine.h_agent_audit)


if __name__ == "__main__":
    unittest.main()
