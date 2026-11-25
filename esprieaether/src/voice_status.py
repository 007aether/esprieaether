"""J64 — état vocal temps réel, public et sans secret.

Le daemon vocal écrit ici les étapes ``listening / thinking / speaking / idle``
pour que le visage local puisse bouger en synchronie. Le fichier est petit,
atomique, lisible par l'API : aucun texte parlé, aucune clé, aucun en-tête.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

import run_store

BASE_DIR = Path(__file__).resolve().parents[1]
STAGES = ("idle", "listening", "thinking", "speaking")
STATUS_PATH = Path(
    os.getenv("SUNNAVOK_VOICE_STATUS", str(BASE_DIR / "state" / "voice_status.json"))
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _empty(reason: str = "no_data_source") -> dict:
    return {
        "stage": "idle", "level": 0.0, "updatedAt": None,
        "reason": reason,
    }


def write(
    stage: str,
    level: float = 0.0,
    reason: Optional[str] = None,
    path: Union[str, Path, None] = None,
) -> dict:
    """Écrit un état borné et masqué, sans laisser de fichier temporaire."""
    name = str(stage or "idle").lower()
    if name not in STAGES:
        name = "idle"
    try:
        value = round(max(0.0, min(1.0, float(level or 0.0))), 2)
    except (TypeError, ValueError):
        value = 0.0
    payload = {
        "stage": name,
        "level": value,
        "updatedAt": _now(),
        "reason": run_store.redact(reason)[:160] if reason else None,
    }
    target = Path(path) if path else STATUS_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".voice_status-", suffix=".json",
                               dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp, target)
    except Exception:
        try:
            Path(tmp).unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return payload


def read(path: Union[str, Path, None] = None) -> dict:
    """Lit l'état ; un fichier absent ou corrompu reste `no_data_source`."""
    target = Path(path) if path else STATUS_PATH
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return _empty()
    if not isinstance(data, dict) or data.get("stage") not in STAGES:
        return _empty("invalid_status")
    try:
        level = round(max(0.0, min(1.0, float(data.get("level") or 0.0))), 2)
    except (TypeError, ValueError):
        level = 0.0
    return {
        "stage": data["stage"],
        "level": level,
        "updatedAt": data.get("updatedAt"),
        "reason": data.get("reason"),
    }


__all__ = ["STAGES", "STATUS_PATH", "write", "read"]
