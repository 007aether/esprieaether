#!/usr/bin/env python3
"""EsprieAether — One-command launcher for core services.

Starts (in background where possible):
  - AI Router
  - Web Dashboard
  - Watchdog (self-heal)
  - Optional: Trade Cycle daemon, Telegram bot

Usage:
    python start_all.py
    python start_all.py --with-trade --with-bot
    python start_all.py --health-only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Load .env if present
def _load_dotenv():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _spawn(name: str, cmd: list[str], cwd: Path | None = None) -> subprocess.Popen | None:
    print(f"  → starting {name} ...")
    try:
        kwargs = {
            "cwd": str(cwd or ROOT),
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore
        else:
            kwargs["start_new_session"] = True
        return subprocess.Popen([sys.executable, *cmd], **kwargs)
    except Exception as e:
        print(f"  ✗ {name} failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="EsprieAether launcher")
    parser.add_argument("--with-trade", action="store_true", help="Also start trade_cycle daemon")
    parser.add_argument("--with-bot", action="store_true", help="Also start Telegram bot")
    parser.add_argument("--with-evolve", action="store_true", help="Also start autonome_evolve")
    parser.add_argument("--health-only", action="store_true", help="Only print health report")
    args = parser.parse_args()

    _load_dotenv()

    if args.health_only:
        try:
            from src.system_health import format_report_text
            print(format_report_text())
        except Exception as e:
            print(f"Health module error: {e}")
        return

    print("⚡ EsprieAether — starting core services")
    print(f"   root: {ROOT}")
    print()

    processes = []

    # Core
    processes.append(("ai_router", _spawn("ai_router", ["src/ai_router.py"])))
    time.sleep(0.8)
    processes.append(("web_interface", _spawn("web_interface", ["src/web_interface.py"])))
    time.sleep(0.5)
    processes.append(("watchdog", _spawn("watchdog", ["src/watchdog.py"])))

    if args.with_trade:
        tc = ROOT / "work" / "agents" / "trade_cycle" / "loop.py"
        if tc.exists():
            processes.append(("trade_cycle", _spawn("trade_cycle", [str(tc), "--daemon"])))

    if args.with_bot:
        processes.append(("telegram_bot", _spawn("telegram_bot", ["src/bot.py"])))

    if args.with_evolve:
        processes.append(("autonome_evolve", _spawn("autonome_evolve", ["src/autonome_evolve.py", "--daemon"])))

    print()
    time.sleep(2.0)

    try:
        from src.system_health import format_report_text
        print(format_report_text())
    except Exception as e:
        print(f"(health check skipped: {e})")

    print()
    print("Dashboard: http://localhost:5000")
    print("Health:    python start_all.py --health-only")
    print()
    print("Processes launched in background. Use watchdog or Task Manager to stop them.")
    print("Tip: keep this terminal open or run under a process manager for production.")


if __name__ == "__main__":
    main()
