from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import gsm_termux_prepare as prep  # noqa: E402

NOW = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)


def _state(tmp_path: Path, sim: str = "ABSENT") -> Path:
    (tmp_path / "gsm_status.json").write_text(json.dumps({
        "checkedAt": "2026-11-28T10:00:00Z",
        "devices": [{"serial": "S1", "model": "SM-G955", "sim_state": sim,
                     "root": False, "termux": False, "free_mb": 200}],
    }), encoding="utf-8")
    return tmp_path


def test_prepare_writes_files_but_no_execution(tmp_path: Path) -> None:
    target = prep.prepare(_state(tmp_path), tmp_path / "plan")
    assert (target / "worker.py").exists()
    assert (target / "bootstrap.sh").exists()
    assert (target / "README.md").exists()
    plan = json.loads((target / "plan.json").read_text(encoding="utf-8"))
    assert plan["deviceCount"] == 1
    assert plan["devices"][0]["state"] == "pending"
    assert plan["devices"][0]["approved"] is False
    assert plan["devices"][0]["executed"] is False
    assert plan["devices"][0]["command"] is None
    assert plan["executor"] == "adb.exe only"
    assert "touping.exe" in plan["forbiddenBinaries"]
    assert not list(target.glob("*.tmp"))


def test_source_has_no_executor(tmp_path: Path) -> None:
    source = (ROOT / "scripts" / "gsm_termux_prepare.py").read_text(encoding="utf-8")
    host = source.split("WORKER = '''", 1)[0]
    assert "import subprocess" not in host
    assert "touping.exe" in host  # uniquement comme zone interdite
    assert "os.system" not in host
    assert "Popen" not in host


def test_worker_is_read_only_and_token_gated(tmp_path: Path) -> None:
    worker = prep.WORKER
    assert 'ALLOWED = ("status", "battery", "props")' in worker
    assert "127.0.0.1" in worker
    assert "X-Worker-Token" in worker
    assert '["dumpsys", "battery"]' in worker
    assert "getprop" in worker
    assert "am start" not in worker
    assert "send_sms" not in worker
    assert "content://sms" not in worker


@pytest.mark.parametrize("approval", [
    None,
    {},
    {"state": "proposed"},
    {"state": "approved_once"},
    {"state": "approved_once", "actor": "owner"},
    {"state": "approved_once", "actor": "owner", "serial": "OTHER",
     "action": "gsm_termux_bootstrap", "recipient": "S1", "content": "install"},
    {"state": "approved_once", "actor": "owner", "serial": "S1",
     "action": "gsm_send_sms", "recipient": "S1", "content": "install"},
])
def test_render_command_requires_explicit_approval(tmp_path: Path, approval) -> None:
    state = _state(tmp_path, sim="READY")
    assert prep.render_command("S1", approval, state) is None


def test_sim_not_ready_never_returns_command(tmp_path: Path) -> None:
    state = _state(tmp_path, sim="ABSENT")
    approval = {"state": "approved_once", "actor": "owner", "serial": "S1",
                "action": "gsm_termux_bootstrap", "recipient": "S1", "content": "prepare"}
    assert prep.render_command("S1", approval, state) is None


def test_approved_ready_device_returns_text_only(tmp_path: Path) -> None:
    state = _state(tmp_path, sim="READY")
    approval = {"state": "approved_once", "actor": "owner", "serial": "S1",
                "action": "gsm_termux_bootstrap", "recipient": "S1", "content": "prepare"}
    command = prep.render_command("S1", approval, state)
    assert command == "adb -s S1 shell sh /sdcard/termux-bootstrap.sh"
    assert "touping" not in command
