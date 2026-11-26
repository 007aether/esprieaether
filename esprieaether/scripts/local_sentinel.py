#!/usr/bin/env python3
"""Sentinelle locale des agents — lecture seule, loopback, stdlib uniquement.

Dérivé de l'idée de oujnit/jarvis-sentinel (détection processus + croissance
des fichiers de session), réécrit pour Windows et pour la pile ESPRIEATHER.
Aucun appel réseau sortant, aucune clé, aucun contrôle d'exécution.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path.home()
ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("ESPRIE_SENTINEL_PORT", "8766"))
HOST = "127.0.0.1"
APPDATA = Path(os.getenv("APPDATA", HOME / "AppData" / "Roaming")) if os.name == "nt" else HOME / ".config"
LOCALAPPDATA = Path(os.getenv("LOCALAPPDATA", HOME / "AppData" / "Local")) if os.name == "nt" else HOME / ".local" / "share"
FRELLM_HOME = APPDATA / "FreeLLMAPI"
CLAUDE_CODE_HOME = LOCALAPPDATA / "Claude-3p" / "claude-code"
if not CLAUDE_CODE_HOME.exists():
    CLAUDE_CODE_HOME = HOME / ".claude"
CLAUDE_SESSIONS = LOCALAPPDATA / "Claude-3p" / "claude-code-sessions"
SHARE_LEDGER = ROOT / "state" / "model_share.jsonl"
SHARE_CONSUMERS = ("atulya", "claude_code")

# Un agent = (1) un processus reconnaissance, (2) une empreinte de fichiers locaux.
# Les motifs évitent les simples chemins (ex. "Documents\Codex") pour ne pas
# compter un shell comme une activité d'agent.
TOOLS = {
    "opencode": {
        "label": "OPENCODE",
        "home": HOME / ".local" / "share" / "opencode",
        "proc_in": [r"(?i)[\\/]opencode(?:\.exe)?\b", r"(?i)\bopencode\.exe\b"],
        "proc_ex": [r"(?i)opencodex", r"(?i)local_sentinel"],
        "signals": [
            (HOME / ".local" / "share" / "opencode", "log/*.log"),
            (HOME / ".local" / "share" / "opencode", "shell/*/*.out"),
            (HOME / ".local" / "share" / "opencode", "opencode.db-wal"),
        ],
    },
    "codex": {
        "label": "CODEX",
        "home": HOME / ".codex",
        "proc_in": [
            r"(?i)[\\/]codex\.exe\b",
            r"(?i)codex-code-mode-host",
            r"(?i)openai\.chatgpt-[^ ]*[\\/]codex\b",
            r"(?i)[\\/]codex[\\/]bin[\\/]codex",
        ],
        "proc_ex": [r"(?i)codexbar", r"(?i)local_sentinel"],
        "signals": [
            (HOME / ".codex", "sessions/**/*.jsonl"),
            (HOME / ".codex", ".codex-global-state.json"),
        ],
    },
    "freellmapi": {
        "label": "FRELLMAPI",
        "home": FRELLM_HOME,
        "proc_in": [r"(?i)[\\/]FreeLLMAPI(?:\.exe)?\b"],
        "proc_ex": [r"(?i)local_sentinel"],
        "signals": [
            (FRELLM_HOME, "logs/freeapi.log"),
            (FRELLM_HOME, "freeapi.db-wal"),
            (FRELLM_HOME, "DIPS-wal"),
        ],
    },
    "claude": {
        "label": "CLAUDE CODE",
        "home": CLAUDE_CODE_HOME,
        "proc_in": [
            r"(?i)[\\/]claude(?:\.exe)?\b",
            r"(?i)[\\/]claude-code[\\/]",
            r"(?i)[\\/]claude-code-vm[\\/]",
            r"(?i)@anthropic-ai[\\/]claude-code",
        ],
        "proc_ex": [
            r"(?i)[\\/]WindowsApps[\\/]Claude",
            r"(?i)[\\/]Claude-3p[\\/]app[\\/]Claude\.exe",
            r"(?i)--restarted-by-app",
            r"(?i)--type=(crashpad-handler|gpu-process|renderer|utility)",
            r"(?i)claude-code-syntax",
            r"(?i)local_sentinel",
        ],
        "signals": [
            (HOME / ".claude", "sessions/**/*.jsonl"),
            (HOME / ".claude", "projects/*/*.jsonl"),
            (HOME / ".claude", "history.jsonl"),
            (CLAUDE_SESSIONS, "**/*.jsonl"),
        ],
    },
    "atulya": {
        "label": "ATULYA",
        "home": ROOT / "state" / "atulya",
        "proc_in": [r"(?i)\batulya(?:\.cli)?\b"],
        "proc_ex": [r"(?i)local_sentinel"],
        "signals": [
            (ROOT / "state" / "atulya", "operations.sqlite3"),
            (ROOT / "state" / "atulya", "operations.sqlite3-wal"),
            (ROOT / "state" / "atulya", "conversations.sqlite3"),
            (ROOT / "state" / "atulya", "conversations.sqlite3-wal"),
            (ROOT / "state" / "atulya", "lessons.json"),
            (ROOT / "state" / "atulya", "briefings.json"),
            (ROOT / "state" / "atulya", "novel_tasks.jsonl"),
        ],
    },
}
for cfg in TOOLS.values():
    cfg["proc_in"] = [re.compile(p) for p in cfg["proc_in"]]
    cfg["proc_ex"] = [re.compile(p) for p in cfg["proc_ex"]]

# Windows: WMI donne la ligne de commande complète. Le script reste muet et local.
PROC_SCRIPT = (
    "$ErrorActionPreference='SilentlyContinue';"
    "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine } | "
    "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress -Depth 2"
)

LOCK = threading.Lock()
LAST_ACTIVE = {key: 0.0 for key in TOOLS}
STATE = {
    "ts": 0,
    "source": "local_sentinel",
    "host": "windows" if os.name == "nt" else "posix",
    "cpu_measured": False,
    "tools": {},
    "summary": {},
    "share": {},
}


def read_share() -> dict:
    """Part réelle des requêtes, lue dans un journal local sans secret."""
    counts = {key: 0 for key in SHARE_CONSUMERS}
    failed = {key: 0 for key in SHARE_CONSUMERS}
    updated = None
    try:
        lines = SHARE_LEDGER.read_text(encoding="utf-8").splitlines()[-5000:]
    except OSError:
        lines = []
    for line in lines:
        try:
            entry = json.loads(line)
        except (ValueError, TypeError):
            continue
        consumer = entry.get("consumer")
        if consumer not in counts:
            continue
        counts[consumer] += 1
        if not entry.get("ok", True):
            failed[consumer] += 1
        updated = entry.get("ts") or updated
    total = sum(counts.values())
    if total:
        shares = {key: round(counts[key] * 100 / total, 1) for key in SHARE_CONSUMERS}
    else:
        try:
            atulya = max(0, min(100, int(os.getenv("FREELLMAPI_SHARE_ATULYA", "60"))))
        except ValueError:
            atulya = 60
        shares = {"atulya": atulya, "claude_code": 100 - atulya}
    return {
        "source": "local_share_ledger",
        "counts": counts,
        "failed": failed,
        "shares": shares,
        "total": total,
        "updated_at": updated,
    }


def match_command(command: str) -> set[str]:
    """Renvoie les agents dont la ligne de commande correspond, hors exclusions."""
    found = set()
    for key, cfg in TOOLS.items():
        if any(p.search(command) for p in cfg["proc_ex"]):
            continue
        if any(p.search(command) for p in cfg["proc_in"]):
            found.add(key)
    return found


def scan_processes() -> dict[str, int]:
    """Compte les processus par agent. Aucune mesure CPU n'est inventée."""
    stats = {key: 0 for key in TOOLS}
    try:
        if os.name == "nt":
            raw = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", PROC_SCRIPT],
                capture_output=True, text=True, timeout=4,
            ).stdout
            rows = json.loads(raw) if raw.strip() else []
        else:
            raw = subprocess.run(
                ["ps", "aux"], capture_output=True, text=True, timeout=3,
            ).stdout
            rows = [{"CommandLine": line.split(None, 10)[-1]}
                    for line in raw.splitlines()[1:] if len(line.split(None, 10)) > 10]
    except (OSError, ValueError, subprocess.SubprocessError):
        return stats
    if isinstance(rows, dict):
        rows = [rows]
    shells = {"powershell.exe", "pwsh.exe", "cmd.exe", "conhost.exe"}
    for row in rows:
        if not isinstance(row, dict):
            continue
        # Un shell qui affiche un chemin d'agent n'est pas l'agent lui-même.
        if str(row.get("Name") or "").lower() in shells:
            continue
        for key in match_command(str(row.get("CommandLine") or "")):
            stats[key] += 1
    return stats


def snapshot_signals() -> dict[str, dict[str, tuple[int, int]]]:
    """Empreinte (mtime_ns, taille) des fichiers de session locaux."""
    result = {}
    for key, cfg in TOOLS.items():
        files = {}
        for base, pattern in cfg["signals"]:
            if not base.exists():
                continue
            try:
                for item in base.glob(pattern):
                    try:
                        st = item.stat()
                        files[str(item)] = (st.st_mtime_ns, st.st_size)
                    except OSError:
                        pass
            except OSError:
                pass
        result[key] = files
    return result


def diff_snapshots(previous, current) -> dict[str, int]:
    """Compte les fichiers nouveaux/modifiés. Premier passage = 0 activité."""
    if previous is None:
        return {key: 0 for key in current}
    return {
        key: sum(1 for path, stamp in current.get(key, {}).items()
                 if previous.get(key, {}).get(path) != stamp)
        for key in current
    }


def decay(level: float, changed: int) -> float:
    """Activité événementielle à décroissance exponentielle, bornée à 1."""
    return round(min(1.0, level * 0.80 + changed * 0.45), 3)


def classify(level: float, procs: int, installed: bool) -> str:
    """Quatre états honnêtes : active / running / offline / absent."""
    if level >= 0.08:
        return "active"
    if procs > 0:
        return "running"
    return "offline" if installed else "absent"


def collector(interval: float = 1.0) -> None:
    previous = None
    levels = {key: 0.0 for key in TOOLS}
    procs = {key: 0 for key in TOOLS}
    last_proc_scan = 0.0
    while True:
        now = time.time()
        if now - last_proc_scan >= 3.0:
            procs = scan_processes()
            last_proc_scan = now
        current = snapshot_signals()
        changed = diff_snapshots(previous, current)
        previous = current
        share = read_share()
        tools = {}
        for key, cfg in TOOLS.items():
            events = changed.get(key, 0)
            levels[key] = decay(levels[key], events)
            if events > 0:
                LAST_ACTIVE[key] = now
            tools[key] = {
                "label": cfg["label"],
                "installed": cfg["home"].exists(),
                "state": classify(levels[key], procs.get(key, 0), cfg["home"].exists()),
                "procs": procs.get(key, 0),
                "level": levels[key],
                "lastActive": LAST_ACTIVE[key],
                "events": events,
            }
            if key == "freellmapi":
                tools[key]["share"] = share["shares"]["atulya"]
                tools[key]["shareLabel"] = "حصة JARVIS"
            if key == "claude":
                tools[key]["share"] = share["shares"]["claude_code"]
                tools[key]["shareLabel"] = "حصة CLAUDE"
        summary = {
            "active": sum(1 for t in tools.values() if t["state"] == "active"),
            "running": sum(1 for t in tools.values() if t["state"] == "running"),
            "offline": sum(1 for t in tools.values() if t["state"] == "offline"),
            "absent": sum(1 for t in tools.values() if t["state"] == "absent"),
            "level": round(sum(t["level"] for t in tools.values()) / max(1, len(tools)), 3),
        }
        with LOCK:
            STATE["ts"] = now
            STATE["tools"] = tools
            STATE["summary"] = summary
            STATE["share"] = share
        time.sleep(interval)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            with LOCK:
                payload = dict(STATE)
            self._send(200, {"status": "ok", "source": payload["source"],
                             "ts": payload["ts"], "summary": payload["summary"],
                             "share": payload.get("share", {})})
            return
        if self.path.startswith("/events"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            try:
                while True:
                    with LOCK:
                        frame = json.dumps(STATE)
                    self.wfile.write(("data: " + frame + "\n\n").encode("utf-8"))
                    self.wfile.flush()
                    time.sleep(1)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            return
        if self.path in ("/", "/index.html"):
            with LOCK:
                self._send(200, {"source": "local_sentinel", "endpoints": ["/health", "/events"]})
            return
        self._send(404, {"error": "not_found"})

    def log_message(self, *args) -> None:
        return


def main() -> None:
    threading.Thread(target=collector, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    print("JARVIS sentinel local -> http://%s:%d (health /health, flux /events)" % (HOST, PORT))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("sentinel stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
