from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import gsm_compute  # noqa: E402

NOW = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)


def _stamp(delta_days: int = 0) -> str:
    return (NOW - timedelta(days=delta_days)).isoformat().replace("+00:00", "Z")


def _state(tmp_path: Path, *, devices=None, online=10, workers_online=0,
           gsm_age=1, workers_age=1, registered=None) -> Path:
    devices = devices if devices is not None else [
        {"serial": "a", "sim_state": "ABSENT", "network": "Unknown", "root": False, "termux": False},
        {"serial": "b", "sim_state": "READY", "network": "Orange", "root": False, "termux": False},
    ]
    (tmp_path / "gsm_status.json").write_text(json.dumps({
        "status": "live_verified", "checkedAt": _stamp(gsm_age),
        "expiresAt": _stamp(gsm_age - 7), "discovered": len(devices), "online": online,
        "root_count": 0, "termux_count": 0,
        "worker": {"mode": "thin_endpoint", "ready": online, "heavyInference": False},
        "devices": devices,
    }), encoding="utf-8")
    (tmp_path / "gsm_workers.json").write_text(json.dumps({
        "status": "needs_user_data", "checkedAt": _stamp(workers_age),
        "online": workers_online, "succeeded": 0,
    }), encoding="utf-8")
    (tmp_path / "gsm_model_trial.json").write_text(json.dumps({
        "status": "needs_user_data", "checkedAt": _stamp(1), "ready": False,
    }), encoding="utf-8")
    if registered is not None:
        (tmp_path / "gsm_compute_workers.json").write_text(
            json.dumps({"workers": registered}), encoding="utf-8")
    return tmp_path


def test_no_compute_worker_is_not_available(tmp_path: Path) -> None:
    state = _state(tmp_path)
    snap = gsm_compute.build_snapshot(state, NOW)
    assert snap["status"] == "not_available"
    assert snap["fleet"]["adbOnline"] == 10
    assert snap["fleet"]["simReady"] == 1
    assert snap["fleet"]["internetReported"] == 1
    assert snap["capabilities"]["allowedNow"] == ["status", "battery", "props"]
    assert snap["capabilities"]["computeTasks"] == []
    assert snap["capabilities"]["ramExtensionPossible"] is False


def test_contradictory_evidence_is_reported_not_fixed(tmp_path: Path) -> None:
    state = _state(tmp_path)
    snap = gsm_compute.build_snapshot(state, NOW)
    assert any("incoherentes" in item for item in snap["contradictions"])


def test_stale_adb_evidence_downgrades_to_needs_user_data(tmp_path: Path) -> None:
    state = _state(tmp_path, gsm_age=9)
    snap = gsm_compute.build_snapshot(state, NOW)
    assert snap["status"] == "needs_user_data"
    assert snap["evidence"]["gsmStatusFresh"] is False


def test_live_worker_without_benchmark_is_unverified(tmp_path: Path) -> None:
    state = _state(tmp_path, registered=[{
        "id": "phone-1", "lastSeen": _stamp(0), "reachable": True,
    }])
    snap = gsm_compute.build_snapshot(state, NOW)
    assert snap["status"] == "implemented_unverified"
    assert snap["fleet"]["liveWorkers"] == 1
    assert snap["capabilities"]["computeTasks"] == ["compute:map", "compute:reduce"]


def test_live_verified_requires_fresh_benchmark(tmp_path: Path) -> None:
    state = _state(tmp_path, registered=[{
        "id": "phone-1", "lastSeen": _stamp(0),
        "benchmark": {"checkedAt": _stamp(1), "tasksSucceeded": 12},
    }])
    snap = gsm_compute.build_snapshot(state, NOW)
    assert snap["status"] == "live_verified"
    assert snap["ok"] is True
    assert snap["capabilities"]["heavyInference"] is True


def test_write_is_atomic_and_readable(tmp_path: Path) -> None:
    state = _state(tmp_path)
    target = gsm_compute.write_snapshot(state, NOW)
    assert target.name == "gsm_compute.json"
    assert json.loads(target.read_text(encoding="utf-8"))["status"] == "not_available"
    assert not list(state.glob("gsm_compute.*.tmp"))


@pytest.mark.parametrize("missing,status,online", [
    ("gsm_status.json", "needs_user_data", 0),
    ("gsm_workers.json", "not_available", 10),
])
def test_missing_file_never_invents_capacity(
    tmp_path: Path, missing: str, status: str, online: int
) -> None:
    state = _state(tmp_path)
    (state / missing).unlink()
    snap = gsm_compute.build_snapshot(state, NOW)
    assert snap["status"] == status
    assert snap["fleet"]["adbOnline"] == online
