#!/usr/bin/env python3
"""Partage local des requêtes FreeLLMAPI entre JARVIS et Claude Code.

Journal append-only : aucune clé, aucun prompt, aucun contenu de réponse.
Un seul enregistrement par requête : horodatage, consommateur, modèle, succès.
Le fichier reste dans state/ et n'est jamais versionné.
"""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parent.parent / "state"
LEDGER = Path(
    os.getenv("ESPRIE_MODEL_SHARE_LEDGER", str(STATE_DIR / "model_share.jsonl"))
)
CONSUMERS = ("atulya", "claude_code")
MAX_LINES = 5000
_LOCK = threading.Lock()

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def ratio() -> dict[str, int]:
    """Répartition cible, bornée 0–100, sans dépendance externe."""
    try:
        atulya = int(os.getenv("FREELLMAPI_SHARE_ATULYA", "60"))
    except (TypeError, ValueError):
        atulya = 60
    atulya = max(0, min(100, atulya))
    return {"atulya": atulya, "claude_code": 100 - atulya}


def _clean_model(model: object) -> str | None:
    if model is None:
        return None
    text = _CONTROL.sub(" ", str(model)).strip()
    return text[:80] or None


def record(consumer: str, model: object = None, ok: bool = True,
           ledger: Path | None = None) -> bool:
    """Ajoute une ligne au journal. Aucune donnée sensible n'est acceptée."""
    if consumer not in CONSUMERS:
        return False
    target = Path(ledger) if ledger is not None else LEDGER
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "consumer": consumer,
        "model": _clean_model(model),
        "ok": bool(ok),
    }
    line = json.dumps(entry, ensure_ascii=False, sort_keys=True)
    with _LOCK:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
            return True
        except OSError:
            return False


def snapshot(ledger: Path | None = None) -> dict:
    """Compteurs et parts réelles, dérivés du journal local uniquement."""
    target = Path(ledger) if ledger is not None else LEDGER
    counts = {key: 0 for key in CONSUMERS}
    failed = {key: 0 for key in CONSUMERS}
    last_models: dict[str, str | None] = {key: None for key in CONSUMERS}
    updated_at = None
    try:
        lines = target.read_text(encoding="utf-8").splitlines()[-MAX_LINES:]
    except OSError:
        lines = []
    for line in lines:
        try:
            entry = json.loads(line)
        except (ValueError, TypeError):
            continue
        consumer = entry.get("consumer")
        if consumer not in CONSUMERS:
            continue
        counts[consumer] += 1
        if not entry.get("ok", True):
            failed[consumer] += 1
        if entry.get("model"):
            last_models[consumer] = entry["model"]
        updated_at = entry.get("ts") or updated_at
    total = sum(counts.values())
    target_ratio = ratio()
    if total:
        shares = {
            key: round(counts[key] * 100 / total, 1) for key in CONSUMERS
        }
    else:
        shares = dict(target_ratio)
    return {
        "source": "local_share_ledger",
        "ratio": target_ratio,
        "counts": counts,
        "failed": failed,
        "shares": shares,
        "total": total,
        "last_models": last_models,
        "updated_at": updated_at,
        "ledger": target.name,
    }


def choose(snap: dict | None = None) -> str:
    """Consommateur le plus en deficit par rapport a la part cible."""
    current = snap if snap is not None else snapshot()
    target = current["ratio"]
    total = max(1, current["total"])
    deficits = {
        key: target[key] - (current["counts"][key] * 100 / total)
        for key in CONSUMERS
    }
    return max(CONSUMERS, key=lambda key: (deficits[key], -CONSUMERS.index(key)))


__all__ = ["CONSUMERS", "LEDGER", "choose", "ratio", "record", "snapshot"]
