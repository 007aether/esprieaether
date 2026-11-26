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
import sys
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
DEFAULT_ADB_PORT = "5038"
INVENTORY_CMD = (
    "getprop ro.build.version.release; getprop ro.build.version.sdk; "
    "getprop ro.product.cpu.abi; id; free -m | head -2; "
    "df -h /data | tail -1; pm list packages | grep -i termux || true"
)
READ_ONLY_TAIL = frozenset({
    "devices", "-l", "shell", "getprop", "dumpsys", "battery", INVENTORY_CMD,
})
PROP_KEYS = (
    "ro.product.model",
    "gsm.sim.state",
    "gsm.network.type",
    "gsm.operator.alpha",
    "gsm.operator.numeric",
)
THIN_COMMANDS = {
    "status": [INVENTORY_CMD],
    "battery": ["dumpsys", "battery"],
    "props": ["getprop"],
}
THIN_TASKS = tuple(THIN_COMMANDS)
DEFAULT_GATEWAY = os.environ.get("ESPRIE_GSM_GATEWAY", "http://127.0.0.1:31416")
MAX_MODEL_MB = 600
MODEL_TRIAL_FILE = "gsm_model_trial.json"
WORKER_PROBE_FILE = "gsm_workers.json"
DEFAULT_BINARY_DIRS = (
    BASE_DIR.parent / ".tools",
    BASE_DIR / "models",
    BASE_DIR.parent / "GITHUB_IMPORT" / "Atulya-Tantra" / "models" / "runtime" / "llama.cpp",
)
DEFAULT_MODEL_DIRS = (
    BASE_DIR / "models",
    BASE_DIR.parent / "GITHUB_IMPORT" / "Atulya-Tantra" / "models",
)
TTL_DAYS = 7
Runner = Callable[[List[str], int], str]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def adb_port() -> str:
    """Port du serveur ADB local, configurable sans quitter le lecture seule."""
    return os.environ.get("ESPRIE_GSM_ADB_PORT", DEFAULT_ADB_PORT)


def adb_env() -> dict:
    """Environnement des sous-processus adb, sans toucher aux appareils."""
    env = os.environ.copy()
    env["ANDROID_ADB_SERVER_PORT"] = adb_port()
    return env


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
        env=adb_env(),
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip()[:300] or "adb a échoué")
    return proc.stdout


def worker_plan(statuses: List[dict], online: int) -> dict:
    """Plan des 20 téléphones comme endpoints légers du brain local."""
    return {
        "mode": "thin_endpoint",
        "gateway": DEFAULT_GATEWAY,
        "ready": online,
        "readOnly": True,
        "tasks": list(THIN_TASKS),
        "heavyInference": False,
        "next": "Lectures ADB seulement : aucun APK, root, SMS ni appel.",
    }


def dispatch_task(
    adb: Union[str, Path],
    serial: str,
    task: str,
    runner: Optional[Runner] = None,
) -> dict:
    """Exécute une tâche de lecture seule sur un appareil, sans écriture."""
    if task not in THIN_COMMANDS:
        raise ValueError(f"tâche non autorisée: {task}")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", serial):
        raise ValueError("numéro de série invalide")
    device = adb_path(adb)
    if device is None:
        raise RuntimeError("adb introuvable (ESPRIE_GSM_ADB)")
    argv = [str(device), "-s", serial, "shell", *THIN_COMMANDS[task]]
    output = _run(argv, 8, runner)
    return {
        "serial": serial,
        "task": task,
        "output": output.strip()[:2000],
        "readOnly": True,
        "checkedAt": _stamp(_utcnow()),
    }


def _looks_arm64(path: Path) -> bool:
    name = path.name.lower()
    if "arm64" not in name and "aarch64" not in name:
        return False
    try:
        with path.open("rb") as handle:
            return handle.read(4) == b"\x7fELF"
    except OSError:
        return False


def _is_tiny_model(path: Path) -> bool:
    if path.suffix.lower() != ".gguf":
        return False
    try:
        return path.stat().st_size <= MAX_MODEL_MB * 1024 * 1024
    except OSError:
        return False


def _find_file(directories, predicate) -> Optional[Path]:
    for directory in directories:
        root = Path(directory)
        if not root.is_dir():
            continue
        try:
            for path in sorted(root.rglob("*")):
                if path.is_file() and predicate(path):
                    return path
        except OSError:
            continue
    return None


def model_preflight(
    state_dir: Union[str, Path, None] = None,
    binary: Union[str, Path, None] = None,
    model: Union[str, Path, None] = None,
    binary_dirs=None,
    model_dirs=None,
) -> dict:
    """Vérifie localement les fichiers d'un essai on-device, sans téléchargement."""
    directory = Path(state_dir) if state_dir is not None else DEFAULT_STATE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    chosen_binary = Path(binary) if binary else _find_file(
        DEFAULT_BINARY_DIRS if binary_dirs is None else binary_dirs, _looks_arm64)
    chosen_model = Path(model) if model else _find_file(
        DEFAULT_MODEL_DIRS if model_dirs is None else model_dirs, _is_tiny_model)
    if chosen_binary is not None and not _looks_arm64(chosen_binary):
        chosen_binary = None
    if chosen_model is not None and not _is_tiny_model(chosen_model):
        chosen_model = None
    ready = chosen_binary is not None and chosen_model is not None
    reasons = []
    if chosen_binary is None:
        reasons.append("binaire llama.cpp arm64 ELF local absent")
    if chosen_model is None:
        reasons.append(f"GGUF local <= {MAX_MODEL_MB} Mo absent")
    checked = _utcnow()
    report = {
        "ok": False,
        "status": "implemented_unverified" if ready else "needs_user_data",
        "ready": ready,
        "readOnly": True,
        "target": "un seul appareil",
        "checkedAt": _stamp(checked),
        "expiresAt": _stamp(checked + timedelta(days=TTL_DAYS)),
        "binary": str(chosen_binary) if chosen_binary else None,
        "model": str(chosen_model) if chosen_model else None,
        "maxModelMb": MAX_MODEL_MB,
        "reason": "" if ready else "; ".join(reasons),
        "next": "Fournir les fichiers localement, puis benchmarker un seul S8 avant toute généralisation.",
    }
    target = directory / MODEL_TRIAL_FILE
    tmp = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return report


def probe_fleet(
    state_dir: Union[str, Path, None] = None,
    adb: Union[str, Path, None] = None,
    runner: Optional[Runner] = None,
    serials=None,
    tasks=None,
) -> dict:
    """Probe les endpoints légers avec des tâches de lecture seule."""
    directory = Path(state_dir) if state_dir is not None else DEFAULT_STATE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    chosen = tuple(tasks) if tasks is not None else THIN_TASKS
    invalid = [task for task in chosen if task not in THIN_COMMANDS]
    if invalid:
        raise ValueError(f"tâches non autorisées: {', '.join(invalid)}")
    if serials is None:
        source = directory / "gsm_status.json"
        try:
            saved = json.loads(source.read_text(encoding="utf-8"))
            serials = [row["serial"] for row in saved.get("devices", []) if row.get("serial")]
        except (OSError, ValueError, TypeError):
            serials = []
    samples: List[dict] = []
    errors: List[str] = []
    succeeded = 0
    for serial in serials:
        for task in chosen:
            try:
                result = dispatch_task(adb, serial, task, runner)
                succeeded += 1
                if len(samples) < 4:
                    samples.append({
                        "serial": result["serial"],
                        "task": result["task"],
                        "output": result["output"],
                        "readOnly": result["readOnly"],
                    })
            except Exception as exc:  # un appareil en panne ne bloque pas les autres
                errors.append(f"{serial}:{task}:{type(exc).__name__}")
    if not serials:
        status, ok = "needs_user_data", False
    elif errors and succeeded:
        status, ok = "implemented_unverified", False
    elif errors:
        status, ok = "not_available", False
    else:
        status, ok = "live_verified", True
    checked = _utcnow()
    report = {
        "ok": ok,
        "status": status,
        "readOnly": True,
        "mode": "thin_endpoint",
        "gateway": DEFAULT_GATEWAY,
        "online": len(serials),
        "succeeded": succeeded,
        "tasks": list(chosen),
        "samples": samples,
        "errors": errors,
        "checkedAt": _stamp(checked),
        "expiresAt": _stamp(checked + timedelta(days=TTL_DAYS)),
        "next": "Relancer la sonde en lecture seule ; aucun APK, root, SMS ni appel.",
    }
    target = directory / WORKER_PROBE_FILE
    tmp = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return report


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


def _size_gb(value: str) -> Optional[float]:
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([GMK])", value.strip())
    if not match:
        return None
    number = float(match.group(1))
    return number / 1024 if match.group(2) == "M" else number / (1024 * 1024) if match.group(2) == "K" else number


def parse_inventory(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    def at(index: int) -> str:
        return lines[index] if index < len(lines) else ""

    memory = next((line for line in lines if line.startswith("Mem:")), "")
    parts = memory.split()
    free_mb = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None
    data_line = next((line for line in lines if line.rstrip().endswith("/data")), "")
    data_parts = data_line.split()
    storage_gb = _size_gb(data_parts[3]) if len(data_parts) > 3 else None
    return {
        "android": at(0),
        "sdk": at(1),
        "abi": at(2),
        "root": at(3).startswith("uid=0("),
        "free_mb": free_mb,
        "storage_gb": storage_gb,
        "termux": "termux" in text.lower(),
    }


def device_status(adb: Path, serial: str, runner: Optional[Runner] = None) -> dict:
    base = [str(adb), "-s", serial, "shell"]
    props = parse_props(_run(base + ["getprop"], 8, runner))
    battery = parse_battery(_run(base + ["dumpsys", "battery"], 8, runner))
    inventory = parse_inventory(_run(base + [INVENTORY_CMD], 8, runner))
    return {
        "serial": serial,
        "model": props.get("ro.product.model", ""),
        "sim_state": props.get("gsm.sim.state", ""),
        "network": props.get("gsm.network.type", ""),
        "operator": props.get("gsm.operator.alpha", ""),
        "battery_level": battery["level"],
        "usb_powered": battery["usb_powered"],
        **inventory,
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
    adb_states = {"device": 0, "offline": 0, "unauthorized": 0}
    statuses: List[dict] = []

    if device_list is None:
        errors.append("adb introuvable (ESPRIE_GSM_ADB)")
        status, ok = "not_available", False
    else:
        try:
            rows = parse_devices(_run([str(device_list), "devices", "-l"], 10, runner))
            discovered = len(rows)
            for row in rows:
                if row["state"] in adb_states:
                    adb_states[row["state"]] += 1
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

    androids = [row["android"] for row in statuses if row.get("android")]
    abis = [row["abi"] for row in statuses if row.get("abi")]
    free_values = [row["free_mb"] for row in statuses if isinstance(row.get("free_mb"), int)]
    storage_values = [row["storage_gb"] for row in statuses if isinstance(row.get("storage_gb"), (int, float))]
    summary = {
        "android": max(set(androids), key=androids.count) if androids else None,
        "abi": max(set(abis), key=abis.count) if abis else None,
        "root_count": sum(1 for row in statuses if row.get("root")),
        "termux_count": sum(1 for row in statuses if row.get("termux")),
        "free_mb_min": min(free_values) if free_values else None,
        "storage_gb_min": min(storage_values) if storage_values else None,
    }
    report = {
        "ok": ok,
        "status": status,
        "engine": "local_only",
        "readOnly": True,
        "checkedAt": _stamp(checked),
        "expiresAt": _stamp(checked + timedelta(days=TTL_DAYS)),
        "adb": str(device_list) if device_list else None,
        "adbPort": adb_port(),
        "adbStates": adb_states,
        "discovered": discovered,
        "online": online,
        "devices": statuses,
        **summary,
        "worker": worker_plan(statuses, online),
        "errors": errors,
        "next": "Relancer en lecture seule ; aucune commande SMS/appel n'est autorisée ici.",
    }
    target = directory / "gsm_status.json"
    tmp = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return report


def main() -> None:
    if "--probe" in sys.argv[1:]:
        probe = probe_fleet()
        print(json.dumps({
            "status": probe["status"],
            "online": probe["online"],
            "succeeded": probe["succeeded"],
            "errors": probe["errors"],
            "checkedAt": probe["checkedAt"],
        }, ensure_ascii=False))
        return
    report = scan()
    trial = model_preflight()
    print(json.dumps({
        "status": report["status"],
        "online": report["online"],
        "worker": report["worker"]["mode"],
        "modelTrial": trial["status"],
        "errors": report["errors"],
        "checkedAt": report["checkedAt"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
