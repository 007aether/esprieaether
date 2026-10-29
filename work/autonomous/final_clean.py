#!/usr/bin/env python3
"""One-shot clean install: kill self_heal+loop, start exactly ONE of each, verify."""
import psutil, sqlite3, subprocess, sys, time
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
    return ("self_heal_daemon.py" in cl) or ("agents/trade_cycle/loop.py --daemon" in cl)

# kill until empty (3 rounds)
for i in range(4):
    ks = [p.info["pid"] for p in psutil.process_iter(["pid","name","cmdline"]) if is_target(p)]
    if not ks:
        break
    for pid in ks:
        try:
            psutil.Process(pid).kill()
        except Exception:
            pass
    print(f"kill pass {i+1}: {ks}", flush=True)
    time.sleep(4)

# start exactly ONE self_heal
logf = open(WORK + "/data/autonomous_selfheal_daemon.log", "ab", buffering=0)
proc = subprocess.Popen([sys.executable, "work/autonomous/self_heal_daemon.py"],
                        cwd=WORK, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
print("self_heal pid =", proc.pid, flush=True)

# wait long enough for self_heal to (re)start trade_cycle
time.sleep(30)

# verify
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
print("DB: cycle_runs=%d feedback=%d research=%d" % (
    con.execute("SELECT COUNT(*) c FROM cycle_runs").fetchone()[0],
    con.execute("SELECT COUNT(*) c FROM feedback").fetchone()[0],
    con.execute("SELECT COUNT(*) c FROM research").fetchone()[0]))
con.close()

loops = [p.info["pid"] for p in psutil.process_iter(["pid","name","cmdline"])
         if p.info["name"] in ("python.exe","python3.exe") and "agents/trade_cycle/loop.py --daemon" in " ".join(p.info["cmdline"] or "")]
heals = [p.info["pid"] for p in psutil.process_iter(["pid","name","cmdline"])
         if p.info["name"] in ("python.exe","python3.exe") and "self_heal_daemon.py" in " ".join(p.info["cmdline"] or "")]
print("FINAL loop.py --daemon:", loops)
print("FINAL self_heal_daemon.py:", heals)
print("FINAL DONE")
