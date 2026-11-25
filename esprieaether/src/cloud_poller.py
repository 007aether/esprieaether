#!/usr/bin/env python3
"""
cloud_poller.py — PC side of the GitHub cloud bridge

WHAT: The cloud node (GitHub Actions) writes commands into
data/cloud_commands.json and pushes them. This poller:
  1. git pull (fetch cloud status + queued commands)
  2. executes every unexecuted command (mesh cycle, scans...)
  3. marks them executed, pushes the board/status back
  4. stamps pc_last_seen so the cloud knows the PC is alive

WHY: GitHub Issues are the free remote-control channel — the user opens an
issue from their phone, the cloud answers immediately for cloud-capable
commands, and PC-only commands (the mesh needs local Ollama) are queued here.

Run: standalone (python src/cloud_poller.py) or as a daemon (--daemon, 5 min).
Also wired into autonomous_loop as task_cloud_bridge (every 10 min).
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA = BASE_DIR / "data"
COMMANDS_FILE = DATA / "cloud_commands.json"
STATUS_FILE = DATA / "cloud_status.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def run_git(*args, timeout=120):
    return subprocess.run(
        ["git", *args],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=dict(os.environ, GIT_TERMINAL_PROMPT="0"),
    )


def git_pull():
    """Fetch cloud writes (commands + status) from origin."""
    try:
        r = run_git("pull", "--rebase", "--autostash", "origin", "main", timeout=180)
        return {"ok": r.returncode == 0, "output": (r.stdout or r.stderr or "").strip()[:200]}
    except Exception as e:
        return {"ok": False, "output": str(e)[:200]}


def git_push_board():
    """Push local results (board, status) back to the cloud node."""
    try:
        run_git("add", "data/", timeout=60)
        st = run_git("status", "--porcelain", timeout=60)
        if not (st.stdout or "").strip():
            return {"ok": True, "pushed": False}
        run_git(
            "-c", "user.name=aether-pc",
            "-c", "user.email=pc@aether.local",
            "commit", "-m", f"🖥️ PC sync ({now_iso()})",
            timeout=60,
        )
        ps = run_git("push", "origin", "main", timeout=180)
        return {"ok": ps.returncode == 0, "pushed": ps.returncode == 0}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def stamp_pc_alive():
    """Tell the cloud node the PC is alive (merged into cloud_status.json)."""
    try:
        status = {}
        if STATUS_FILE.exists():
            status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        status["pc_last_seen"] = now_iso()
        status["pc_ok"] = True
        STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def execute_command(cmd_entry):
    """Execute one cloud command on the PC. Returns a result dict."""
    cmd = cmd_entry.get("command", "")
    result = {"command": cmd, "ts": now_iso(), "status": "ok"}

    if cmd == "mesh_cycle":
        try:
            sys.path.insert(0, str(BASE_DIR / "src"))
            import agent_mesh
            results = agent_mesh.mesh_cycle(rounds=1)
            result["agents_thought"] = len(results)
            result["ok_count"] = sum(1 for r in results if r.get("ok"))
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)[:200]

    elif cmd == "scan":
        try:
            sys.path.insert(0, str(BASE_DIR / "src"))
            import airdrop_scorer
            scored = airdrop_scorer.score_all(deep_enrich=False)
            result["scored"] = len(scored) if scored else 0
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)[:200]

    elif cmd == "status":
        result["pc_status"] = "ok"
        result["services"] = probe_services()

    else:
        result["status"] = "error"
        result["error"] = f"unknown command: {cmd}"

    return result


def probe_services():
    """Quick local health sweep for the cloud's status board."""
    import urllib.request
    services = {
        "router": "http://127.0.0.1:11435/v1/models",
        "mesh": "http://127.0.0.1:11437/health",
        "web": "http://127.0.0.1:5000/health",
        "sunna": "http://127.0.0.1:5100/health",
    }
    out = {}
    for name, url in services.items():
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                out[name] = r.status
        except Exception:
            out[name] = 0
    return out


def poll_once():
    """One poll cycle: pull → execute queued commands → push back."""
    report = {"ts": now_iso()}

    # 1. pull cloud writes
    pull = git_pull()
    report["pull"] = pull["ok"]
    if pull["ok"] and "Already up to date" not in pull.get("output", ""):
        report["pull_output"] = pull.get("output", "")[:150]

    # 2. PC is alive
    stamp_pc_alive()

    # 3. execute queued commands
    executed = []
    if COMMANDS_FILE.exists():
        try:
            cmds = json.loads(COMMANDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            cmds = []
        for entry in cmds:
            if entry.get("executed"):
                continue
            res = execute_command(entry)
            entry["executed"] = True
            entry["result"] = res
            executed.append(res)
        COMMANDS_FILE.write_text(json.dumps(cmds, ensure_ascii=False, indent=2), encoding="utf-8")
    report["executed"] = executed

    # 4. push board + status + results back to the cloud
    if executed or True:  # always stamp pc_last_seen
        push = git_push_board()
        report["pushed"] = push.get("pushed", False)

    return report


def main():
    if "--daemon" in sys.argv:
        print(f"🖥️  Cloud poller daemon — {BASE_DIR}")
        while True:
            try:
                rep = poll_once()
                n = len(rep.get("executed", []))
                if n:
                    print(f"  [{rep['ts']}] executed {n} cloud command(s)")
                else:
                    print(f"  [{rep['ts']}] idle (pc stamped)")
            except Exception as e:
                print(f"  poll error: {e}")
            time.sleep(300)  # 5 minutes
    else:
        rep = poll_once()
        print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
