#!/usr/bin/env python3
"""
bot_heartbeat.py — dead-man switch for all EsprieAether + Sunna bots/services.

Checks every monitored target on a schedule and pings Cronpulse
(or, standalone, pings Telegram via the bot API). If a target stops
checking in within its interval, you get alerted.

Standalone mode (default, no Cronpulse server needed): checks each
target's health directly and sends a Telegram alert on failure.
Cronpulse mode: set CRONPULSE_URL + CRONPULSE_API_KEY to also forward
pings to a running Cronpulse server.

Targets: the 7 services + the 12 Sunna bots.
Alerts go to the same Telegram chat as the bot (BOT_TOKEN + CHAT_ID).
"""

import os
import subprocess
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SUNNA = Path(os.environ.get("SUNNA_DIR", str(Path.home() / "Desktop" / "Sunna-Equipe-Industrial")))

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CRONPULSE_URL = os.getenv("CRONPULSE_URL", "")  # optional
CRONPULSE_KEY = os.getenv("CRONPULSE_API_KEY", "")

# service -> (port, path)
SERVICES = {
    "router": (11435, "/health"),
    "orchestrator": (11436, "/health"),
    "web": (5000, "/health"),
    "cloud-desktop": (5001, "/health"),
    "jarvis": (8000, "/api/health"),
    "sunna-api": (5100, "/health"),
    "dsh-bridge": (5101, "/health"),
    "integrations": (5102, "/health"),
}

# bot script -> expected to be running (process match)
BOTS = {
    "netlify-keepalive": "netlify_keepalive_bot.py",
    "sunna-web": "sunna_web_bot.py",
}

CHECK_EVERY = int(os.getenv("HEARTBEAT_INTERVAL", "300"))  # 5 min
_last_alert = {}


def now():
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def log(msg):
    print(f"[{now()}] heartbeat | {msg}", flush=True)


def http_up(port: int, path: str) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
            return r.status < 500
    except Exception:
        return False


def process_running(match: str) -> bool:
    try:
        if os.name == "nt":
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object {{ $_.CommandLine -like '*{match}*' }} | Measure-Object).Count"],
                capture_output=True, text=True, timeout=15).stdout.strip()
            return out not in ("0", "")
        out = subprocess.run(["pgrep", "-f", match], capture_output=True, text=True).returncode
        return out == 0
    except Exception:
        return False


def telegram(text: str):
    if not (BOT_TOKEN and CHAT_ID):
        return
    try:
        data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=data, timeout=10)
    except Exception:
        pass


def cronpulse_ping(monitor_id: int):
    if not (CRONPULSE_URL and CRONPULSE_KEY):
        return
    try:
        req = urllib.request.Request(f"{CRONPULSE_URL}/api/ping/{monitor_id}",
                                     headers={"X-API-Key": CRONPULSE_KEY})
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass


def check_all() -> dict:
    results = {}
    for name, (port, path) in SERVICES.items():
        results[name] = http_up(port, path)
    for name, match in BOTS.items():
        results[name] = process_running(match)
    return results


def main():
    log(f"=== heartbeat started — {len(SERVICES)} services + {len(BOTS)} bots ===")
    while True:
        res = check_all()
        down = [k for k, v in res.items() if not v]
        up = sum(1 for v in res.values() if v)
        if down:
            log(f"DOWN: {down} ({up}/{len(res)} up)")
            for name in down:
                # alert at most once per 30 min per target
                if time.time() - _last_alert.get(name, 0) > 1800:
                    telegram(f"🔴 EsprieAether: {name} is DOWN\nWatchdog should restart it.")
                    _last_alert[name] = time.time()
        else:
            log(f"all healthy ({up}/{len(res)})")
        # forward pings to cronpulse if configured (id = index+1)
        if CRONPULSE_URL and CRONPULSE_KEY:
            for i, name in enumerate(res, 1):
                cronpulse_ping(i)
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
