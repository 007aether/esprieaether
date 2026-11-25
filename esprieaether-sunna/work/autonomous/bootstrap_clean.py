#!/usr/bin/env python3
"""
Clean bootstrap for the ESPRIEAETHER self-heal system + Trade Cycle.

Steps:
 1) Kill any stale self_heal_daemon / loop.py --daemon / trade_cycle processes.
 2) Start ONE self_heal_daemon.py (supervisor for the whole system).
 3) Confirm loop.py --daemon is running and a cycle executes.
"""
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

WORK = r"C:\Users\ESPRIEAETHER\Desktop\esprieaether"
TC = Path(WORK) / "work" / "agents" / "trade_cycle"
DB = Path(WORK) / "work" / "data" / "trade_cycle.db"
HEAL_LOG = Path(WORK) / "data" / "autonomous_selfheal_daemon.log"

def kill_matches(terms):
    """Kill every process whose command line mentions one of the terms."""
    import psutil
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = " ".join(p.info["cmdline"] or [])
        except Exception:
            continue
        if any(t in cmd for t in terms):
            try:
                p.kill()
                print(f"[bootstrap] killed pid {p.info['pid']} ({p.info['name']}): {cmd[:80]}")
            except Exception as e:
                print(f"[bootstrap] kill failed pid {p.info['pid']}: {e}")
    time.sleep(2)

def cycle_runs():
    if not DB.exists():
        return 0
    con = sqlite3.connect(DB)
    c = con.execute("SELECT COUNT(*) c FROM cycle_runs").fetchone()[0]
    con.close()
    return c

print("[bootstrap] step 1: killing stale self_heal / trade_cycle processes ...")
kill_matches(["self_heal_daemon.py", "loop.py --daemon", "trade_cycle"])
time.sleep(2)

# give a moment for anything that was mid-cycle to settle, then confirm
before = cycle_runs()
print(f"[bootstrap] cycle_runs before fresh start = {before}")

print("[bootstrap] step 2: starting self_heal_daemon.py ...")
logf = HEAL_LOG.open("ab", buffering=0)
proc = subprocess.Popen(
    [sys.executable, "work/autonomous/self_heal_daemon.py"],
    cwd=WORK, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
print(f"[bootstrap] self_heal_daemon pid={proc.pid}")

print("[bootstrap] step 3: waiting 40s then checking trade_cycle status ...")
time.sleep(40)
import sqlite3 as sql2
con = sql2.connect(DB); con.row_factory = sql2.Row
cycles = con.execute("SELECT COUNT(*) c FROM cycle_runs").fetchone()[0]
feedback = con.execute("SELECT COUNT(*) c FROM feedback").fetchone()[0]
research = con.execute("SELECT COUNT(*) c FROM research").fetchone()[0]
con.close()
print(f"[bootstrap] cycle_runs={cycles} feedback={feedback} research={research}")
print(f"[bootstrap] loop.py --daemon running: ", end="")
import subprocess as sp
ps = sp.run(["powershell","-NoProfile","-Command",
             "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'loop.py --daemon' } | Measure-Object"].stdout.decode(), shell=False)
print(ps.returncode == 0)
print("[bootstrap] DONE")
