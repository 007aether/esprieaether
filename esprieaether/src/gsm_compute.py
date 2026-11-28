"""J195 — صورة صادقة لقدرة الحوسبة على شبكة GSM.

لا تفتح الشبكة، لا تنفّذ أمراً على جهاز، ولا تدّعي أن الهواتف تزيد RAM الحاسوب.
كلشي مقروء من ملفات الحالة المحلية، و`live_verified` ما كيجي إلا بدليل حي حديث.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parent
_STATE_DIR = _SRC.parent / "state"
TTL_DAYS = 7
THIN_TASKS = ("status", "battery", "props")
COMPUTE_TASKS = ("compute:map", "compute:reduce")


def _read(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _parse_stamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _fresh(value: dict[str, Any] | None, now: datetime) -> bool:
    """الدليل كيكون حديث إلا كان checkedAt قديمش وexpiresAt مازال ما فاتش."""
    if not value:
        return False
    checked = _parse_stamp(value.get("checkedAt"))
    expires = _parse_stamp(value.get("expiresAt"))
    if not checked or checked > now + timedelta(minutes=5):
        return False
    if expires and expires < now:
        return False
    if not expires and now - checked > timedelta(days=TTL_DAYS):
        return False
    return True


def _int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _registered_workers(state_dir: Path, now: datetime) -> tuple[list[dict[str, Any]], int]:
    """سجل اختياري للعمال الحقيقيين؛ ما كاينش إلا إلا إذا سجّلوه صراحة."""
    path = state_dir / "gsm_compute_workers.json"
    raw = _read(path)
    if not raw:
        return [], 0
    workers = raw.get("workers")
    if not isinstance(workers, list):
        return [], 0
    live = 0
    for worker in workers:
        if not isinstance(worker, dict):
            continue
        seen = _parse_stamp(worker.get("lastSeen"))
        if seen and now - seen <= timedelta(days=TTL_DAYS) and seen <= now + timedelta(minutes=5):
            live += 1
    return workers, live


def build_snapshot(state_dir: Path = _STATE_DIR, now: datetime | None = None) -> dict[str, Any]:
    """يبني صورة من الملفات المحلية غير. أي رقم ما عندوش دليل كيبقى 0."""
    now = now or datetime.now(timezone.utc)
    state_dir = Path(state_dir)
    gsm = _read(state_dir / "gsm_status.json")
    workers_file = _read(state_dir / "gsm_workers.json")
    trial = _read(state_dir / "gsm_model_trial.json")
    registered, live_workers = _registered_workers(state_dir, now)

    gsm_fresh = _fresh(gsm, now)
    devices = gsm.get("devices") if gsm and isinstance(gsm.get("devices"), list) else []
    devices = [d for d in devices if isinstance(d, dict)]
    discovered = _int(gsm.get("discovered")) if gsm else 0
    online = _int(gsm.get("online")) if gsm else 0
    if not discovered:
        discovered = len(devices)
    sim_ready = sum(1 for d in devices if str(d.get("sim_state") or "").upper() == "READY")
    internet_reported = sum(
        1 for d in devices
        if str(d.get("network") or "").strip().lower() not in ("", "unknown", "none")
    )
    root_count = _int(gsm.get("root_count")) if gsm else 0
    termux_count = _int(gsm.get("termux_count")) if gsm else 0
    thin_ready = _int((gsm.get("worker") or {}).get("ready")) if gsm and isinstance(gsm.get("worker"), dict) else 0

    workers_online = _int(workers_file.get("online")) if workers_file else 0
    benchmark = None
    for worker in registered:
        if isinstance(worker, dict) and isinstance(worker.get("benchmark"), dict):
            bench = worker["benchmark"]
            seen = _parse_stamp(bench.get("checkedAt") or worker.get("lastSeen"))
            if seen and now - seen <= timedelta(days=TTL_DAYS):
                benchmark = bench
                break

    contradictions: list[str] = []
    if gsm_fresh and workers_file and online > 0 and workers_online == 0:
        contradictions.append(
            f"gsm_status online={online} mais gsm_workers online=0 — preuves locales incoherentes"
        )
    if online > len(devices):
        contradictions.append(f"online={online} > devices listes={len(devices)}")

    if not gsm_fresh:
        status = "needs_user_data"
        reason = "aucune preuve ADB fraiche (scan read-only a relancer)"
    elif live_workers == 0:
        status = "not_available"
        reason = "aucun agent de calcul enregistre sur les telephones; ADB read-only seul"
    elif benchmark is None:
        status = "implemented_unverified"
        reason = "des workers sont enregistres mais aucun benchmark frais"
    else:
        status = "live_verified"
        reason = "benchmark frais disponible"

    return {
        "status": status,
        "ok": status == "live_verified",
        "checkedAt": now.isoformat().replace("+00:00", "Z"),
        "reason": reason,
        "fleet": {
            "targetDevices": 20,
            "discovered": discovered,
            "adbOnline": online,
            "simReady": sim_ready,
            "internetReported": internet_reported,
            "rootCount": root_count,
            "termuxCount": termux_count,
            "thinEndpointsReady": thin_ready,
            "registeredWorkers": len(registered),
            "liveWorkers": live_workers,
        },
        "capabilities": {
            "allowedNow": list(THIN_TASKS),
            "computeTasks": list(COMPUTE_TASKS) if live_workers else [],
            "heavyInference": bool(live_workers and benchmark),
            "ramExtensionPossible": False,
            "ramNote": "Un telephone ne peut pas ajouter de RAM au PC; seul le calcul peut etre delegue.",
        },
        "contradictions": contradictions,
        "evidence": {
            "gsmStatusFresh": gsm_fresh,
            "gsmStatusCheckedAt": (gsm or {}).get("checkedAt"),
            "workersCheckedAt": (workers_file or {}).get("checkedAt"),
            "modelTrialStatus": (trial or {}).get("status"),
            "benchmark": benchmark,
        },
        "note": (
            "Lecture locale seulement. Aucun SMS, appel, APK, root ou commande device. "
            "Chaque action GSM reste soumise a SIM READY et approved_once explicite."
        ),
    }


def write_snapshot(state_dir: Path = _STATE_DIR, now: datetime | None = None) -> Path:
    state_dir = Path(state_dir)
    snapshot = build_snapshot(state_dir, now)
    target = state_dir / "gsm_compute.json"
    fd, tmp_name = tempfile.mkstemp(prefix="gsm_compute.", suffix=".tmp", dir=str(state_dir))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Etat honeste de la capacite de calcul GSM")
    parser.add_argument("--state-dir", default=str(_STATE_DIR))
    parser.add_argument("--write", action="store_true", help="ecrire gsm_compute.json")
    args = parser.parse_args()
    state_dir = Path(args.state_dir)
    if args.write:
        target = write_snapshot(state_dir)
        print(f"written {target}")
    print(json.dumps(build_snapshot(state_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
