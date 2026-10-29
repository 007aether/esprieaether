#!/usr/bin/env python3
"""Aggressive final cleanup + single clean self-heal restart."""
import psutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

WORK = r"C:\Users\ESPRIEAETHER\Desktop\esprieaether"
DB = Path(WORK) / "work" / "data" / "trade_cycle.db"

def is_target(p):
    try:
        cl = " ".join(p.info["cmdline"] or "")
    except Exception:
        return False
    if p.info["name"] not in ("python.exe", "python3.exe"):
        return False
    return ("self_heal_daemon.py" in cl) or ("loop.py --daemon" in cl)

def kill_all():
    killed = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        if is_target(p):
            try:
                p.kill(); killed.append(p.info["pid"])
            except Exception:
                pass
    return killed

# two aggressive kill passes
for i in range(3):
    k = kill_all()
    if not k:
        break
    print(f"pass {i+1}: killed {k}")
    time.sleep(3)

logf = open(WORK + "/data/autonomous_selfheal_daemon.log", "ab", buffering=0)
proc = subprocess.Popen([sys.executable, "work/autonomous/self_heal_daemon.py"],
                        cwd=WORK, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
print("self_heal pid =", proc.pid)
time.sleep(40)

con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
print("DB: cycle_runs=%d feedback=%d research=%d" % (
    con.execute("SELECT COUNT(*) c FROM cycle_runs").fetchone()[0],
    con.execute("SELECT COUNT(*) c FROM feedback").fetchone()[0],
    con.execute("SELECT COUNT(*) c FROM research").fetchone()[0]))
con.close()

print("=== loop.py --daemon (python.exe) ===")
loops = []
for p in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        cl = " ".join(p.info["cmdline"] or "")
    except Exception:
        continue
    if "loop.py --daemon" in cl and p.info["name"] in ("python.exe", "python3.exe"):
        loops.append(p.info["pid"])
        print(" ", p.info["pid"])
print("loop count =", len(loops))

print("=== self_heal_daemon.py (python.exe) ===")
heals = []
for p in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        cl = " ".join(p.info["cmdline"] or "")
    except Exception:
        continue
    if "self_heal_daemon.py" in cl and p.info["name"] in ("python.exe", "python3.exe"):
        heals.append(p.info["pid"])
        print(" ", p.info["pid"])
print("self_heal count =", len(heals))
print("FINAL")
