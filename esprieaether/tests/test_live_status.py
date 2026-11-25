"""État système honnête, recherche de connaissances et edge loopback."""

import ast
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))
os.environ.setdefault("WEB_SECRET_KEY", "test-secret-not-a-real-key")

import web_interface  # noqa: E402

FIXTURES = {
    "quality_guard_report.json": {
        "checked_at": "2026-11-23T02:19:16",
        "python": {"ran": 53, "ok": True},
        "dashboard": {"passed": 3, "failed": 0},
        "env": {"hash_matches": True},
        "endpoints": "up=10/10 down=none",
        "checks": {"python": True, "dashboard": True, "env": True, "endpoints": True, "graph": True},
    },
    "vault_guard_report.json": {
        "checked_at": "2026-11-23T02:19:28",
        "checks": {"nodes": 259, "edges": 493, "ok": True},
    },
    "backlog_scout_report.json": {
        "checked_at": "2026-11-23T02:19:28",
        "items": [],
        "missing_sources": ["legal", "fiscal", "travail"],
    },
    "local_brain_verification.json": {
        "checked_at": "2026-11-23T00:33:23+00:00",
        "router_health": {"active": "dolphin3", "available": ["dolphin3"], "count": 1},
        "router_models": ["dolphin3"],
        "gateway_status": {"provider": "local-brain"},
        "gateway_completion": {"routed_via": "local-brain", "status": "success"},
        "sentinel": ["ok", "up=10/10 down=none"],
    },
}


class LiveStatusTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.reports = Path(self._tmp.name)
        for name, value in FIXTURES.items():
            (self.reports / name).write_text(json.dumps(value), encoding="utf-8")
        self.client = web_interface.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    def test_local_status_aggregates_real_robot_reports(self):
        with patch.object(web_interface, "REPORT_DIR", self.reports):
            response = self.client.get("/api/local/status")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.get_json()
        self.assertTrue(body["available"])
        self.assertEqual(body["robots"]["quality"]["pythonRan"], 53)
        self.assertEqual(body["robots"]["sentinel"]["summary"], "up=10/10 down=none")
        self.assertEqual(body["robots"]["backlog"]["missingSources"], ["legal", "fiscal", "travail"])
        self.assertEqual(body["graph"]["nodes"], 259)
        self.assertEqual(body["brains"]["count"], 1)
        self.assertEqual(body["brains"]["provider"], "local-brain")
        self.assertNotIn("de9449", json.dumps(body).lower())

    def test_local_status_is_honest_when_reports_are_missing(self):
        empty = self.reports / "empty"
        empty.mkdir()
        with patch.object(web_interface, "REPORT_DIR", empty):
            body = self.client.get("/api/local/status").get_json()
        self.assertFalse(body["available"])
        self.assertEqual(body["robots"]["quality"]["pythonRan"], None)
        self.assertEqual(body["brains"]["count"], 0)
        self.assertEqual(body["graph"]["nodes"], None)

    def test_knowledge_api_is_registered_and_searchable(self):
        rules = {str(rule) for rule in web_interface.app.url_map.iter_rules()}
        self.assertIn("/api/knowledge/search", rules)
        self.assertIn("/api/knowledge/stats", rules)
        stats = self.client.get("/api/knowledge/stats")
        self.assertEqual(stats.status_code, 200, stats.text)
        self.assertGreaterEqual(stats.get_json()["total"], 1)
        search = self.client.get("/api/knowledge/search?q=SUNNAVOK")
        self.assertEqual(search.status_code, 200, search.text)
        self.assertIn("results", search.get_json())
        self.assertIn("total", search.get_json())

    def test_knowledge_page_is_served(self):
        response = self.client.get("/knowledge")
        self.assertEqual(response.status_code, 200, response.text[:200])
        self.assertIn('id="kb-q"', response.text)
        self.assertIn("/api/knowledge/search", response.text)

    def test_home_jarvis_card_uses_local_brain_not_dead_ollama_port(self):
        brain = json.loads(json.dumps(FIXTURES["local_brain_verification.json"]))
        brain["router_health"]["port"] = 31416
        brain["gateway_status"]["local_brain"] = {
            "base_url": "http://127.0.0.1:31416/v1", "available": True,
        }
        (self.reports / "local_brain_verification.json").write_text(
            json.dumps(brain), encoding="utf-8"
        )
        with patch.object(web_interface, "REPORT_DIR", self.reports), \
             patch.object(web_interface, "get_ollama_status", return_value={
                 "status": "offline", "host": "http://127.0.0.1:11434",
             }):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200, response.text[:200])
        self.assertNotIn("11434", response.text)
        self.assertNotIn(">offline<", response.text)
        self.assertIn("31416", response.text)
        self.assertIn("dolphin3", response.text)

    def test_brain_status_api_uses_same_origin_proxy(self):
        rules = {str(rule) for rule in web_interface.app.url_map.iter_rules()}
        self.assertIn("/api/brain/status", rules)

        class _Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch.object(web_interface.urllib.request, "urlopen", return_value=_Resp()) as probe:
            body = self.client.get("/api/brain/status").get_json()
        self.assertEqual([s["name"] for s in body["services"]], ["local-brain", "freellmapi"])
        self.assertTrue(all(s["up"] for s in body["services"]))
        self.assertEqual(probe.call_count, 2)
        self.assertNotIn("de9449", json.dumps(body).lower())

    def test_control_page_points_to_live_ports_only(self):
        text = (BASE_DIR / "src" / "templates" / "control.html").read_text(encoding="utf-8")
        self.assertNotIn("127.0.0.1:8000", text)
        self.assertNotIn("localhost:8000", text)
        self.assertNotIn("127.0.0.1:11434", text)
        self.assertNotIn("localhost:11434", text)
        self.assertNotIn("localhost:5100/status", text)
        self.assertNotIn("localhost:5100/bots", text)
        self.assertNotIn("127.0.0.1:5100/bots", text)
        self.assertNotIn("localhost:5102", text)
        self.assertNotIn("localhost:5103", text)
        self.assertNotIn("/netlify", text)
        self.assertNotIn("/prices'", text)
        self.assertIn("127.0.0.1:5002/health", text)
        self.assertIn("127.0.0.1:5100/health", text)
        self.assertIn("j('/api/okx')", text)
        self.assertIn("j('/api/brain/status')", text)
        self.assertNotIn("'http://127.0.0.1:31416/health'", text)
        self.assertNotIn("'http://127.0.0.1:31415/health'", text)
        self.assertIn("http://127.0.0.1:5103/board", text)
        self.assertIn("http://127.0.0.1:5102/list", text)
        self.assertNotIn("'service indisponible'", text)
        web = (BASE_DIR / "src" / "web_interface.py").read_text(encoding="utf-8")
        self.assertIn("http://127.0.0.1:31416/health", web)
        self.assertIn("http://127.0.0.1:31415/health", web)

    def test_kanban_creates_nested_board_path(self):
        import veritas_kanban

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "deep" / "Coordination" / "kanban.md"
            with patch.object(veritas_kanban, "KANBAN", target):
                text = veritas_kanban._read()
            self.assertTrue(target.exists())
            self.assertIn("## todo", text)

    def test_local_adapters_bind_loopback_and_allow_control_origin(self):
        for rel in ("src/integrations_adapter.py", "src/veritas_kanban.py"):
            with self.subTest(rel=rel):
                text = (BASE_DIR / rel).read_text(encoding="utf-8")
                self.assertIn('app.run(host="127.0.0.1"', text)
                self.assertNotIn('app.run(host="0.0.0.0"', text)
                self.assertIn("Access-Control-Allow-Origin", text)
                self.assertIn("http://127.0.0.1:5000", text)

    def test_service_startup_console_output_survives_windows_cp1252(self):
        for rel in (
            "src/cloud_desktop_agent.py",
            "src/homedock_dashboard.py",
            "src/ai_router.py",
            "src/orchestrator.py",
            "src/agent_mesh.py",
            "src/dsh_bridge.py",
        ):
            with self.subTest(script=rel):
                source = (BASE_DIR / rel).read_text(encoding="utf-8")
                for node in ast.walk(ast.parse(source)):
                    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                        continue
                    if node.func.id not in ("print", "log"):
                        continue
                    for arg in node.args:
                        parts = [arg]
                        if isinstance(arg, ast.JoinedStr):
                            parts.extend(arg.values)
                        for part in parts:
                            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                                self.assertTrue(part.value.isascii(), f"{rel}: {part.value!r}")

    def test_tunnel_panels_never_expose_host_user_or_fingerprint(self):
        control = (BASE_DIR / "src" / "templates" / "control.html").read_text(encoding="utf-8")
        cloud = (BASE_DIR / "src" / "templates" / "cloud.html").read_text(encoding="utf-8")
        agent = (BASE_DIR / "src" / "cloud_desktop_agent.py").read_text(encoding="utf-8")
        for name, text in (("control", control), ("cloud", cloud)):
            with self.subTest(panel=name):
                self.assertNotIn("remote_host", text)
                self.assertNotIn("remote_port", text)
                self.assertNotIn("TUNNEL_KEY", text)
        self.assertIn("TUNNEL_CONFIGURED", agent)
        self.assertIn("configured", agent)
        self.assertIn("http://127.0.0.1:5002", cloud)
        self.assertNotIn("http://127.0.0.1:5001", cloud)

    def test_news_scanner_console_output_survives_windows_cp1252(self):
        source = (BASE_DIR / "scanners" / "news_scanner.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id not in ("print", "_say"):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    calls += 1
                    self.assertTrue(arg.value.isascii(), f"non-ASCII console text: {arg.value!r}")
        self.assertGreater(calls, 0)
        self.assertIn("def _say(", source)

    def test_service_panels_use_local_brains_not_dead_ports(self):
        for rel in ("src/homedock_dashboard.py", "src/cloud_desktop_agent.py"):
            with self.subTest(rel=rel):
                text = (BASE_DIR / rel).read_text(encoding="utf-8")
                self.assertNotIn("11434", text)
                self.assertNotIn(":8000", text)
                self.assertIn("31416", text)
                self.assertIn("31415", text)

    def test_edge_binds_loopback_and_cors_is_not_wildcard(self):
        launcher = (BASE_DIR / "start_web_server.py").read_text(encoding="utf-8")
        web = (BASE_DIR / "src" / "web_interface.py").read_text(encoding="utf-8")
        self.assertIn("WEB_HOST", launcher)
        self.assertNotIn("host='0.0.0.0'", launcher)
        self.assertNotIn('host="0.0.0.0"', launcher)
        self.assertIn('os.getenv("WEB_HOST", "127.0.0.1")', web)
        self.assertNotIn('Access-Control-Allow-Origin"] = "*"', web)
        self.assertNotIn('"aether_default_secret"', web)


if __name__ == "__main__":
    unittest.main()
