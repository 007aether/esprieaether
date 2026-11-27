"""J129 — TDD : pont GSM local en lecture seule, sans touping.exe ni cloud."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock
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

INVENTORY = """9
28
arm64-v8a
uid=2000(shell) gid=2000(shell) groups=2000(shell),1004(input)
		total        used        free      shared     buffers
Mem:             3347       2828         519           1          25
/dev/block/dm-1  53G  3.3G   50G   7% /data
"""


def fake_runner(calls):
    def run(argv, timeout):
        calls.append(list(argv))
        if argv[-1] == "-l" and "devices" in argv:
            return DEVICES
        if argv[-1] == gsm_bridge.INVENTORY_CMD:
            return INVENTORY
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

    def test_scan_juge_la_capacite_reelle_des_telephones(self) -> None:
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            report = gsm_bridge.scan(state_dir=Path(tmp), adb=ADB, runner=fake_runner(calls))
        row = report["devices"][0]
        self.assertEqual(row["android"], "9")
        self.assertEqual(row["sdk"], "28")
        self.assertEqual(row["abi"], "arm64-v8a")
        self.assertFalse(row["root"])
        self.assertEqual(row["free_mb"], 519)
        self.assertEqual(row["storage_gb"], 50)
        self.assertFalse(row["termux"])
        self.assertEqual(report["android"], "9")
        self.assertEqual(report["free_mb_min"], 519)
        self.assertEqual(report["storage_gb_min"], 50)
        self.assertEqual(report["root_count"], 0)
        self.assertEqual(report["termux_count"], 0)

    def test_scan_publie_un_plan_de_worker_leger(self) -> None:
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            report = gsm_bridge.scan(state_dir=Path(tmp), adb=ADB, runner=fake_runner(calls))
        worker = report["worker"]
        self.assertEqual(worker["mode"], "thin_endpoint")
        self.assertEqual(worker["ready"], 2)
        self.assertTrue(worker["readOnly"])
        self.assertEqual(set(worker["tasks"]), {"status", "battery", "props"})
        self.assertTrue(worker["gateway"].startswith("http://127.0.0.1:"))
        self.assertFalse(worker["heavyInference"])

    def test_dispatch_refuse_une_tache_daction(self) -> None:
        with self.assertRaises(ValueError):
            gsm_bridge.dispatch_task(ADB, "serial-1", "sms", fake_runner([]))

    def test_dispatch_execute_une_lecture_seule(self) -> None:
        calls = []

        def runner(argv, timeout):
            calls.append(list(argv))
            return BATTERY

        result = gsm_bridge.dispatch_task(ADB, "serial-1", "battery", runner)
        self.assertEqual(result["task"], "battery")
        self.assertEqual(result["serial"], "serial-1")
        self.assertIn("level: 87", result["output"])
        self.assertTrue(result["readOnly"])
        self.assertEqual(calls[0][3:], ["shell", "dumpsys", "battery"])

    def test_scan_nenvoie_aucune_commande_daction(self) -> None:
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            gsm_bridge.scan(state_dir=Path(tmp), adb=ADB, runner=fake_runner(calls))
        for argv in calls:
            tail = " ".join(argv).lower()
            self.assertNotIn("sms", tail)
            self.assertNotIn("call", tail)
            self.assertNotIn("input text", tail)
            allowed = {"devices", "-l", "shell", "getprop", "dumpsys", "battery", gsm_bridge.INVENTORY_CMD}
            self.assertTrue(set(argv[3:]).issubset(allowed))

    def test_probe_fleet_execute_les_taches_de_lecture(self) -> None:
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            report = gsm_bridge.probe_fleet(
                state_dir=Path(tmp), adb=ADB, runner=fake_runner(calls),
                serials=["serial-1", "serial-2"], tasks=("battery",),
            )
            saved = json.loads((Path(tmp) / "gsm_workers.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "live_verified")
        self.assertEqual(report["online"], 2)
        self.assertTrue(report["readOnly"])
        self.assertEqual(len(report["samples"]), 2)
        self.assertEqual(saved["status"], "live_verified")
        for argv in calls:
            self.assertTrue(set(argv[3:]).issubset({
                "shell", "getprop", "dumpsys", "battery", gsm_bridge.INVENTORY_CMD,
            }))

    def test_probe_fleet_sans_appareil_demande_les_donnees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = gsm_bridge.probe_fleet(
                state_dir=Path(tmp), adb=ADB, runner=fake_runner([]), serials=[]
            )
        self.assertEqual(report["status"], "needs_user_data")
        self.assertEqual(report["online"], 0)

    def test_model_preflight_sans_prerequis_demande_des_donnees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = gsm_bridge.model_preflight(
                state_dir=Path(tmp), binary_dirs=[], model_dirs=[]
            )
            saved = json.loads((Path(tmp) / "gsm_model_trial.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "needs_user_data")
        self.assertFalse(report["ready"])
        self.assertIn("arm64", report["reason"])
        self.assertEqual(saved["status"], "needs_user_data")

    def test_dossier_de_depot_local_est_dans_les_chemins_par_defaut(self) -> None:
        self.assertEqual(gsm_bridge.LOCAL_MODEL_DIR, gsm_bridge.BASE_DIR / "state" / "gsm_model")
        self.assertIn(gsm_bridge.LOCAL_MODEL_DIR, gsm_bridge.DEFAULT_BINARY_DIRS)
        self.assertIn(gsm_bridge.LOCAL_MODEL_DIR, gsm_bridge.DEFAULT_MODEL_DIRS)

    def test_modele_local_est_decouvert_sans_telechargement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state"
            binary_dir = state / "gsm_model" / "binary"
            model_dir = state / "gsm_model" / "models"
            binary_dir.mkdir(parents=True)
            model_dir.mkdir(parents=True)
            binary = binary_dir / "llama.cpp-arm64"
            binary.write_bytes(b"\x7fELF" + b"\x00" * 12)
            model = model_dir / "tiny.gguf"
            model.write_bytes(b"\x00" * 1024)
            with mock.patch.object(gsm_bridge, "DEFAULT_BINARY_DIRS", (binary_dir,)), \
                    mock.patch.object(gsm_bridge, "DEFAULT_MODEL_DIRS", (model_dir,)):
                report = gsm_bridge.model_preflight(state_dir=state)
            self.assertEqual(report["status"], "implemented_unverified")
            self.assertTrue(report["ready"])
            self.assertEqual(report["binary"], str(binary))
            self.assertEqual(report["model"], str(model))
            self.assertNotIn("http", report["reason"])
            self.assertTrue((state / gsm_bridge.MODEL_TRIAL_FILE).exists())

    def test_model_preflight_avec_prerequis_reste_non_verifie(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "runtime"
            models = root / "models"
            runtime.mkdir()
            models.mkdir()
            binary = runtime / "llama-cli-arm64"
            binary.write_bytes(b"\x7fELFlocal")
            model = models / "tiny-Q4.gguf"
            model.write_bytes(b"GGUF" + b"\0" * 128)
            report = gsm_bridge.model_preflight(
                state_dir=root, binary_dirs=[runtime], model_dirs=[models]
            )
        self.assertEqual(report["status"], "implemented_unverified")
        self.assertTrue(report["ready"])
        self.assertTrue(report["binary"].endswith("llama-cli-arm64"))
        self.assertTrue(report["model"].endswith("tiny-Q4.gguf"))

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

    def test_port_adb_local_est_5038_et_surchargeable(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(gsm_bridge.adb_port(), "5038")
            self.assertEqual(gsm_bridge.adb_env()["ANDROID_ADB_SERVER_PORT"], "5038")
        with mock.patch.dict("os.environ", {"ESPRIE_GSM_ADB_PORT": "5040"}):
            self.assertEqual(gsm_bridge.adb_port(), "5040")
            self.assertEqual(gsm_bridge.adb_env()["ANDROID_ADB_SERVER_PORT"], "5040")

    def test_run_transmet_le_port_adb_sans_changer_les_arguments(self) -> None:
        proc = mock.Mock(returncode=0, stdout="ok", stderr="")
        argv = [ADB, "-s", "serial-1", "shell", "dumpsys", "battery"]
        with mock.patch.object(gsm_bridge.subprocess, "run", return_value=proc) as run:
            output = gsm_bridge._run(argv, 8, None)
        self.assertEqual(output, "ok")
        self.assertEqual(run.call_args.kwargs["env"]["ANDROID_ADB_SERVER_PORT"], "5038")
        self.assertEqual(run.call_args.args[0], argv)

    def test_scan_publie_les_etats_adb_et_le_port(self) -> None:
        devices = """List of devices attached
9887a839464e323432     device product:dreamqltesq model:SM_G950U transport_id:1
ce0517153333862301     device product:dreamltexx model:SM_G950F transport_id:2
ce071717c2d7403f0c     offline
deadbeef00000000     unauthorized
"""

        def runner(argv, timeout):
            if "devices" in argv:
                return devices
            return fake_runner([])(argv, timeout)

        with tempfile.TemporaryDirectory() as tmp:
            report = gsm_bridge.scan(state_dir=Path(tmp), adb=ADB, runner=runner)
            saved = json.loads((Path(tmp) / "gsm_status.json").read_text(encoding="utf-8"))
        self.assertEqual(report["adbPort"], "5038")
        self.assertEqual(report["adbStates"], {"device": 2, "offline": 1, "unauthorized": 1})
        self.assertEqual(report["online"], 2)
        self.assertEqual(saved["adbStates"]["unauthorized"], 1)
        self.assertEqual(saved["adbPort"], "5038")


if __name__ == "__main__":
    unittest.main()
