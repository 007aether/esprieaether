#!/usr/bin/env python3
"""Clean restart of the self-heal daemon + Trade Cycle confirmation."""
import os
import psutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

WORK = r"C:\Users\ESPRIEAETHER\Desktop\esprieaether"
DB = Path(WORK) / "work" / "data" / "trade_cycle.db"

def b(name):
    return f"kill {name}"

# 1) Kill stale self_heal_daemon.py and loop.py --daemon processes
killed = []
for p in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        cl = " ".join(p.info["cmdline"] or [])
    except Exception:
        continue
    if "self_heal_daemon.py" in cl:
        try:
            p.kill(); killed.append(p.info["pid"])
        except Exception as e:
            print("kill fail", p.info["pid"], e)
    elif "loop.py --daemon" in cl:
        try:
            p.kill(); killed.append(p.info["pid"])
        except Exception as e:
            print("kill fail", p.info["pid"], e)
print("killed pids:", killed)
time.sleep(2)

# 2) Start ONE self_heal_daemon.py
logf = open(WORK + "/data/autonomous_selfheal_daemon.log", "ab", buffering=0)
proc = subprocess.Popen(
    [sys.executable, "work/autonomous/self_heal_daemon.py"],
    cwd=WORK, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
print("self_heal_daemon pid =", proc.pid)

# 3) Wait and confirm Trade Cycle is live
time.sleep(50)
import sqlite3 as sql
con = sql.connect(DB); con.row_factory = sql.Row
cycles = con.execute("SELECT COUNT(*) c FROM cycle_runs").fetchone()[0]
feedback = con.execute("SELECT COUNT(*) c FROM feedback").fetchone()[0]
research = con.execute("SELECT COUNT(*) c FROM research").fetchone()[0]
con.close()
print(f"cycle_runs={cycles} feedback={feedback} research={research}")

# 4) Check whether loop.py --daemon is running now
import subprocess as sp
out = sp.run(["powershell","-NoProfile","-Command",
    "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'loop.py --daemon' } | Select-Object -First 1 | Select-Object CommandLine"],
    capture_output=True, text=True, timeout=15)
print("loop.py --daemon detection (powershell):", out.stdout.strip()[:120])
print("DONE")
