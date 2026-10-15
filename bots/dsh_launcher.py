#!/usr/bin/env python3
"""
dsh_launcher.py — launch DSH (DeepSeek Harness) web server detached (24/7)

DSH web = browser GUI at http://127.0.0.1:3080/?token=<auto> (CDP 19387).
When DSH is up, the JARVIS⇄DSH relay (port 5105) switches from local-fallback
to DSH-driven browser automation.

DSH requires a real TTY (stdin+stdout interactive) — a plain detached process
is NOT enough. This launcher uses PowerShell Start-Process with a hidden
console window (which gives DSH the TTY it needs while staying invisible).

Usage:
    python dsh_launcher.py           # launch DSH web if not running
    python dsh_launcher.py --check   # report DSH status only
"""

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DSH_DIR = BASE_DIR / "tools" / "dsh"
DSH_BIN = DSH_DIR / "node_modules" / "@deepseek-ai" / "dsh" / "lib" / "bin.js"
NODE = Path("C:/Users/ESPRIEAETHER/AppData/Local/hermes/tools/node-26.7.0-win32-x64/node.exe")
DSH_WEB_URL = "http://127.0.0.1:3080/"
DSH_CDP_URL = "http://127.0.0.1:19387/json/version"
STATE_FILE = BASE_DIR / "data" / "dsh_state.json"


def dsh_running() -> bool:
    try:
        with urllib.request.urlopen(DSH_WEB_URL, timeout=4) as r:
            return r.status == 200
    except Exception:
        return False


def check() -> dict:
    return {
        "dsh_web": dsh_running(),
        "dsh_url": DSH_WEB_URL,
        "bin_exists": DSH_BIN.exists(),
        "node_exists": NODE.exists(),
    }


def launch() -> dict:
    if dsh_running():
        return {"ok": True, "already_running": True, "url": DSH_WEB_URL}
    if not DSH_BIN.exists():
        return {"ok": False, "error": f"DSH bin not found: {DSH_BIN} — run npm install in tools/dsh first"}
    if not NODE.exists():
        return {"ok": False, "error": f"node not found: {NODE}"}

    # PowerShell Start-Process with a hidden window gives DSH the real TTY it
    # needs (a plain detached process gets 'stdout is not a tty' and exits).
    ps = (
        "Start-Process "
        f"-FilePath '{NODE}' "
        f"-ArgumentList '{DSH_BIN}','web','--no-open' "
        f"-WorkingDirectory '{DSH_DIR}' "
        "-WindowStyle Hidden "
        f"-RedirectStandardOutput '{BASE_DIR / 'data' / 'logs' / 'dsh.log'}' "
        f"-RedirectStandardError '{BASE_DIR / 'data' / 'logs' / 'dsh.err'}'"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, timeout=20)
        # wait for it to come up
        import time
        for _ in range(12):
            time.sleep(5)
            if dsh_running():
                STATE_FILE.write_text(json.dumps(
                    {"status": "running", "url": DSH_WEB_URL}, indent=2))
                return {"ok": True, "url": DSH_WEB_URL}
        return {"ok": False, "error": "DSH did not come up within 60s — check data/logs/dsh.err"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


if __name__ == "__main__":
    if "--check" in sys.argv:
        print(json.dumps(check(), indent=2))
    else:
        print(json.dumps(launch(), indent=2))
