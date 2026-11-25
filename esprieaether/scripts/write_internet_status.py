#!/usr/bin/env python3
"""J57 — sonde Internet publique, stdlib uniquement, sans secret ni clé.

Écrit state/internet_status.json pour le tableau de bord local. Uniquement un
hôte public (pypi.org par défaut) : aucun réseau privé, aucune donnée envoyée.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))
from policy_gate import check_url  # noqa: E402
DEFAULT_OUTPUT = BASE_DIR / "state" / "internet_status.json"
HOST = os.getenv("SUNNAVOK_NET_HOST", "pypi.org")
PORT = int(os.getenv("SUNNAVOK_NET_PORT", "443"))
TIMEOUT = float(os.getenv("SUNNAVOK_NET_TIMEOUT", "4"))


def probe(host: str = HOST, port: int = PORT, timeout: float = TIMEOUT) -> Dict[str, object]:
    """DNS + connexion TCP courte. Aucun secret, aucun contenu téléchargé."""
    checked = datetime.now(timezone.utc).isoformat(timespec="seconds")
    started = time.monotonic()
    base = {"host": str(host), "checkedAt": checked, "mode": "internet"}
    gate = check_url(f"https://{host}:{port}/")
    if not gate.allowed:
        return {**base, "available": False,
                "reason": f"egress_blocked:{gate.reason}", "latencyMs": None}
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return {**base, "available": False, "reason": "dns_failed", "latencyMs": None}

    last_error: Optional[Exception] = None
    for family, socktype, proto, _, address in infos:
        try:
            with socket.socket(family, socktype, proto) as handle:
                handle.settimeout(timeout)
                handle.connect(address)
            latency = int((time.monotonic() - started) * 1000)
            return {**base, "available": True, "reason": None, "latencyMs": latency}
        except OSError as exc:
            last_error = exc
    return {
        **base, "available": False,
        "reason": f"connect_failed:{type(last_error).__name__ if last_error else 'unknown'}",
        "latencyMs": None,
    }


def write_status(path=DEFAULT_OUTPUT, payload: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Écriture atomique, lisible par l'API locale."""
    data = payload if payload is not None else probe()
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(destination)
    return data


if __name__ == "__main__":
    result = write_status()
    print(f"internet={result['available']} host={result['host']} reason={result['reason']}")
