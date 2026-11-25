#!/usr/bin/env python3
"""Definitive clean restart: one self_heal, one loop, verified after 20s."""
import psutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

WORK = r"C:\Users\ESPRIEAETHER\Desktop\esprieaether"
DB = Path(WORK) / "work" / "data" / "trade_cycle.db"

def kill_matches(terms):
    killed = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cl = " ".join(p.info["cmdline"] or "")
        except Exception:
            continue
        if p.info["name"] in ("python.exe", "python3.exe") and any(t in cl for t in terms):
            try:
                p.kill(); killed.append(p.info["pid"])
            except Exception as e:
                print("fail", p.info["pid"], e)
    return killed

killed = kill_matches(["self_heal_daemon.py", "loop.py --daemon"])
print("killed:", killed)
time.sleep(3)

logf = open(WORK + "/data/autonomous_selfheal_daemon.log", "ab", buffering=0)
p = subprocess.Popen([sys.executable, "work/autonomous/self_heal_daemon.py"],
                     cwd=WORK, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
print("self_heal pid =", p.pid)
time.sleep(25)

import sqlite3 as sql
con = sql.connect(DB); con.row_factory = sql.Row
print("DB: cycle_runs=%d feedback=%d research=%d" % (
    con.execute("SELECT COUNT(*) c FROM cycle_runs").fetchone()[0],
    con.execute("SELECT COUNT(*) c FROM feedback").fetchone()[0],
    con.execute("SELECT COUNT(*) c FROM research").fetchone()[0]))
con.close()

print("=== loop.py --daemon processes (python.exe only) ===")
loops = []
for p in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        cl = " ".join(p.info["cmdline"] or "")
    except Exception:
        continue
    if "loop.py --daemon" in cl and p.info["name"] in ("python.exe", "python3.exe"):
        loops.append(p.info["pid"])
        print(" ", p.info["pid"])
print("loop.py --daemon count =", len(loops))

print("=== self_heal_daemon.py processes (python.exe only) ===")
heals = []
for p in psutil.process_iter(["pid", "name", "cmdline"]):
    try:
        cl = " ".join(p.info["cmdline"] or "")
    except Exception:
        continue
    if "self_heal_daemon.py" in cl and p.info["name"] in ("python.exe", "python3.exe"):
        heals.append(p.info["pid"])
        print(" ", p.info["pid"])
print("self_heal_daemon.py count =", len(heals))
print("FINAL DONE")
