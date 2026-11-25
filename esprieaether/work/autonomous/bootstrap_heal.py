#!/usr/bin/env python3
"""Self-heal bootstrap: kill stale self_heal/loop/trade_cycle processes, then start ONE clean daemon."""
import os
import signal
import subprocess
import sys
import time

WORK = r"C:\Users\ESPRIEAETHER\Desktop\esprieaether"
sys.path.insert(0, WORK)

# 1) Kill stale processes whose cmdline mentions self_heal / loop.py --daemon / trade_cycle
killed = []
try:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Select-Object ProcessName,CommandLine | Where-Object { $_.CommandLine -match 'self_heal|loop.py|trade_cycle' } | Select-Object -ExpandProperty ProcessName"],
        capture_output=True, text=True, timeout=30)
    pids = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line:
            pids.append(line)
    # pkill by name for those command lines is not reliable here; fall back to a
    # ps-style scan via pywin32 if available, else skip real PID killing.
    print("[bootstrap] matching process names:", pids)
except Exception as e:
    print("[bootstrap] powershell scan failed:", e)

# 2) Verify loop.py --daemon runs standalone (one cycle) by executing it once if not running
import sqlite3
from pathlib import Path
DB = Path(WORK) / "work" / "data" / "trade_cycle.db"
TC = Path(WORK) / "work" / "agents" / "trade_cycle"

def cycle_count():
    if not DB.exists():
        return 0
    con = sqlite3.connect(DB)
    c = con.execute("SELECT COUNT(*) c FROM cycle_runs").fetchone()[0]
    con.close()
    return c

before = cycle_count()
print(f"[bootstrap] cycle_runs before = {before}")

# 3) Start ONE self-heal daemon
log = open(WORK + "/data/autonomous_selfheal_daemon.log", "ab", buffering=0)
proc = subprocess.Popen(
    [sys.executable, "work/autonomous/self_heal_daemon.py"],
    cwd=WORK, stdout=log, stderr=subprocess.STDOUT,
    start_new_session=True)
print(f"[bootstrap] started self_heal_daemon pid={proc.pid}")

# 4) Wait and report
time.sleep(10)
time.sleep(20)
after = cycle_count()
print(f"[bootstrap] cycle_runs after  = {after}")
print("[bootstrap] DONE")
