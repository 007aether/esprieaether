#!/usr/bin/env python3
"""
watchdog.py — 24/7 self-healing for EsprieAether + DSH stack.

Checks every 60s, restarts anything dead:
  - ollama   (11434)
  - router   (11435)  ← Aether AI Router (5 brains + 6 agents)
  - orchestrator (11436) ← 7-agent orchestrator
  - web      (5000)
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
JARVIS_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "Temp" / "JARVIS_repo" / "backend"
GOVERNOR_DIR = Path(os.environ.get("LOCALAPPDATA", "")) / "Temp" / "new_repos" / "governor-edr"

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
    "cloud-desktop": {
        "kind": "http",
        "url": "http://127.0.0.1:5001/health",
        "cwd": PROJECT,
        "cmd": [_PY, "src/cloud_desktop_agent.py"],
    },
    "traffmonetizer": {
        "kind": "exists",
        "match": "Traffmonetizer",
        "cmd": ["C:\\Users\\ESPRIEAETHER\\AppData\\Roaming\\Traffmonetizer\\app\\Traffmonetizer.exe"],
    },
    "github-desktop": {
        "kind": "exists",
        "match": "GitHubDesktop",
        "cmd": ["C:\\Users\\ESPRIEAETHER\\AppData\\Local\\GitHubDesktop\\app-3.6.7\\GitHubDesktop.exe"],
    },
    "bot": {
        "kind": "process",
        "match": "bot.py",
        "cwd": PROJECT,
        "cmd": [_PY, "src/bot.py"],
    },
    "sunna-api": {
        "kind": "http",
        "url": "http://127.0.0.1:5100/health",
        "cwd": PROJECT,
        "cmd": [_PY, "src/sunna_api.py"],
    },
    "jarvis": {
        "kind": "http",
        "url": "http://127.0.0.1:8000/api/health",
        "cwd": str(JARVIS_DIR),
        "cmd": [str(JARVIS_DIR / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
    },
    "agent-mesh": {
        "kind": "http",
        "url": "http://127.0.0.1:11437/health",
        "cwd": PROJECT,
        "cmd": [_PY, "src/agent_mesh.py"],
    },
    "jarvis-frontend": {
        "kind": "http",
        "url": "http://127.0.0.1:3000/",
        "cwd": str(JARVIS_DIR.parent / "frontend"),
        "cmd": ["cmd.exe", "/c", "npx next dev --port 3000"],
    },
    "integrations": {
        "kind": "http",
        "url": "http://127.0.0.1:5102/health",
        "cwd": PROJECT,
        "cmd": [_PY, "src/integrations_adapter.py"],
    },
    "kanban": {
        "kind": "http",
        "url": "http://127.0.0.1:5103/health",
        "cwd": PROJECT,
        "cmd": [_PY, "src/veritas_kanban.py"],
    },
    "homedock": {
        "kind": "http",
        "url": "http://127.0.0.1:5104/health",
        "cwd": PROJECT,
        "cmd": [_PY, "src/homedock_dashboard.py"],
    },
    "governor-edr": {
        "kind": "http",
        "url": "http://127.0.0.1:11123/",
        "cwd": str(GOVERNOR_DIR),
        "cmd": [_PY, "main.py"],
    },
    # hexstrike intentionally NOT watched: startup takes ~2+ min (process pool +
    # tshark probe) and the watchdog's restart loop kills it mid-startup.
    # Start it manually when needed: cd ../hexstrike-ai && uv run python hexstrike_server.py
}

_restarts = {name: deque() for name in SERVICES}
_last_restart = {name: 0.0 for name in SERVICES}

# ── Scheduled jobs (run at HH:MM, once per day) ──
SUNNA = Path(os.path.expanduser("~")) / "Desktop" / "Sunna-Equipe-Industrial"
SCHEDULE = {
    "sunna-offres": {"hour": 9, "minute": 0, "cwd": SUNNA, "cmd": [_PY, "bots/offres_bot.py"]},
    "sunna-pinterest": {"hour": 20, "minute": 0, "cwd": SUNNA, "cmd": [_PY, "bots/pinterest_bot.py"]},
    "sunna-veille": {"hour": 8, "minute": 30, "cwd": SUNNA, "cmd": [_PY, "bots/veille_bot.py", "run"]},
    "sunna-souk": {"hour": 21, "minute": 0, "cwd": SUNNA, "cmd": [_PY, "bots/souk_bot.py"]},
}
_last_run: dict = {name: None for name in SCHEDULE}  # date string last run
DISK_ALERT_PCT = 80


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


def process_alive(match: str, name: str = "python.exe") -> bool:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-CimInstance Win32_Process -Filter \"Name='{name}'\" | Where-Object {{ $_.CommandLine -like '*{match}*' }} | Measure-Object).Count"],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip() not in ("", "0")
    except Exception:
        return True  # don't restart if we can't check


def process_exists(name: str) -> bool:
    """Check if any process with this exact name is running."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-Process -Name '{name}' -ErrorAction SilentlyContinue | Measure-Object).Count"],
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
        elif svc["kind"] == "exists":
            alive = process_exists(svc["match"])
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
                if name == "traffmonetizer":
                    log("💰 traffmonetizer restarted — earning continues")
    # TraffMonetizer stats snapshot (for earnings tracking)
    if "traffmonetizer" in results and results["traffmonetizer"]:
        try:
            subprocess.run([sys.executable, "src/tm_stats.py", "once"],
                           cwd=str(PROJECT), capture_output=True, timeout=20)
        except Exception:
            pass
    return results


def check_disk():
    """Alert + auto-clean when disk usage exceeds threshold.

    When > 90%, auto-deletes old logs (>3 days) + tmp zips so services
    never die from a full disk again.
    """
    try:
        import shutil
        usage = shutil.disk_usage(str(HOME))
        pct = usage.used / usage.total * 100
        if pct >= DISK_ALERT_PCT:
            log(f"💾 DISK ALERT: {pct:.0f}% used ({usage.used // (2**30)}GB / {usage.total // (2**30)}GB)")
        if pct >= 90:
            log(f"🧹 disk {pct:.0f}% — auto-cleaning old logs + tmp...")
            freed = 0
            # old logs (>3 days)
            for d in [HOME / "ESPRIEAETHER" / "data", PROJECT,
                      HOME / "Desktop" / "Sunna-Equipe-Industrial"]:
                for f in d.rglob("*.log"):
                    try:
                        if f.stat().st_mtime < time.time() - 3 * 86400:
                            freed += f.stat().st_size
                            f.unlink()
                    except Exception:
                        pass
            # tmp archives
            tmp = Path(os.environ.get("LOCALAPPDATA", "")) / "Temp"
            if tmp.exists():
                for f in tmp.glob("*.zip"):
                    try:
                        freed += f.stat().st_size
                        f.unlink()
                    except Exception:
                        pass
                for f in tmp.glob("*.tar.gz"):
                    try:
                        freed += f.stat().st_size
                        f.unlink()
                    except Exception:
                        pass
            u2 = shutil.disk_usage(str(HOME))
            log(f"🧹 freed {freed // (2**20)}MB — disk now {u2.used / u2.total * 100:.0f}%")
    except Exception as e:
        log(f"❌ disk check error: {e}")


def check_schedule():
    """Run scheduled jobs at their HH:MM once per day."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    for name, job in SCHEDULE.items():
        if now.hour == job["hour"] and now.minute == job["minute"]:
            if _last_run[name] == today:
                continue  # already ran today
            _last_run[name] = today
            cwd = job.get("cwd") or PROJECT
            log(f"⏰ running scheduled: {name}")
            try:
                kwargs = {
                    "cwd": str(cwd),
                    "env": {**os.environ, "OLLAMA_MODELS": OLLAMA_MODELS},
                    "stdout": subprocess.DEVNULL,
                    "stderr": subprocess.DEVNULL,
                }
                if os.name == "nt":
                    kwargs["creationflags"] = 0x00000200 | 0x00000008
                subprocess.Popen([str(c) for c in job["cmd"]], **kwargs)
                log(f"✅ scheduled: {name} started")
            except Exception as e:
                log(f"❌ scheduled {name} failed: {e}")


def main():
    log("═" * 50)
    log("🐕 Aether Watchdog started — 24/7 self-healing")
    for name, svc in SERVICES.items():
        kind = svc["kind"]
        log(f"   watching: {name} ({kind})")
    for name, job in SCHEDULE.items():
        log(f"   scheduled: {name} at {job['hour']:02d}:{job['minute']:02d}")
    log(f"   disk alert: {DISK_ALERT_PCT}%")
    log("═" * 50)

    while True:
        try:
            r = check_once()
            dead = [k for k, v in r.items() if not v]
            if dead:
                log(f"⚠️ dead: {dead} → restart issued")
            else:
                log("✅ all services alive")
            check_schedule()
            check_disk()
        except Exception as e:
            log(f"❌ watchdog error: {e}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
