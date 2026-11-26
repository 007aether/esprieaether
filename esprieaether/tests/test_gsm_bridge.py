"""J129 — TDD : pont GSM local en lecture seule, sans touping.exe ni cloud."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import gsm_bridge  # noqa: E402

ADB = r"C:\Program Files (x86)\panda_android\tools\adb.exe"

DEVICES = """List of devices attached
9887a839464e323432     device product:dreamqltesq model:SM_G950U device:dreamqltesq transport_id:3
ce0517153333862301     device product:dreamltexx model:SM_G950F device:dreamlte transport_id:16
ce071717c2d7403f0c     offline
"""

PROPS = """[ro.product.model]: [SM_G950U]
[gsm.sim.state]: [READY]
[gsm.network.type]: [LTE]
[gsm.operator.alpha]: [LOCAL OP]
[gsm.operator.numeric]: [12345]
"""

BATTERY = """Current Battery Service state:
  AC powered: false
  USB powered: true
  level: 87
  status: 2
"""


def fake_runner(calls):
    def run(argv, timeout):
        calls.append(list(argv))
        if argv[-1] == "-l" and "devices" in argv:
            return DEVICES
        if argv[-2:] == ["shell", "getprop"]:
            return PROPS
        if argv[-3:] == ["shell", "dumpsys", "battery"]:
            return BATTERY
        raise AssertionError(f"commande inattendue: {argv}")
    return run


class GsmBridgeTest(unittest.TestCase):
    def test_parse_devices_ignore_les_lignes_de_daemon(self) -> None:
        rows = gsm_bridge.parse_devices("List of devices attached\n* daemon not running; starting it\n" + DEVICES)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["serial"], "9887a839464e323432")
        self.assertEqual(rows[0]["model"], "SM_G950U")
        self.assertEqual(rows[2]["state"], "offline")

    def test_parse_props_et_batterie(self) -> None:
        props = gsm_bridge.parse_props(PROPS)
        self.assertEqual(props["gsm.sim.state"], "READY")
        self.assertEqual(props["gsm.operator.numeric"], "12345")
        battery = gsm_bridge.parse_battery(BATTERY)
        self.assertEqual(battery["level"], 87)
        self.assertTrue(battery["usb_powered"])

    def test_scan_est_live_verified_avec_20_telephones(self) -> None:
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            report = gsm_bridge.scan(
                state_dir=state,
                adb=ADB,
                runner=fake_runner(calls),
            )
            saved = json.loads((state / "gsm_status.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "live_verified")
        self.assertTrue(report["ok"])
        self.assertTrue(report["readOnly"])
        self.assertEqual(report["online"], 2)
        self.assertEqual(len(report["devices"]), 2)
        self.assertEqual(report["devices"][0]["sim_state"], "READY")
        self.assertEqual(report["devices"][0]["battery_level"], 87)
        checked = datetime.fromisoformat(report["checkedAt"].replace("Z", "+00:00"))
        expires = datetime.fromisoformat(report["expiresAt"].replace("Z", "+00:00"))
        self.assertEqual(expires - checked, timedelta(days=7))
        self.assertEqual(saved["status"], "live_verified")
        self.assertNotIn("token=", json.dumps(saved).lower())

    def test_scan_nenvoie_aucune_commande_daction(self) -> None:
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            gsm_bridge.scan(state_dir=Path(tmp), adb=ADB, runner=fake_runner(calls))
        for argv in calls:
            tail = " ".join(argv).lower()
            self.assertNotIn("sms", tail)
            self.assertNotIn("call", tail)
            self.assertNotIn("input text", tail)
            self.assertTrue(set(argv[3:]).issubset({"devices", "-l", "shell", "getprop", "dumpsys", "battery"}))

    def test_scan_sans_adb_est_not_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = gsm_bridge.scan(state_dir=Path(tmp), adb="C:/introuvable/adb.exe", runner=fake_runner([]))
        self.assertEqual(report["status"], "not_available")
        self.assertFalse(report["ok"])

    def test_scan_sans_telephone_demande_les_donnees(self) -> None:
        def no_devices(argv, timeout):
            if "devices" in argv:
                return "List of devices attached\n"
            raise AssertionError(argv)

        with tempfile.TemporaryDirectory() as tmp:
            report = gsm_bridge.scan(state_dir=Path(tmp), adb=ADB, runner=no_devices)
        self.assertEqual(report["status"], "needs_user_data")
        self.assertEqual(report["online"], 0)


if __name__ == "__main__":
    unittest.main()
