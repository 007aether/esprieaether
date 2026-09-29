# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Smart Alerts
تنبيهات ذكية: يقرر JARVIS أيها مهم
"""
import os
import re
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("smart_alerts")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

ALERTS_LOG = BASE_DIR / "smart_alerts_log.json"


class SmartAlerts:
    """تنبيهات ذكية"""

    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if ALERTS_LOG.exists():
            try:
                return json.loads(ALERTS_LOG.read_text())
            except Exception:
                pass
        return {"alerts": [], "suppressed": []}

    def _save_state(self):
        ALERTS_LOG.write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False)
        )

    # ─────────────────────────────────────
    #  قواعد التنبيه الذكية
    # ─────────────────────────────────────
    def should_alert(self, event_type: str, event_data: dict) -> bool:
        """هل يجب التنبيه؟"""
        now = datetime.now()

        # قاعدة 1: لا تنبيه متكرر خلال 15 دقيقة
        recent = [
            a for a in self.state["alerts"]
            if a["type"] == event_type
            and datetime.fromisoformat(a["timestamp"]) > now - timedelta(minutes=15)
        ]
        if recent:
            logger.info(f"🔇 تنبيه {event_type} مُكتوم (تكرار)")
            return False

        # قاعدة 2: حوادث حرجة → تنبيه فوري
        critical = ["service_down", "internet_down", "vpn_down", "code_error"]
        if event_type in critical:
            return True

        # قاعدة 3: الحوادث العادية → فقط إذا تكررت 3 مرات/ساعة
        if event_type == "service_restart":
            count = len([
                a for a in self.state["alerts"]
                if a["type"] == "service_restart"
                and datetime.fromisoformat(a["timestamp"]) > now - timedelta(hours=1)
            ])
            if count >= 3:
                return True
            return False

        # قاعدة 4: الأحداث الجديدة → تنبيه
        if event_type == "first_time":
            return True

        return True

    def alert(self, event_type: str, message: str, priority: str = "default") -> dict:
        """إرسال تنبيه ذكي"""
        if not self.should_alert(event_type, {}):
            return {"status": "suppressed", "type": event_type}

        # سجل التنبيه
        alert_record = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message[:200],
            "priority": priority,
        }
        self.state["alerts"].append(alert_record)
        # احتفظ بآخر 200
        self.state["alerts"] = self.state["alerts"][-200:]
        self._save_state()

        # أرسل عبر ntfy
        try:
            from notify_agent import NotifyAgent
            n = NotifyAgent()
            if priority == "urgent":
                n.urgent("🚨 " + event_type, message)
            elif priority == "high":
                n.warning("⚠️ " + event_type, message)
            else:
                n.info("ℹ️ " + event_type, message)
        except Exception as e:
            logger.error(f"ntfy فشل: {e}")

        logger.info(f"📢 تنبيه: {event_type} — {message[:60]}")
        return {"status": "sent", "type": event_type}

    # ─────────────────────────────────────
    #  تنبيهات محددة
    # ─────────────────────────────────────
    def alert_service_down(self, service: str):
        return self.alert(
            "service_down",
            f"الخدمة {service} متوقفة",
            priority="high"
        )

    def alert_service_restarted(self, service: str):
        return self.alert(
            "service_restart",
            f"Guardian أعاد تشغيل {service}",
            priority="default"
        )

    def alert_internet_down(self):
        return self.alert(
            "internet_down",
            "الإنترنت مقطوع — التبديل إلى Local",
            priority="high"
        )

    def alert_cloud_failure(self, error: str):
        return self.alert(
            "cloud_failure",
            f"Cloud فشل: {error[:80]}",
            priority="default"
        )

    def alert_code_error(self, file: str, error: str):
        return self.alert(
            "code_error",
            f"خطأ في {file}: {error[:80]}",
            priority="urgent"
        )

    def alert_airdrop_new(self, count: int):
        if count >= 5:
            return self.alert(
                "airdrop_bulk",
                f"{count} إيردروب جديد — تحقق من /airdrops",
                priority="default"
            )
        return {"status": "skipped"}

    # ─────────────────────────────────────
    #  التقرير
    # ─────────────────────────────────────
    def get_stats(self) -> dict:
        now = datetime.now()
        last_24h = [
            a for a in self.state["alerts"]
            if datetime.fromisoformat(a["timestamp"]) > now - timedelta(hours=24)
        ]

        by_type = {}
        for a in last_24h:
            by_type[a["type"]] = by_type.get(a["type"], 0) + 1

        return {
            "total": len(self.state["alerts"]),
            "last_24h": len(last_24h),
            "by_type": by_type,
        }

    def format_telegram(self) -> str:
        s = self.get_stats()
        text = "🔔 *Smart Alerts*" + chr(10) + chr(10)
        text += f"📊 إجمالي: `{s['total']}`" + chr(10)
        text += f"📅 آخر 24 ساعة: `{s['last_24h']}`" + chr(10)
        if s["by_type"]:
            text += chr(10) + "*حسب النوع:*" + chr(10)
            for t, c in sorted(s["by_type"].items(), key=lambda x: -x[1])[:5]:
                text += f"• `{t}`: {c}" + chr(10)
        return text


if __name__ == "__main__":
    print("═" * 60)
    print("🔔 Smart Alerts Test")
    print("═" * 60)

    s = SmartAlerts()

    # اختبارات
    print("\n▶ اختبار 1: تنبيه خدمة")
    r = s.alert_service_down("aether-bot")
    print(f"  {r}")

    print("\n▶ اختبار 2: تنبيه متكرر (يُكتَم)")
    r = s.alert_service_down("aether-bot")
    print(f"  {r}")

    print("\n▶ اختبار 3: الإنترنت مقطوع")
    r = s.alert_internet_down()
    print(f"  {r}")

    print("\n▶ الإحصائيات:")
    print(s.format_telegram())
