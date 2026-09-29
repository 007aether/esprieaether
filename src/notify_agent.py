# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Notify Agent
وكيل الإشعارات عبر ntfy.sh
"""
import os
import json
import logging
import requests
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

NTFY_TOPIC = os.getenv("NTFY_TOPIC", "esprieaether-007")
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh")

logger = logging.getLogger("notify_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class NotifyAgent:
    """وكيل إشعارات ntfy.sh"""

    def __init__(self):
        self.topic = NTFY_TOPIC
        self.server = NTFY_SERVER.rstrip("/")
        self.enabled = bool(self.topic)

    def send(self, title: str, message: str,
             priority: str = "default", tags: list = None,
             click_url: str = None) -> dict:
        """
        إرسال إشعار
        priority: min, low, default, high, urgent
        tags: مثل ["warning", "robot"]
        """
        if not self.enabled:
            return {"status": "disabled", "reason": "NTFY_TOPIC غير مُعدّ"}

        try:
            headers = {
                "Title": title.encode("utf-8").decode("latin-1", errors="ignore"),
                "Priority": priority,
                "Content-Type": "text/plain; charset=utf-8",
            }
            if tags:
                headers["Tags"] = ",".join(tags)
            if click_url:
                headers["Click"] = click_url

            r = requests.post(
                f"{self.server}/{self.topic}",
                data=message.encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            r.raise_for_status()
            logger.info(f"📱 إشعار أُرسل: {title}")
            return {"status": "ok", "topic": self.topic}
        except Exception as e:
            logger.error(f"❌ فشل إرسال الإشعار: {e}")
            return {"status": "error", "error": str(e)}

    def info(self, title: str, message: str):
        return self.send(title, message, priority="low", tags=["information_source"])

    def success(self, title: str, message: str):
        return self.send(title, message, priority="default", tags=["white_check_mark"])

    def warning(self, title: str, message: str):
        return self.send(title, message, priority="high", tags=["warning"])

    def urgent(self, title: str, message: str):
        return self.send(title, message, priority="urgent", tags=["rotating_light"])


if __name__ == "__main__":
    print("═" * 60)
    print("📱 Notify Agent Test")
    print("═" * 60)

    agent = NotifyAgent()
    print(f"📡 Topic: {agent.topic}")
    print(f"🌐 Server: {agent.server}")
    print()

    result = agent.success(
        "⚡ EsprieAether",
        f"اختبار الإشعارات — {datetime.now().strftime('%H:%M:%S')}"
    )
    print(f"✅ النتيجة: {result}")
