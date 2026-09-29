# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Daily Digest
تقرير يومي شامل
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("daily_digest")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class DailyDigest:
    """مولّد التقرير اليومي"""

    def __init__(self):
        pass

    # ─────────────────────────────────────
    #  جمع البيانات
    # ─────────────────────────────────────
    def collect(self) -> dict:
        """جمع كل البيانات"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().date().isoformat(),
        }

        # 1. الخدمات
        try:
            from guardian_agent import GuardianAgent
            g = GuardianAgent()
            data["services"] = g.check_services()
        except Exception:
            data["services"] = {}

        # 2. Airdrops
        try:
            from airdrop_agent import AirdropAgent
            a = AirdropAgent()
            data["airdrops"] = {
                "total": a.count(),
                "recent": a.get_recent(5),
            }
        except Exception:
            data["airdrops"] = {}

        # 3. VPN
        try:
            from vpn_agent import VPNAgent
            v = VPNAgent()
            data["vpn"] = {
                "active": v.is_active(),
                "ip": v.get_ip(),
            }
        except Exception:
            data["vpn"] = {}

        # 4. Market
        try:
            from market_watcher import MarketWatcher
            m = MarketWatcher()
            data["market"] = {
                "top_movers": m.get_top_movers(3),
                "opportunities": m.find_opportunities()[:3],
            }
        except Exception:
            data["market"] = {}

        # 5. Guardian Stats
        try:
            from guardian_agent import GuardianAgent
            g = GuardianAgent()
            data["guardian"] = {
                "checks": g.state.get("checks", 0),
                "errors_detected": g.state.get("errors_detected", 0),
                "errors_fixed": g.state.get("errors_fixed", 0),
            }
        except Exception:
            data["guardian"] = {}

        # 6. Alerts
        try:
            from smart_alerts import SmartAlerts
            s = SmartAlerts()
            data["alerts"] = s.get_stats()
        except Exception:
            data["alerts"] = {}

        # 7. Autonomous
        try:
            state_file = BASE_DIR / "autonomous_state.json"
            if state_file.exists():
                st = json.loads(state_file.read_text())
                data["autonomous"] = {
                    "cycles": st.get("cycles", 0),
                    "tasks": len(st.get("last_run", {})),
                }
        except Exception:
            data["autonomous"] = {}

        # 8. System
        try:
            import psutil
            data["system"] = {
                "cpu": psutil.cpu_percent(interval=0.5),
                "ram": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage("/").percent,
            }
        except Exception:
            data["system"] = {}

        return data

    # ─────────────────────────────────────
    #  صياغة التقرير
    # ─────────────────────────────────────
    def format_telegram(self) -> str:
        """تنسيق للـ Telegram"""
        d = self.collect()

        text = "📊 *ESPRIEAETHER — تقرير يومي*" + chr(10)
        text += "_" + d["date"] + "_" + chr(10) + chr(10)

        # 1. الخدمات
        services = d.get("services", {})
        active = sum(1 for s in services.values() if s == "active")
        total = len(services)
        text += "🖥️ *الخدمات*: `" + str(active) + "/" + str(total) + "`" + chr(10)
        for name, st in services.items():
            emoji = "🟢" if st == "active" else "🔴"
            text += "  " + emoji + " " + name + chr(10)
        text += chr(10)

        # 2. Airdrops
        airdrops = d.get("airdrops", {})
        if airdrops:
            text += "📡 *الإيردروبات*: `" + str(airdrops.get("total", 0)) + "`" + chr(10)
            for r in airdrops.get("recent", [])[:3]:
                text += "  • " + r["title"][:50] + chr(10)
            text += chr(10)

        # 3. VPN
        vpn = d.get("vpn", {})
        if vpn:
            emoji = "🟢" if vpn.get("active") else "🔴"
            text += "🔐 *VPN*: " + emoji + " `" + vpn.get("ip", "—") + "`" + chr(10) + chr(10)

        # 4. Market
        market = d.get("market", {})
        if market.get("top_movers"):
            text += "📈 *السوق*" + chr(10)
            for m in market["top_movers"][:3]:
                arrow = "🟢" if m["change"] > 0 else "🔴"
                text += "  " + arrow + " " + m["coin"] + ": " + str(m["change"]) + "%" + chr(10)
            text += chr(10)

        # 5. Guardian
        g = d.get("guardian", {})
        if g:
            text += "🛡️ *Guardian*" + chr(10)
            text += "  • فحوصات: `" + str(g.get("checks", 0)) + "`" + chr(10)
            text += "  • إصلاحات: `" + str(g.get("errors_fixed", 0)) + "`" + chr(10) + chr(10)

        # 6. Alerts
        alerts = d.get("alerts", {})
        if alerts:
            text += "🔔 *التنبيهات*: `" + str(alerts.get("last_24h", 0)) + "`" + chr(10) + chr(10)

        # 7. Autonomous
        auto = d.get("autonomous", {})
        if auto:
            text += "🤖 *Autonomous*" + chr(10)
            text += "  • دورات: `" + str(auto.get("cycles", 0)) + "`" + chr(10)
            text += "  • مهام: `" + str(auto.get("tasks", 0)) + "`" + chr(10) + chr(10)

        # 8. System
        sys_data = d.get("system", {})
        if sys_data:
            text += "💻 *النظام*" + chr(10)
            text += "  • CPU: `" + str(sys_data.get("cpu", 0)) + "%`" + chr(10)
            text += "  • RAM: `" + str(sys_data.get("ram", 0)) + "%`" + chr(10)
            text += "  • Disk: `" + str(sys_data.get("disk", 0)) + "%`" + chr(10)

        return text

    def send(self) -> dict:
        """إرسال التقرير"""
        try:
            text = self.format_telegram()

            # Telegram
            from notify_agent import NotifyAgent
            n = NotifyAgent()
            n.info("📊 التقرير اليومي", "التقرير جاهز على Telegram")

            return {"status": "ok", "length": len(text)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def send_email(self) -> dict:
        """إرسال بالبريد"""
        try:
            from email_agent import EmailAgent
            e = EmailAgent()
            if not e.is_configured():
                return {"status": "not_configured"}

            text = self.format_telegram()
            result = e.send_email(
                subject="📊 EsprieAether — تقرير يومي",
                body=text,
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    print("═" * 60)
    print("📊 Daily Digest Test")
    print("═" * 60)

    d = DailyDigest()

    print("\n▶ جمع البيانات...")
    data = d.collect()
    print(f"  ✅ {len(data)} قسم")

    print("\n▶ التقرير:")
    print(d.format_telegram())
