#!/usr/bin/env python3
"""J158 — veilleuse GSM locale, en lecture seule.

Elle ne lance un scan ADB que si la preuve locale est absente ou périmée
(7 jours). Elle n'envoie jamais SMS, appel, APK, root ni commande vers le
lanceur USB propriétaire. Un scan réussi remplace ``gsm_status.json`` ;
un échec dégrade le statut et lève ``alert=expired`` sans rien inventer.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import gsm_bridge

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = BASE_DIR / "state"
STATE_FILE = "gsm_status.json"
WATCH_FILE = "gsm_watch.json"
TARGET_DEVICES = 20
TTL_DAYS = gsm_bridge.TTL_DAYS


def _parse(stamp: Any) -> Optional[datetime]:
    if not isinstance(stamp, str):
        return None
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fresh(row: Optional[Dict[str, Any]], now: datetime) -> bool:
    checked = _parse(row.get("checkedAt") or row.get("checked_at")) if row else None
    if checked is None:
        return False
    return checked <= now + timedelta(minutes=5) and now - checked <= timedelta(days=TTL_DAYS)


def refresh(
    state_dir: Optional[Path] = None,
    scan_fn: Optional[Callable[..., Dict[str, Any]]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    directory = Path(state_dir) if state_dir is not None else DEFAULT_STATE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    current = now or datetime.now(timezone.utc)
    path = directory / STATE_FILE
    old: Optional[Dict[str, Any]] = None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        old = raw if isinstance(raw, dict) else None
    except (OSError, ValueError):
        old = None

    fresh = _fresh(old, current)
    refreshed = False
    failure = ""
    gsm = old
    if fresh:
        alert = None
    else:
        try:
            runner = scan_fn or gsm_bridge.scan
            result = runner(state_dir=directory)
            gsm = result if isinstance(result, dict) else old
            refreshed = isinstance(result, dict)
            alert = None if refreshed else ("no_evidence" if old is None else "expired")
        except Exception as exc:  # type du seul détail publié : pas de message brut
            failure = type(exc).__name__
            alert = "expired" if old is not None else "no_evidence"

    gsm = gsm if isinstance(gsm, dict) else {}
    devices = gsm.get("devices") if isinstance(gsm.get("devices"), list) else []
    discovered = gsm.get("discovered")
    if not isinstance(discovered, int):
        discovered = len(devices)
    online = gsm.get("online") if isinstance(gsm.get("online"), int) else 0

    if alert == "expired":
        status = "implemented_unverified"
    elif not gsm:
        status = "needs_user_data"
    else:
        status = str(gsm.get("status") or "needs_user_data")

    watch = {
        "ok": bool(gsm) and alert is None,
        "status": status,
        "readOnly": True,
        "refreshed": refreshed,
        "alert": alert,
        "reason": (f"scan en lecture seule indisponible ({failure})" if failure
                   else ("preuve GSM locale absente" if alert == "no_evidence" else "")),
        "online": online,
        "discovered": discovered,
        "targetDevices": TARGET_DEVICES,
        "targetReached": discovered >= TARGET_DEVICES,
        "simReady": sum(1 for device in devices
                        if isinstance(device, dict)
                        and str(device.get("sim_state") or "").upper() == "READY"),
        "checkedAt": gsm.get("checkedAt") or gsm.get("checked_at"),
        "expiresAt": gsm.get("expiresAt"),
    }
    target = directory / WATCH_FILE
    tmp = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(watch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return watch


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Veilleuse GSM locale en lecture seule")
    parser.add_argument("--once", action="store_true", help="un seul contrôle puis sortie")
    parser.add_argument("--daemon", action="store_true", help="boucle de surveillance")
    parser.add_argument("--interval", type=int, default=900, help="secondes entre deux contrôles")
    args = parser.parse_args(argv)
    while True:
        watch = refresh()
        print(json.dumps({
            "status": watch["status"], "online": watch["online"],
            "discovered": watch["discovered"], "alert": watch["alert"],
            "refreshed": watch["refreshed"],
        }, ensure_ascii=False))
        if not args.daemon or args.once:
            return 0
        time.sleep(max(60, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
