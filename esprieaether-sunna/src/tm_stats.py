#!/usr/bin/env python3
"""
tm_stats.py — TraffMonetizer stats tracker + logger

Reads TM app settings + tracks earnings over time:
  - token status (from settings.json)
  - device ID (from storage.json)
  - uptime (process alive?)
  - connections (outbound)
  - estimated traffic sold (from network delta)

Writes a daily log: ~/ESPRIEAETHER/data/tm_stats.jsonl
Endpoint: /tmstats (JSON) + /tmlog (append)

Usage:
  python tm_stats.py once    — snapshot now
  python tm_stats.py watch   — loop every 5 min
  python tm_stats.py log     — show recent log
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

LOG = Path(os.path.expanduser("~")) / "ESPRIEAETHER" / "data" / "tm_stats.jsonl"
TM_APP = Path(os.environ.get("APPDATA", "")) / "Traffmonetizer"
TM_EXE = TM_APP / "app" / "Traffmonetizer.exe"


def ps(cmd: str) -> str:
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=15,
        ).stdout.strip()
    except Exception:
        return ""


def snapshot() -> dict:
    s = {}
    # settings
    sf = TM_APP / "settings.json"
    if sf.exists():
        try:
            data = json.loads(sf.read_text())
            s["accepting"] = data.get("Accepting")
            s["start_with_windows"] = data.get("StartWithWindows")
            s["token_prefix"] = (data.get("Token", "")[:8] + "...") if data.get("Token") else None
        except Exception:
            pass
    # device id
    df = TM_APP / "storage.json"
    if df.exists():
        try:
            s["device_id"] = json.loads(df.read_text()).get("id")
        except Exception:
            pass
    # process
    s["running"] = ps(f"(Get-Process -Name 'Traffmonetizer*' -ErrorAction SilentlyContinue | Measure-Object).Count") not in ("", "0")
    # connections
    pid = ps("(Get-Process -Name 'Traffmonetizer*' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Id)")
    if pid:
        s["pid"] = int(pid)
        s["connections"] = int(ps(f"(Get-NetTCPConnection -OwningProcess {pid} -ErrorAction SilentlyContinue | Measure-Object).Count") or 0)
    s["timestamp"] = datetime.now().isoformat()
    return s


def append_log(s: dict):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")


def show_log(limit: int = 10):
    if not LOG.exists():
        print("no log yet")
        return
    lines = LOG.read_text(encoding="utf-8").strip().split("\n")
    print(f"last {min(limit, len(lines))} entries:\n")
    for line in lines[-limit:]:
        try:
            s = json.loads(line)
            conn = s.get("connections", "?")
            print(f"  {s['timestamp']}  run={s.get('running')}  conn={conn}  accept={s.get('accepting')}")
        except Exception:
            pass


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "once"
    if action == "once":
        s = snapshot()
        append_log(s)
        print(json.dumps(s, indent=2, ensure_ascii=False))
    elif action == "log":
        show_log(int(sys.argv[2]) if len(sys.argv) > 2 else 10)
    elif action == "watch":
        print("watching TM every 5 min (Ctrl+C to stop)...")
        while True:
            s = snapshot()
            append_log(s)
            print(f"{s['timestamp']}  run={s.get('running')}  conn={s.get('connections','?')}")
            time.sleep(300)
    else:
        print("usage: python tm_stats.py [once|log [n]|watch]")
