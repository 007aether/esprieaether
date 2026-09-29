"""
⚡ EsprieAether - Guardian Agent
وكيل حراسة يصلح الأخطاء تلقائياً 24/7
"""
import os
import re
import json
import time
import logging
import subprocess
import threading
from datetime import datetime, timedelta
from smart_alerts import SmartAlerts
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("guardian")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# ─── حدود الأمان ───
MAX_FIXES_PER_HOUR = 5
FIX_COOLDOWN_SECONDS = 300  # 5 دقيقة بين كل إصلاح
GUARDIAN_STATE = BASE_DIR / "guardian_state.json"
HEARTBEAT_DIR = BASE_DIR / "heartbeats"
HEARTBEAT_INTERVAL = 60  # فحص كل 60 ثانية
HEARTBEAT_TOLERANCE = 120  # tolerance 2 minutes


class GuardianAgent:
    """وكيل مراقبة وإصلاح"""

    def __init__(self):
        self.state = self._load_state()
        self.alerts = SmartAlerts()
        self._start_heartbeat_check()

    def _load_state(self) -> dict:
        if GUARDIAN_STATE.exists():
            try:
                return json.loads(GUARDIAN_STATE.read_text())
            except Exception:
                pass
        return {
            "started_at": datetime.now().isoformat(),
            "fixes": [],
            "checks": 0,
            "errors_detected": 0,
            "errors_fixed": 0,
            "errors_failed": 0,
        }

    def _save_state(self):
        GUARDIAN_STATE.write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False)
        )

    # ─────────────────────────────────────
    #  فحص خدماتHeartbeat
    # ─────────────────────────────────────
    def check_heartbeats(self) -> list:
        """الensure agents نشطة باستخدام قاعدة Heartbeat"""
        active_agents = []
        if not HEARTBEAT_DIR.exists():
            return active_agents

        now = datetime.now()
        for heartbeat_file in HEARTBEAT_DIR.glob("*.json"):
            try:
                data = json.loads(heartbeat_file.read_text())
                last_seen = datetime.fromisoformat(data["last_seen"])
                if (now - last_seen).total_seconds() <= HEARTBEAT_TOLERANCE:
                    active_agents.append(heartbeat_file.stem)
            except Exception as e:
                logger.warning(f"Failed to read heartbeat {heartbeat_file.name}: {e}")
        return active_agents

    def _heartbeat_monitor_loop(self):
        """الدورة الدورية ل servants heartbeats"""
        while True:
            try:
                active = self.check_heartbeats()
                self.state["checks"] += 1
                self.state["last_heartbeat_check"] = datetime.now().isoformat()
                self.state["active_agents"] = active
                self._save_state()
                logger.info(f"Heartbeat check completed. Active agents: {len(active)}")
            except Exception as e:
                logger.error(f"Heartbeat check failed: {e}")
            time.sleep(HEARTBEAT_INTERVAL)

    def _start_heartbeat_check(self):
        """Start heartbeat monitoring in a separate thread"""
        thread = threading.Thread(
            target=self._heartbeat_monitor_loop,
            daemon=True,
            name="HeartbeatMonitor"
        )
        thread.start()
        logger.info("Heartbeat monitoring started (60s interval)")

    # ─────────────────────────────────────
    #  فحص Services (as existing)
    # ─────────────────────────────────────
    def check_services(self) -> dict:
        """ inspection situation of services"""
        services = ["aether-web", "aether-bot", "aether-core", "ollama"]
        result = {}

        for svc in services:
            try:
                r = subprocess.run(
                    ["systemctl", "is-active", svc],
                    capture_output=True, text=True, timeout=5
                )
                result[svc] = r.stdout.strip()
            except Exception as e:
                result[svc] = f"error: {e}"

        return result

    # ─────────────────────────────────────
    #  Main run (example)
    # ─────────────────────────────────────
    def run(self):
        """Main execution loop"""
        logger.info("Guardian Agent started")
        while True:
            try:
                # Check services
                services = self.check_services()
                logger.info(f"Services status: {services}")

                # Save state periodically
                self._save_state()

            except Exception as e:
                logger.error(f"Main loop error: {e}")

            time.sleep(300)  # 5 minutes between service checks


if __name__ == "__main__":
    guardian = GuardianAgent()
    guardian.run()