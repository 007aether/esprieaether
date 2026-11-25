#!/usr/bin/env python3
"""
orchestrator_agent.py — MASTER AGENT: the brain that runs everything

WHAT: A single daemon that sits above the whole EsprieAether stack and
orchestrates it. It is the "conductor" — every other service/agent reports
to it, and it decides what runs when.

The ONE thing it does every 60s:
  1. SWEEP all services (12 ports) — who's up/down
  2. SWEEP all daemons — who's alive
  3. READ the mesh board — what did the agents say
  4. READ the vector memory — what do we know
  5. DECIDE — trigger a mesh cycle, wake JARVIS, run a Sunna task,
     or stay quiet (everything healthy)
  6. REPORT — write data/orchestrator_state.json + optional Telegram digest

WHY one orchestrator:
  - supervisor.ps1 starts processes, but doesn't coordinate them
  - watchdog restarts dead services, but doesn't decide what to DO
  - autonomous_loop runs scheduled tasks, but doesn't adapt
  - THIS is the adaptive brain: it looks at the whole system state
    and picks the highest-value action each minute

Does NOT replace: supervisor (process launch), watchdog (health restart),
autonomous_loop (scheduled tasks). It ADDS the decision layer on top.

Usage:
  python orchestrator_agent.py              # daemon (60s loop)
  python orchestrator_agent.py --once       # one sweep, print report, exit
  python orchestrator_agent.py --telegram   # print Telegram status
"""

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "data" / "orchestrator_state.json"
LOG_FILE = BASE_DIR / "data" / "logs" / "orchestrator_agent.log"

# ── the full system map ──────────────────────────────────────────────
# name -> (port, health_path)
SERVICES = {
    "router":        (11435, "/v1/models"),
    "mesh":          (11437, "/health"),
    "web":           (5000,  "/health"),
    "cloud-desktop": (5001,  "/health"),
    "sunna":         (5100,  "/health"),
    "integrations":  (5102,  "/health"),
    "kanban":        (5103,  "/health"),
    "homedock":      (5104,  "/health"),
    "jarvis-api":    (8000,  "/api/health"),
    "jarvis-fe":     (3000,  "/"),
    "ollama":        (11434, "/api/tags"),
    "governor":      (11123, "/"),   # MCP: 500 = alive
}

# daemons = python processes that must keep running
DAEMONS = ["bot.py", "watchdog.py", "autonomous_loop.py",
           "cloud_poller.py", "guardian_agent.py", "vpn_agent.py"]

# mesh agents (informational)
MESH_API = "http://127.0.0.1:11437"
JARVIS_API = "http://127.0.0.1:8000"

CYCLE_SECONDS = 60

logger = logging.getLogger("orchestrator_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


# ── helpers ──────────────────────────────────────────────────────────
def http_get(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status
    except Exception:
        return 0


def http_json(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:
        return None


def daemon_alive(script):
    """Is a .venv python process running this script? (Windows-safe)."""
    try:
        import subprocess
        cmd = ('powershell -NoProfile -Command "Get-CimInstance Win32_Process '
               f'-Filter \\"Name=\'python.exe\'\\" | Where-Object {{ '
               f'$_.CommandLine -like \'*{script}*\' -and $_.CommandLine '
               f'-like \'*\\.venv*\' }} | Measure-Object | ForEach-Object '
               '{ $_.Count }"')
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return int(r.stdout.strip() or 0) > 0
    except Exception:
        return False


# ── the sweep ────────────────────────────────────────────────────────
def sweep_services():
    """Check every service port. Returns {name: code}."""
    out = {}
    for name, (port, path) in SERVICES.items():
        code = http_get(f"http://127.0.0.1:{port}{path}")
        out[name] = code
    return out


def sweep_daemons():
    """Check every daemon. Returns {name: alive_bool}."""
    return {d: daemon_alive(d) for d in DAEMONS}


def read_mesh_board(limit=5):
    """Latest mesh board messages."""
    data = http_json(f"{MESH_API}/board?limit={limit}")
    if data:
        return data.get("messages", []), data.get("total", 0)
    return [], 0


def read_jarvis():
    """JARVIS configured services."""
    data = http_json(f"{JARVIS_API}/api/services")
    if data and isinstance(data, list):
        return len([s for s in data if s.get("configured")])
    return 0


# ── the decision ─────────────────────────────────────────────────────
def decide(services, daemons, board_total):
    """Pick the highest-value action. Returns (action, reason)."""
    down = [n for n, c in services.items() if c == 0]
    dead_daemons = [d for d, a in daemons.items() if not a]

    # priority 1: critical services down → let watchdog handle, but note it
    if "router" in down or "mesh" in down:
        return "critical", f"خدمات حرجة طايحة: {down}"

    # priority 2: a daemon died → orchestrator can nudge (watchdog will restart)
    if dead_daemons:
        return "wake", f"daemons ميتة: {dead_daemons}"

    # priority 3: mesh idle a long time → trigger a cycle
    if board_total < 5:
        return "mesh_cycle", "الmesh خاوي — نtrigger دورة"

    # priority 4: everything healthy
    return "idle", f"كلشي سليم ({len(services)-len(down)}/{len(services)} خدمات، {sum(daemons.values())}/{len(daemons)} daemons)"


def trigger_mesh_cycle():
    """POST /cycle to the mesh (fire and forget-ish)."""
    try:
        req = urllib.request.Request(
            f"{MESH_API}/cycle", data=b"{}", method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status == 200
    except Exception as e:
        logger.warning(f"mesh cycle failed: {e}")
        return False


# ── the report ───────────────────────────────────────────────────────
def build_state(action, reason, services, daemons, board_total, jarvis_configured):
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "reason": reason,
        "services": services,
        "services_up": sum(1 for c in services.values() if c > 0),
        "services_total": len(services),
        "daemons": daemons,
        "daemons_up": sum(1 for a in daemons.values() if a),
        "daemons_total": len(daemons),
        "mesh_board": board_total,
        "jarvis_configured": jarvis_configured,
    }


def save_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def format_telegram(state):
    """Telegram status report."""
    s = state
    lines = [
        "🎛️ *Orchestrator* — حالة النظام الكاملة",
        "",
        f"🖥️ الخدمات: *{s['services_up']}/{s['services_total']}*",
    ]
    down = [n for n, c in s["services"].items() if c == 0]
    if down:
        lines.append(f"❌ طايح: `{', '.join(down)}`")
    lines += [
        "",
        f"⚙️ الـ daemons: *{s['daemons_up']}/{s['daemons_total']}*",
    ]
    dead = [d for d, a in s["daemons"].items() if not a]
    if dead:
        lines.append(f"❌ ميت: `{', '.join(dead)}`")
    lines += [
        "",
        f"🕸️ Mesh board: `{s['mesh_board']}` رسالة",
        f"🧠 JARVIS: `{s['jarvis_configured']}` خدمات مربوطة",
        f"🎬 القرار: *{s['action']}*",
        f"   {s['reason']}",
    ]
    return "\n".join(lines)


# ── the loop ─────────────────────────────────────────────────────────
def once():
    """One sweep + decision + report."""
    services = sweep_services()
    daemons = sweep_daemons()
    board, board_total = read_mesh_board(5)
    jarvis_cfg = read_jarvis()

    action, reason = decide(services, daemons, board_total)
    state = build_state(action, reason, services, daemons, board_total, jarvis_cfg)
    save_state(state)

    logger.info(f"action={action} | services {state['services_up']}/{state['services_total']} "
                f"| daemons {state['daemons_up']}/{state['daemons_total']} | {reason}")

    if action == "mesh_cycle":
        ok = trigger_mesh_cycle()
        logger.info(f"mesh cycle triggered: {'ok' if ok else 'failed'}")

    return state


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--telegram", action="store_true")
    args = ap.parse_args()

    if args.once:
        state = once()
        print(format_telegram(state))
        return

    if args.telegram:
        if STATE_FILE.exists():
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            print(format_telegram(state))
        else:
            print("(no state yet — run --once first)")
        return

    # daemon loop
    logger.info("═" * 50)
    logger.info("Orchestrator Agent — master coordinator")
    logger.info(f"sweep every {CYCLE_SECONDS}s · {len(SERVICES)} services · {len(DAEMONS)} daemons")
    logger.info("═" * 50)

    while True:
        try:
            once()
        except Exception as e:
            logger.error(f"sweep error: {e}")
        time.sleep(CYCLE_SECONDS)


if __name__ == "__main__":
    main()
