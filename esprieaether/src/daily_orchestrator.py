#!/usr/bin/env python3
"""J118/J141 — ordonnanceur local quotidien des cinq agents.

Une seule journée au plus par intervalle de 24 h. Les quatre agents sont
appelés en local, chacun dans son propre ``try`` : une panne n'empêche pas
les autres de travailler. Aucun appel réseau ici, aucun commit, aucun
restart, aucun Telegram : le seul fichier écrit est le rapport public.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

DEFAULT_STATE_DIR = BASE_DIR / "state"
REPORT_NAME = "daily_orchestrator_report.json"
INTERVAL_HOURS = 24

TASKS = [
    {"id": "github-scout", "module": "github_scout", "func": "run",
     "label": "استطلاع غيت هاب"},
    {"id": "doctor", "module": "doctor_agent", "func": "run",
     "label": "الطبيب اللي كيصلّح"},
    {"id": "rea", "module": "rea_agent", "func": "run",
     "label": "الهندسة العكسية"},
    {"id": "learning", "module": "learning_agent", "func": "learn",
     "label": "وكيل التعلّم"},
    {"id": "conversation-report", "module": "conversation_report_agent", "func": "run",
     "label": "وكيل التقارير فـ Atulya"},
]

_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret|authorization|bearer)"
    r"(\s*[=:]\s*)([^\s,;\"'}\]]{2,})"
)


def _scrub(value: object) -> str:
    text = str(value or "")
    text = _SECRET.sub(lambda m: f"{m.group(1)}{m.group(2)}<redacted>", text)
    return text[:200]


def _stamp(now: Optional[datetime]) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _read_report(state_dir: Path) -> Optional[dict]:
    path = Path(state_dir) / REPORT_NAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _write_report(state_dir: Path, report: dict) -> None:
    state = Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)
    path = state / REPORT_NAME
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _default_runners() -> Dict[str, Callable[[Path], dict]]:
    runners: Dict[str, Callable[[Path], dict]] = {}
    for task in TASKS:
        module_name, func_name = task["module"], task["func"]
        task_id = task["id"]

        def runner(state_dir: Path, _module=module_name, _func=func_name) -> dict:
            module = importlib.import_module(_module)
            return getattr(module, _func)(state_dir)

        runners[task_id] = runner
    return runners


def run_once(state_dir=DEFAULT_STATE_DIR, *, runners: Optional[dict] = None,
             now: Optional[datetime] = None) -> dict:
    calls = dict(runners) if runners is not None else _default_runners()
    rows = []
    for task in TASKS:
        task_id = task["id"]
        try:
            result = calls[task_id](Path(state_dir)) or {}
            ok = bool(result.get("ok", True))
            status = str(result.get("status") or ("live_verified" if ok else "partial"))
            detail = result.get("next") or result.get("reason") or task["label"]
        except Exception as exc:  # un agent en panne ne bloque pas les autres
            ok, status = False, "failed"
            detail = f"{type(exc).__name__}: agent local indisponible"
        rows.append({"id": task_id, "label": task["label"], "ok": ok,
                     "status": status, "detail": _scrub(detail)})

    succeeded = [row for row in rows if row["ok"]]
    status = "live_verified" if len(succeeded) == len(rows) else (
        "partial" if succeeded else "no_data_source")
    report = {
        "ok": len(succeeded) == len(rows),
        "status": status,
        "checked_at": _stamp(now),
        "tasks": rows,
        "next": "Prochaine passe dans 24 h ; aucun commit, push ni redémarrage automatique.",
    }
    _write_report(state_dir, report)
    return report


def due(state_dir=DEFAULT_STATE_DIR, *, now: Optional[datetime] = None,
        interval_hours: int = INTERVAL_HOURS) -> bool:
    report = _read_report(Path(state_dir))
    if not report:
        return True
    raw = str(report.get("checked_at") or "")
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return True
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return (reference - stamp) >= timedelta(hours=interval_hours)


def run_due(state_dir=DEFAULT_STATE_DIR, *, runners: Optional[dict] = None,
            now: Optional[datetime] = None,
            interval_hours: int = INTERVAL_HOURS) -> dict:
    if not due(state_dir, now=now, interval_hours=interval_hours):
        return {"ran": False, "report": _read_report(Path(state_dir)) or {}}
    return {"ran": True, "report": run_once(state_dir, runners=runners, now=now)}


def _say(text: str) -> None:
    stream = sys.stdout
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        try:
            buffer.write((text + "\n").encode("utf-8"))
            buffer.flush()
            return
        except Exception:
            pass
    try:
        stream.write(text + "\n")
    except UnicodeEncodeError:
        stream.write(text.encode("ascii", "backslashreplace") + "\n")


def main(state_dir=DEFAULT_STATE_DIR, *, now: Optional[datetime] = None) -> None:
    result = run_due(state_dir, now=now)
    report = result["report"]
    tasks = report.get("tasks") or []
    summary = "، ".join(f"{row['id']}:{row['status']}" for row in tasks)
    _say(f"الجولة اليومية: {report.get('status', 'no_data_source')} — {summary}")


if __name__ == "__main__":
    main()
