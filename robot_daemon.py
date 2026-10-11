#!/usr/bin/env python3
"""
ESPRIEAETHER ROBOT DAEMON — 24/7
يشغّل محرك الروبوتات بشكل مستقل (بلا الويب).
- يقرأ robots المفعّلين (status='active') من DB
- يدور كل 60 ثانية
- يكتب النتائج ف DB + robot_engine.log

التشغيل:
  python robot_daemon.py              # foreground
  python robot_daemon.py --interval 30  # كل 30s

Windows Task Scheduler (24/7 على restart):
  schtasks /create /tn "EsprieAetherRobots" /tr "python robot_daemon.py" /sc onstart /rl highest /f
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

# ─── Logging (ملف + console) ───
LOG_FILE = BASE_DIR / "robot_daemon.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("robot-daemon")


def main():
    interval = 60.0
    if "--interval" in sys.argv:
        try:
            interval = float(sys.argv[sys.argv.index("--interval") + 1])
        except (IndexError, ValueError):
            pass

    from robots.robot_engine import RobotEngine
    eng = RobotEngine(interval=interval)

    # graceful shutdown
    stop = {"flag": False}
    def handler(sig, frame):
        logger.info("shutdown signal received")
        stop["flag"] = True
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    # نظام التشغيل
    import platform
    logger.info("=" * 60)
    logger.info(f"ESPRIEAETHER ROBOT DAEMON — {platform.system()}")
    logger.info(f"interval: {interval}s")
    logger.info("=" * 60)

    # حالة البداية
    st = eng.get_stats()
    active = st.get("robots_by_status", {}).get("active", 0)
    logger.info(f"active robots: {active}")
    if active == 0:
        logger.warning("no active robots — activate systems first:")
        logger.warning("  python robot_daemon.py --activate immune")
        logger.warning("  python robot_daemon.py --activate ai")
        # نفعّل immune + ai تلقائياً (best practice)
        eng.activate(system="immune")
        eng.activate(system="ai")
        logger.info("auto-activated: immune + ai")

    logger.info("daemon running... (Ctrl+C to stop)")

    while not stop["flag"]:
        try:
            eng.run_active()
        except Exception as e:
            logger.error(f"cycle error: {e}")
        # انتظار قابل للـ interrupt
        for _ in range(int(interval * 2)):
            if stop["flag"]:
                break
            time.sleep(0.5)

    logger.info("daemon stopped")


if __name__ == "__main__":
    # allow --activate <system> as one-shot
    if "--activate" in sys.argv:
        idx = sys.argv.index("--activate")
        try:
            system = sys.argv[idx + 1]
            from robots.robot_engine import RobotEngine
            eng = RobotEngine()
            eng.activate(system=system)
            print(f"activated: {system}")
        except (IndexError, ValueError):
            print("usage: robot_daemon.py --activate <system>")
        sys.exit(0)

    main()
