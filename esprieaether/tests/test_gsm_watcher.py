"""J158 — TDD : veilleuse GSM en lecture seule, refresh seulement si preuve périmée."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import gsm_bridge  # noqa: E402
import gsm_watcher  # noqa: E402


def evidence(checked=None, count=2, **extra):
    stamp = checked or datetime.now(timezone.utc)
    stamp = stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "ok": True,
        "status": "live_verified",
        "readOnly": True,
        "checkedAt": stamp,
        "expiresAt": stamp,
        "online": count,
        "discovered": count,
        "devices": [{"serial": f"s{i}", "sim_state": "ABSENT"} for i in range(count)],
        "errors": [],
        **extra,
    }


def stale_evidence():
    old = datetime.now(timezone.utc) - timedelta(days=8)
    return evidence(old)


def write_status(directory, row):
    (directory / "gsm_status.json").write_text(
        json.dumps(row, ensure_ascii=False), encoding="utf-8")


class GsmWatcherTest(unittest.TestCase):
    def test_ne_scanne_pas_quand_la_preuve_est_fraiche(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_status(directory, evidence())

            def forbidden(**kwargs):
                raise AssertionError("scan ne doit pas être lancé")

            out = gsm_watcher.refresh(directory, scan_fn=forbidden)
            self.assertEqual(out["status"], "live_verified")
            self.assertFalse(out["refreshed"])
            self.assertIsNone(out["alert"])
            self.assertTrue(out["readOnly"])

    def test_scanne_en_lecture_seule_quand_la_preuve_est_perimee(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_status(directory, stale_evidence())
            calls = []

            def fake_scan(**kwargs):
                calls.append(kwargs)
                return evidence(count=10)

            out = gsm_watcher.refresh(directory, scan_fn=fake_scan)
            self.assertEqual(len(calls), 1)
            self.assertTrue(out["refreshed"])
            self.assertIsNone(out["alert"])
            self.assertEqual(out["online"], 10)
            watch = json.loads((directory / "gsm_watch.json").read_text(encoding="utf-8"))
            self.assertEqual(watch["online"], 10)
            self.assertEqual(watch["targetDevices"], 20)

    def test_alerte_sans_test_quand_le_scan_echoue(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_status(directory, stale_evidence())

            def broken(**kwargs):
                raise OSError("adb indisponible")

            out = gsm_watcher.refresh(directory, scan_fn=broken)
            self.assertEqual(out["alert"], "expired")
            self.assertEqual(out["status"], "implemented_unverified")
            self.assertFalse(out["refreshed"])

    def test_detecte_les_20_appareils_sans_rien_declencher(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_status(directory, evidence(count=20))
            out = gsm_watcher.refresh(
                directory, scan_fn=lambda **k: self.fail("scan inutile"))
            self.assertTrue(out["targetReached"])
            self.assertEqual(out["discovered"], 20)
            self.assertNotIn("argv", out)
            self.assertNotIn("command", out)

    def test_etat_public_sans_secret_ni_commande(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_status(directory, evidence(token="secret"))
            gsm_watcher.refresh(directory, scan_fn=lambda **k: self.fail("scan inutile"))
            raw = (directory / "gsm_watch.json").read_text(encoding="utf-8")
            self.assertNotIn("secret", raw)
            self.assertNotIn("token", raw)
            self.assertNotIn("sms", raw)
            self.assertNotIn("call", raw)

    def test_les_doubles_chemins_restent_identiques(self):
        self.assertEqual(gsm_watcher.STATE_FILE, "gsm_status.json")
        self.assertEqual(gsm_watcher.WATCH_FILE, "gsm_watch.json")
        self.assertEqual(gsm_watcher.TTL_DAYS, gsm_bridge.TTL_DAYS)

    def test_le_superviseur_lance_la_veilleuse_sans_flag_daction(self):
        script = (SRC.parent / "scripts" / "keep_alive.ps1").read_text(encoding="utf-8")
        self.assertIn("gsm_watcher.py", script)
        self.assertIn("Name='gsm-watcher'", script)
        self.assertIn("'--daemon'", script)
        self.assertNotIn("--sms", script)
        self.assertNotIn("--call", script)


if __name__ == "__main__":
    unittest.main()
