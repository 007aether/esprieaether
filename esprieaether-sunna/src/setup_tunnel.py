#!/usr/bin/env python3
"""
setup_tunnel.py — SSH reverse tunnel setup (cloud desktop remote access)

Creates a reverse SSH tunnel so this Windows PC can be reached from anywhere:
  ssh -R <remote_port>:localhost:5001 <user>@<host>

Usage:
  python setup_tunnel.py start   — start the tunnel
  python setup_tunnel.py stop    — stop the tunnel
  python setup_tunnel.py status  — show tunnel status
  python setup_tunnel.py config  — show current config

Config (env vars or .env):
  TUNNEL_HOST      — remote SSH host (e.g. your VPS)
  TUNNEL_USER      — SSH username
  TUNNEL_KEY       — path to SSH private key (optional)
  TUNNEL_PORT      — remote port to bind (default 2222)
  TUNNEL_LOCAL_PORT — local port to expose (default 5001, cloud desktop)

State file: ~/ESPRIEAETHER/data/tunnel.json
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

PROJECT = Path(__file__).parent.parent
STATE = Path(os.path.expanduser("~")) / "ESPRIEAETHER" / "data" / "tunnel.json"

TUNNEL_HOST = os.getenv("TUNNEL_HOST", "")
TUNNEL_USER = os.getenv("TUNNEL_USER", "")
TUNNEL_KEY = os.getenv("TUNNEL_KEY", "")
TUNNEL_PORT = int(os.getenv("TUNNEL_PORT", "2222"))
LOCAL_PORT = int(os.getenv("TUNNEL_LOCAL_PORT", "5001"))


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(s: dict):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2), encoding="utf-8")


def tunnel_alive(pid: int) -> bool:
    if not pid:
        return False
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        return "ssh.exe" in out.stdout.lower()
    except Exception:
        return False


def start():
    if not TUNNEL_HOST or not TUNNEL_USER:
        print("❌ TUNNEL_HOST / TUNNEL_USER not set in .env")
        print("   Example:")
        print("     TUNNEL_HOST=myvps.com")
        print("     TUNNEL_USER=root")
        print("     TUNNEL_KEY=C:/Users/ESPRIEAETHER/.ssh/id_rsa")
        print("     TUNNEL_PORT=2222")
        return 1

    state = load_state()
    if state.get("pid") and tunnel_alive(state["pid"]):
        print(f"✅ tunnel already running (pid {state['pid']})")
        return 0

    cmd = ["ssh", "-N", "-R", f"{TUNNEL_PORT}:localhost:{LOCAL_PORT}",
           "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3",
           "-o", "ExitOnForwardFailure=yes"]
    if TUNNEL_KEY:
        cmd += ["-i", TUNNEL_KEY]
    cmd += [f"{TUNNEL_USER}@{TUNNEL_HOST}"]

    print(f"🔗 starting tunnel → {TUNNEL_USER}@{TUNNEL_HOST}:{TUNNEL_PORT}")
    print(f"   local port {LOCAL_PORT} exposed remotely")
    try:
        if os.name == "nt":
            kwargs = {"creationflags": 0x00000200 | 0x00000008}
        else:
            kwargs = {"start_new_session": True}
        proc = subprocess.Popen(cmd, **kwargs)
        save_state({"pid": proc.pid, "started_at": datetime.now().isoformat(),
                    "host": TUNNEL_HOST, "user": TUNNEL_USER, "port": TUNNEL_PORT})
        print(f"✅ tunnel started (pid {proc.pid})")
        return 0
    except Exception as e:
        print(f"❌ failed to start tunnel: {e}")
        return 1


def stop():
    state = load_state()
    if not state.get("pid"):
        print("no tunnel running")
        return 0
    try:
        subprocess.run(["taskkill", "/F", "/PID", str(state["pid"])],
                       capture_output=True, timeout=10)
        print(f"🛑 tunnel stopped (pid {state['pid']})")
    except Exception as e:
        print(f"stop error: {e}")
    save_state({})
    return 0


def status():
    state = load_state()
    if not state:
        print("no tunnel state")
        return 0
    pid = state.get("pid")
    alive = tunnel_alive(pid)
    print(f"   pid:      {pid}")
    print(f"   alive:    {'✅' if alive else '❌'}")
    print(f"   host:     {state.get('user')}@{state.get('host')}")
    print(f"   port:     {state.get('port')} → localhost:{LOCAL_PORT}")
    print(f"   started:  {state.get('started_at')}")
    return 0


def config():
    print("Tunnel config:")
    print(f"  TUNNEL_HOST:      {TUNNEL_HOST or '(not set)'}")
    print(f"  TUNNEL_USER:      {TUNNEL_USER or '(not set)'}")
    print(f"  TUNNEL_KEY:       {TUNNEL_KEY or '(not set)'}")
    print(f"  TUNNEL_PORT:      {TUNNEL_PORT}")
    print(f"  LOCAL_PORT:       {LOCAL_PORT} (cloud desktop)")
    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "start":
        sys.exit(start())
    elif action == "stop":
        sys.exit(stop())
    elif action == "status":
        sys.exit(status())
    elif action == "config":
        sys.exit(config())
    else:
        print(f"usage: python setup_tunnel.py [start|stop|status|config]")
        sys.exit(1)
