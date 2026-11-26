"""J129 — pont GSM local en lecture seule.

Les 20 téléphones Samsung S8 sont branchés en USB et exposés par ``adb.exe``.
Ce module ne fait QUE lire : il n'envoie ni SMS, ni appel, ni commande
d'écriture sur les appareils, et ne contacte aucun service distant.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = BASE_DIR / "state"
DEFAULT_ADB = Path(
    os.environ.get(
        "ESPRIE_GSM_ADB",
        r"C:\Program Files (x86)\panda_android\tools\adb.exe",
    )
)
READ_ONLY_TAIL = frozenset({"devices", "-l", "shell", "getprop", "dumpsys", "battery"})
PROP_KEYS = (
    "ro.product.model",
    "gsm.sim.state",
    "gsm.network.type",
    "gsm.operator.alpha",
    "gsm.operator.numeric",
)
TTL_DAYS = 7
Runner = Callable[[List[str], int], str]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def adb_path(explicit: Union[str, Path, None] = None) -> Optional[Path]:
    """Résout l'adb local, sans jamais télécharger quoi que ce soit."""
    if explicit is not None:
        path = Path(explicit)
        return path if path.is_file() else None
    for candidate in (DEFAULT_ADB, shutil.which("adb")):
        if not candidate:
            continue
        path = Path(candidate)
        if path.is_file():
            return path
    return None


def _run(argv: List[str], timeout: int, runner: Optional[Runner]) -> str:
    if runner is not None:
        return runner(argv, timeout)
    if not set(argv[3:]).issubset(READ_ONLY_TAIL):
        raise RuntimeError("commande adb non autorisée (lecture seule)")
    proc = subprocess.run(
        argv, capture_output=True, text=True, errors="replace", timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip()[:300] or "adb a échoué")
    return proc.stdout


def parse_devices(text: str) -> List[dict]:
    rows = []
    for line in text.splitlines():
        match = re.match(r"^(\S+)\s+(device|offline|unauthorized|recovery|sideload)\b\s*(.*)$", line.strip())
        if not match:
            continue
        serial, state, tail = match.groups()
        pairs = dict(re.findall(r"([a-z_]+):(\S+)", tail))
        rows.append({
            "serial": serial,
            "state": state,
            "model": pairs.get("model", ""),
            "product": pairs.get("product", ""),
        })
    return rows


def parse_props(text: str) -> Dict[str, str]:
    found = {}
    for line in text.splitlines():
        match = re.match(r"^\[([^\]]+)\]: \[(.*)\]$", line.strip())
        if match:
            found[match.group(1)] = match.group(2)
    return found


def parse_battery(text: str) -> dict:
    level = re.search(r"^\s*level:\s*(\d+)\s*$", text, re.MULTILINE)
    usb = re.search(r"^\s*USB powered:\s*true\s*$", text, re.MULTILINE | re.IGNORECASE)
    return {
        "level": int(level.group(1)) if level else None,
        "usb_powered": bool(usb),
    }


def device_status(adb: Path, serial: str, runner: Optional[Runner] = None) -> dict:
    base = [str(adb), "-s", serial, "shell"]
    props = parse_props(_run(base + ["getprop"], 8, runner))
    battery = parse_battery(_run(base + ["dumpsys", "battery"], 8, runner))
    return {
        "serial": serial,
        "model": props.get("ro.product.model", ""),
        "sim_state": props.get("gsm.sim.state", ""),
        "network": props.get("gsm.network.type", ""),
        "operator": props.get("gsm.operator.alpha", ""),
        "battery_level": battery["level"],
        "usb_powered": battery["usb_powered"],
    }


def scan(
    state_dir: Union[str, Path, None] = None,
    adb: Union[str, Path, None] = None,
    runner: Optional[Runner] = None,
) -> dict:
    """Lit l'état des téléphones et écrit une preuve locale datée de 7 jours."""
    directory = Path(state_dir) if state_dir is not None else DEFAULT_STATE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    checked = _utcnow()
    device_list = adb_path(adb)
    errors: List[str] = []
    online = 0
    discovered = 0
    statuses: List[dict] = []

    if device_list is None:
        errors.append("adb introuvable (ESPRIE_GSM_ADB)")
        status, ok = "not_available", False
    else:
        try:
            rows = parse_devices(_run([str(device_list), "devices", "-l"], 10, runner))
            discovered = len(rows)
            ready = [row for row in rows if row["state"] == "device"]
            online = len(ready)
            for row in ready:
                try:
                    statuses.append(device_status(device_list, row["serial"], runner))
                except Exception as exc:  # un appareil en panne ne bloque pas les autres
                    errors.append(f"{row['serial']}: {type(exc).__name__}")
            if online == 0:
                status, ok = "needs_user_data", False
            elif errors:
                status, ok = "implemented_unverified", bool(statuses)
            else:
                status, ok = "live_verified", True
        except Exception as exc:
            errors.append(f"adb: {type(exc).__name__}")
            status, ok = "not_available", False

    report = {
        "ok": ok,
        "status": status,
        "engine": "local_only",
        "readOnly": True,
        "checkedAt": _stamp(checked),
        "expiresAt": _stamp(checked + timedelta(days=TTL_DAYS)),
        "adb": str(device_list) if device_list else None,
        "discovered": discovered,
        "online": online,
        "devices": statuses,
        "errors": errors,
        "next": "Relancer en lecture seule ; aucune commande SMS/appel n'est autorisée ici.",
    }
    target = directory / "gsm_status.json"
    tmp = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return report


def main() -> None:
    report = scan()
    print(json.dumps({
        "status": report["status"],
        "online": report["online"],
        "errors": report["errors"],
        "checkedAt": report["checkedAt"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
