"""J84: sentinelle locale des agents — lecture seule, loopback, zéro cloud."""
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SENTINEL = ROOT / "esprieaether" / "scripts" / "local_sentinel.py"
HUD = ROOT / "esprieaether" / "G0DM0D3" / "out" / "jarvis.html"
RELAY = ROOT / "esprieaether" / "scripts" / "serve_g0dm0d3.mjs"
SUPERVISOR = ROOT / "esprieaether" / "scripts" / "keep_alive.ps1"


def load_sentinel():
    spec = importlib.util.spec_from_file_location("esprie_local_sentinel", SENTINEL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LocalSentinelTest(unittest.TestCase):
    def test_sentinel_is_stdlib_only_loopback_and_sse(self):
        source = SENTINEL.read_text(encoding="utf-8")
        self.assertIn('"127.0.0.1"', source)
        self.assertIn("text/event-stream", source)
        self.assertIn('"/events"', source)
        self.assertIn('"/health"', source)
        imports = {m.group(1).split(".")[0] for m in re.finditer(
            r"^(?:import|from)\s+([A-Za-z_][\w.]*)", source, re.M)}
        self.assertTrue(imports <= {
            "__future__", "json", "os", "re", "subprocess", "sys",
            "threading", "time", "http", "pathlib",
        }, imports)
        for forbidden in ("urllib.request", "requests", "httpx", "webbrowser",
                          "Open-Meteo", "codex-resets", "deepseek", "bigmodel"):
            self.assertNotIn(forbidden, source)

    def test_agents_are_local_stack_not_upstream_mac_tools(self):
        source = SENTINEL.read_text(encoding="utf-8")
        for key in ("opencode", "codex", "claude", "atulya"):
            self.assertIn('"%s"' % key, source)
        self.assertNotIn("zcode", source)
        self.assertNotIn("weather", source)
        self.assertNotIn("quota", source)

    def test_classify_uses_four_honest_states(self):
        mod = load_sentinel()
        self.assertEqual(mod.classify(0.20, 0, True), "active")
        self.assertEqual(mod.classify(0.00, 1, True), "running")
        self.assertEqual(mod.classify(0.00, 0, True), "offline")
        self.assertEqual(mod.classify(0.00, 0, False), "absent")

    def test_activity_decays_and_cold_start_is_not_activity(self):
        mod = load_sentinel()
        self.assertEqual(mod.decay(0.5, 0), 0.4)
        self.assertEqual(mod.decay(0.5, 4), 1.0)
        snap = {"a": (1, 10), "b": (2, 20)}
        self.assertEqual(mod.diff_snapshots(None, {"opencode": snap}), {"opencode": 0})
        changed = mod.diff_snapshots(
            {"opencode": snap}, {"opencode": {"a": (1, 11), "b": (2, 20)}})
        self.assertEqual(changed, {"opencode": 1})

    def test_process_matching_ignores_paths_and_sentinel_itself(self):
        mod = load_sentinel()
        self.assertEqual(mod.match_command("C:\\tools\\opencode.exe --session x"), {"opencode"})
        self.assertEqual(mod.match_command("python.exe -m atulya.cli serve"), {"atulya"})
        self.assertEqual(mod.match_command("python.exe scripts\\local_sentinel.py"), set())
        self.assertEqual(mod.match_command("CodexBar.exe"), set())
        self.assertEqual(mod.match_command("python.exe -m src.local_brain"), set())

    def test_atulya_signals_match_real_local_files(self):
        source = SENTINEL.read_text(encoding="utf-8")
        # Les signaux réels vérifiés sur disque, pas un WAL supposé.
        for name in ("operations.sqlite3", "lessons.json",
                     "briefings.json", "novel_tasks.jsonl"):
            self.assertIn('"%s"' % name, source)

    def test_relay_keeps_sse_same_origin_and_loopback(self):
        source = RELAY.read_text(encoding="utf-8")
        self.assertIn("/sentinel/", source)
        self.assertIn("proxySentinel", source)
        self.assertIn("ESPRIE_SENTINEL_HOST", source)
        self.assertIn("text/event-stream", source)
        self.assertIn('"127.0.0.1"', source)

    def test_supervisor_manages_sentinel_health(self):
        source = SUPERVISOR.read_text(encoding="utf-8")
        self.assertIn("Name='sentinel'", source)
        self.assertIn("Port=8766", source)
        self.assertIn("8766 = '/health'", source)

    def test_hud_reads_sse_only_without_external_or_execution_control(self):
        html = HUD.read_text(encoding="utf-8")
        for marker in ('id="sentinelCanvas"', 'id="sentinelAgents"',
                       'id="sentinelWave"', 'var SEN = "/sentinel/events";',
                       'new EventSource(SEN)'):
            self.assertIn(marker, html)
        self.assertNotIn("https://", html)
        self.assertNotIn("cdn.", html)
        self.assertFalse(re.search(r"onclick|\bPOST\b", html))


if __name__ == "__main__":
    unittest.main()
