#!/usr/bin/env python3
"""
cloud_desktop_agent.py — Cloud Desktop Agent (remote access + cloud control)

Allows DSH + Hermes + orchestrator to control this Windows PC remotely:
  - SSH reverse tunnel (SSH into this PC from anywhere)
  - Remote command execution (via SSH or HTTP API)
  - Cloud desktop status (uptime, services, robots, agents)
  - Group integration (Sunna team + DSH + Hermes)

Endpoints (port 5001):
  GET  /status          — full system status
  POST /exec            — run a shell command (auth token required)
  GET  /group           — group members (Sunna team + DSH + Hermes)
  POST /group/add       — add a member to the group
  POST /tunnel/start    — start SSH reverse tunnel
  POST /tunnel/stop     — stop SSH reverse tunnel
  GET  /tunnel/status   — tunnel status

Auth: CLOUD_DESKTOP_TOKEN env (shared secret). Set in .env.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

app = Flask(__name__)

PORT = int(os.getenv("CLOUD_DESKTOP_PORT", "5001"))
TOKEN = os.getenv("CLOUD_DESKTOP_TOKEN", "")
PROJECT = Path(__file__).parent.parent
LOG = Path(os.path.expanduser("~")) / "ESPRIEAETHER" / "data" / "cloud_desktop.log"

# ── Group registry (members that can access this PC) ──
GROUP_FILE = PROJECT / "data" / "group.json"
DEFAULT_GROUP = {
    "members": [
        {"name": "DSH", "role": "orchestrator", "url": "http://localhost:11436"},
        {"name": "Hermes", "role": "bridge", "url": "local"},
        {"name": "Sunna", "role": "team", "url": "local"},
        {"name": "CloudDesktop", "role": "remote", "url": "local"},
    ]
}

# ── SSH tunnel state ──
TUNNEL = {"pid": None, "started_at": None, "remote_host": None, "remote_port": None}


def log(msg: str):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    print(line, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _auth() -> bool:
    """Check auth token."""
    if not TOKEN:
        return False  # token not configured = deny
    return request.headers.get("X-Token", "") == TOKEN


def load_group() -> dict:
    if GROUP_FILE.exists():
        try:
            return json.loads(GROUP_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_GROUP


def save_group(g: dict):
    GROUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    GROUP_FILE.write_text(json.dumps(g, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Endpoints ──

@app.route("/", methods=["GET"])
def dashboard():
    """Dashboard page (inject token so /exec works from the page)."""
    return render_template("cloud.html", token=TOKEN)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "cloud-desktop", "port": PORT})


@app.route("/status")
def status():
    """Full system status."""
    services = {}
    for name, url in [
        ("ollama", "http://127.0.0.1:11434/api/tags"),
        ("router", "http://127.0.0.1:11435/health"),
        ("orchestrator", "http://127.0.0.1:11436/health"),
        ("web", "http://127.0.0.1:5000/health"),
    ]:
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                services[name] = r.status
        except Exception:
            services[name] = 0

    # processes
    def proc_count(match: str) -> int:
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object {{ $_.CommandLine -like '*{match}*' }} | Measure-Object).Count"],
                capture_output=True, text=True, timeout=15,
            )
            return int(out.stdout.strip() or 0)
        except Exception:
            return -1

    return jsonify({
        "services": services,
        "processes": {
            "bot": proc_count("bot.py"),
            "watchdog": proc_count("watchdog"),
            "dsh": proc_count("DeepSeek"),
        },
        "tunnel": TUNNEL,
        "group": load_group(),
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/exec", methods=["POST"])
def exec_cmd():
    """Run a shell command (auth required)."""
    if not _auth():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    cmd = data.get("cmd", "")
    timeout = min(int(data.get("timeout", 60)), 300)
    if not cmd:
        return jsonify({"error": "no cmd"}), 400
    try:
        out = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
            cwd=str(PROJECT),
        )
        return jsonify({"cmd": cmd, "exit_code": out.returncode,
                        "stdout": out.stdout[-4000:], "stderr": out.stderr[-2000:]})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "timeout"}), 408
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/group")
def group():
    return jsonify(load_group())


@app.route("/group/add", methods=["POST"])
def group_add():
    if not _auth():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    name = data.get("name", "")
    if not name:
        return jsonify({"error": "no name"}), 400
    g = load_group()
    g["members"].append({"name": name, "role": data.get("role", "member"),
                          "url": data.get("url", "local")})
    save_group(g)
    log(f"group + {name}")
    return jsonify({"ok": True, "members": g["members"]})


@app.route("/tunnel/start", methods=["POST"])
def tunnel_start():
    """Start SSH reverse tunnel: ssh -R <remote_port>:localhost:5001 <user>@<host>"""
    if not _auth():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    host = data.get("host", "")
    user = data.get("user", "")
    rport = int(data.get("remote_port", 2222))
    key = data.get("key", "")  # path to SSH key
    if not host or not user:
        return jsonify({"error": "need host + user"}), 400

    cmd = ["ssh", "-N", "-R", f"{rport}:localhost:{PORT}"]
    if key:
        cmd += ["-i", key]
    cmd += [f"{user}@{host}"]

    try:
        if os.name == "nt":
            kwargs = {"creationflags": 0x00000200 | 0x00000008}
        else:
            kwargs = {"start_new_session": True}
        proc = subprocess.Popen(cmd, **kwargs)
        TUNNEL.update({"pid": proc.pid, "started_at": datetime.now().isoformat(),
                       "remote_host": host, "remote_port": rport})
        log(f"tunnel start → {user}@{host}:{rport}")
        return jsonify({"ok": True, "pid": proc.pid, "tunnel": TUNNEL})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/tunnel/stop", methods=["POST"])
def tunnel_stop():
    if not _auth():
        return jsonify({"error": "unauthorized"}), 401
    if TUNNEL["pid"]:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(TUNNEL["pid"])],
                           capture_output=True, timeout=10)
        except Exception:
            pass
        log(f"tunnel stop (pid {TUNNEL['pid']})")
        TUNNEL.update({"pid": None, "started_at": None, "remote_host": None, "remote_port": None})
    return jsonify({"ok": True, "tunnel": TUNNEL})


@app.route("/tunnel/status")
def tunnel_status():
    return jsonify(TUNNEL)


@app.route("/tm")
def tm_status():
    """TraffMonetizer status (process + settings)."""
    import subprocess as _sp
    sfile = Path(os.environ.get("APPDATA", "")) / "Traffmonetizer" / "settings.json"
    dfile = Path(os.environ.get("APPDATA", "")) / "Traffmonetizer" / "storage.json"
    s = {}
    if sfile.exists():
        try:
            s = json.loads(sfile.read_text())
        except Exception:
            pass
    d = {}
    if dfile.exists():
        try:
            d = json.loads(dfile.read_text())
        except Exception:
            pass
    pid = ""
    try:
        pid = _sp.run(["powershell", "-NoProfile", "-Command",
                       "(Get-Process -Name 'Traffmonetizer*' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Id)"],
                      capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception:
        pass
    conns = ""
    if pid:
        try:
            conns = _sp.run(["powershell", "-NoProfile", "-Command",
                             f"(Get-NetTCPConnection -OwningProcess {pid} -ErrorAction SilentlyContinue | Measure-Object).Count"],
                            capture_output=True, text=True, timeout=15).stdout.strip()
        except Exception:
            pass
    return jsonify({
        "running": bool(pid),
        "pid": int(pid) if pid.isdigit() else None,
        "connections": int(conns) if conns.isdigit() else None,
        "accepting": s.get("Accepting"),
        "start_with_windows": s.get("StartWithWindows"),
        "token_prefix": (s.get("Token", "")[:8] + "...") if s.get("Token") else None,
        "device_id": d.get("id"),
        "dashboard": "https://app.traffmonetizer.com/dashboard",
    })


if __name__ == "__main__":
    if not TOKEN:
        log("⚠️  CLOUD_DESKTOP_TOKEN not set — exec/tunnel endpoints will deny all requests")
    log(f"🚀 Cloud Desktop Agent → http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
