"""Startup doit rester un seul lanceur, avec mutex avant tout Process."""

from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1]
STARTUP = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / \
    "Start Menu" / "Programs" / "Startup"
LAUNCHER = BASE / "start_esprieaether_247.ps1"
SUPERVISOR = BASE / "scripts" / "keep_alive.ps1"


class StartupGateTest(unittest.TestCase):
    def test_supervisor_mutex_precedes_any_process_start(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        self.assertLess(text.index("SUNNAVOK_KEEPALIVE_7X24"), text.index("Start-Process"))

    def test_launcher_mutex_precedes_any_process_start(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        mutex = text.find("SUNNAVOK_STARTUP_GATE")
        spawn = text.find("Start-Process")
        self.assertGreater(mutex, -1)
        self.assertLess(mutex, spawn)

    def test_every_startup_entry_delegates_to_the_single_launcher(self):
        launcher = str(LAUNCHER)
        for name in ("EsprieAether247.bat", "SUNNAVOK-KeepAlive.cmd"):
            path = STARTUP / name
            if not path.exists():
                continue
            with self.subTest(entry=name):
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertIn(launcher, text)
                self.assertNotIn("keep_alive.ps1", text)
                self.assertNotIn("start /min", text.lower())

    def test_unmanaged_ports_are_documented_not_supervised(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        for port in ("5101", "31501"):
            with self.subTest(port=port):
                self.assertIn(port, text)

    def test_batch_entry_does_not_claim_success_unconditionally(self):
        bat = STARTUP / "EsprieAether247.bat"
        if not bat.exists():
            return
        text = bat.read_text(encoding="utf-8", errors="ignore")
        self.assertNotIn("EsprieAether started.", text)
        self.assertIn("errorlevel", text.lower())

    def test_one_timeout_is_shared_by_bridge_and_atulya(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        self.assertIn("ESPRIE_LOCAL_TIMEOUT", text)
        self.assertIn("ATULYA_MODEL_TIMEOUT=\"$localTimeout\"", text)
        self.assertIn("ESPRIE_LOCAL_TIMEOUT=\"$localTimeout\"", text)

    def test_legacy_router_ports_are_kept_only_for_documented_dependents(self):
        text = SUPERVISOR.read_text(encoding="utf-8")
        self.assertIn("11435", text)
        self.assertIn("31415", text)
        self.assertIn("dépendances", text)


if __name__ == "__main__":
    unittest.main()
