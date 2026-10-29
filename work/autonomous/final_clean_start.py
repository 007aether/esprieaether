#!/usr/bin/env python3
"""
Final clean start: one self_heal_daemon.py supervising one trade_cycle loop.py --daemon.
"""
import psutil
import subprocess
import sys
import time
from pathlib import Path

WORK = r"C:\Users\ESPRIEAETHER\Desktop\esprieaether"
DB = Path(WORK) / "work" / "data" / "trade_cycle.db"

# 1) Kill only the real python processes (not bash wrappers)
killed = []
for p in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        cl = " ".join(p.info["cmdline"] or "")
    except Exception:
        continue
    if p.info["name"] in ("python.exe", "python3.exe") and ("self_heal_daemon.py" in cl or "loop.py --daemon" in cl):
        try:
            p.kill()
            killed.append(p.info["pid"])
        except Exception as e:
            print("kill fail", p.info["pid"], e)
print("killed real python pids:", killed)
time.sleep(3)

# 2) Start ONE self_heal_daemon.py (supervised background)
logf = open(WORK + "/data/autonomous_selfheal_daemon.log", "ab", buffering=0)
proc = subprocess.Popen(
    [sys.executable, "work/autonomous/self_heal_daemon.py"],
    cwd=WORK, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
print("self_heal_daemon started (pid %d)" % proc.pid)
time.sleep(8)

# 3) Verify Trade Cycle is live (DB cycle count grew)
import sqlite3
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
cycles = con.execute("SELECT COUNT(*) c FROM cycle_runs").fetchone()[0]
feedback = con.execute("SELECT COUNT(*) c FROM feedback").fetchone()[0]
research = con.execute("SELECT COUNT(*) c FROM research").fetchone()[0]
print(f"DB -> cycle_runs={cycles} feedback={feedback} research={research}")

# 4) Show live loop.py --daemon (should be 1 now)
print("=== loop.py --daemon running now ===")
cnt = 0
for p in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        cl = " ".join(p.info["cmdline"] or "")
    except Exception:
        continue
    if "loop.py --daemon" in cl and p.info["name"] in ("python.exe", "python3.exe"):
        print(" ", p.info["pid"], cl[-90:])
        cnt += 1
print("loop.py --daemon count:", cnt)
print("DONE")
