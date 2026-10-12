#!/usr/bin/env python3
"""
watchdog.py — 24/7 self-healing for EsprieAether + DSH stack.

Checks every 60s, restarts anything dead:
  - ollama   (11434)
  - router   (11435)  ← Aether AI Router (5 brains + 6 agents)
  - orchestrator (11436) ← 7-agent orchestrator
  - web      (5000)
  - hexstrike(8888)
  - bot      (telegram process)

Logs to ~/ESPRIEAETHER/data/watchdog.log
Restart policy: max 5 restarts per service per 10 min (then wait).
"""

import os
import subprocess
import sys
import time
import urllib.request
from collections import deque
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).parent.parent
HOME = Path(os.path.expanduser("~"))
LOG = HOME / "ESPRIEAETHER" / "data" / "watchdog.log"
OLLAMA_MODELS = "C:/Users/ESPRIEAETHER/.ollama/models"

INTERVAL = 60
MAX_RESTARTS = 5          # per window
WINDOW = 600              # 10 min

# service definitions: name -> (kind, check, restart command)
_PY = sys.executable
OLLAMA_BIN = str(HOME / ".local" / "bin" / "ollama")
HEXPY = str(PROJECT.parent / "hexstrike-ai" / ".venv" / "Scripts" / "python.exe")

SERVICES = {
    "ollama": {
        "kind": "http",
        "url": "http://127.0.0.1:11434/api/tags",
        "cmd": [OLLAMA_BIN, "serve"],
    },
    "router": {
        "kind": "http",
        "url": "http://127.0.0.1:11435/health",
        "cwd": PROJECT,
        "cmd": [_PY, "src/ai_router.py"],
    },
    "orchestrator": {
        "kind": "http",
        "url": "http://127.0.0.1:11436/health",
        "cwd": PROJECT,
        "cmd": [_PY, "src/orchestrator.py"],
    },
    "web": {
        "kind": "http",
        "url": "http://127.0.0.1:5000/health",
        "cwd": PROJECT,
        "cmd": [_PY, "src/web_interface.py"],
    },
    "hexstrike": {
        "kind": "http",
        "url": "http://127.0.0.1:8888/health",
        "cwd": PROJECT.parent / "hexstrike-ai",
        "cmd": [HEXPY, "hexstrike_server.py"],
        "grace": 300,  # very slow startup (process pool + heavy imports)
    },
    "bot": {
        "kind": "process",
        "match": "bot.py",
        "cwd": PROJECT,
        "cmd": [_PY, "src/bot.py"],
    },
}

_restarts = {name: deque() for name in SERVICES}
_last_restart = {name: 0.0 for name in SERVICES}


def log(msg: str):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    print(line, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def http_ok(url: str, timeout: int = 6) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def process_alive(match: str) -> bool:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object {{ $_.CommandLine -like '*{match}*' }} | Measure-Object).Count"],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip() not in ("", "0")
    except Exception:
        return True  # don't restart if we can't check


def restart(name: str, svc: dict) -> bool:
    """Restart a service. Returns False if rate-limited."""
    now = time.time()
    q = _restarts[name]
    while q and now - q[0] > WINDOW:
        q.popleft()
    if len(q) >= MAX_RESTARTS:
        log(f"⛔ {name}: rate-limited ({MAX_RESTARTS} restarts in {WINDOW}s) — waiting")
        return False

    q.append(now)
    cwd = svc.get("cwd") or PROJECT

    kwargs = {
        "cwd": str(cwd),
        "env": {**os.environ, "OLLAMA_MODELS": OLLAMA_MODELS},
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        # CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
        kwargs["creationflags"] = 0x00000200 | 0x00000008
    try:
        subprocess.Popen([str(c) for c in svc["cmd"]], **kwargs)
        log(f"🔄 {name}: restarted ({len(q)}/{MAX_RESTARTS})")
        return True
    except Exception as e:
        log(f"❌ {name}: restart failed: {e}")
        return False


def check_once() -> dict:
    results = {}
    now = time.time()
    for name, svc in SERVICES.items():
        if svc["kind"] == "http":
            alive = http_ok(svc["url"])
        else:
            alive = process_alive(svc["match"])
        results[name] = alive
        if not alive:
            # grace: don't re-restart a slow-starting service mid-startup
            grace = svc.get("grace", 30)
            if now - _last_restart[name] < grace:
                continue
            if restart(name, svc):
                _last_restart[name] = now
    return results


def main():
    log("═" * 50)
    log("🐕 Aether Watchdog started — 24/7 self-healing")
    for name, svc in SERVICES.items():
        kind = svc["kind"]
        log(f"   watching: {name} ({kind})")
    log("═" * 50)

    while True:
        try:
            r = check_once()
            dead = [k for k, v in r.items() if not v]
            if dead:
                log(f"⚠️ dead: {dead} → restart issued")
            else:
                log("✅ all services alive")
        except Exception as e:
            log(f"❌ watchdog error: {e}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
