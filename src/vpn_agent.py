# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - VPN Agent
وكيل التحكم بـ WireGuard VPN
"""
import os
import re
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

VPN_INTERFACE = os.getenv("VPN_INTERFACE", "aether-nl")
VPN_CONFIG_PATH = f"/etc/wireguard/{VPN_INTERFACE}.conf"

logger = logging.getLogger("vpn_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class VPNAgent:
    """وكيل التحكم بـ WireGuard VPN"""

    def __init__(self, interface: str = VPN_INTERFACE):
        self.interface = interface

    # ─────────────────────────────────────
    #  فحص الحالة
    # ─────────────────────────────────────
    def is_active(self) -> bool:
        """هل VPN يعمل؟"""
        try:
            r = subprocess.run(
                ["ip", "link", "show", self.interface],
                capture_output=True, text=True, timeout=5
            )
            return r.returncode == 0
        except Exception:
            return False

    def get_ip(self, ipv4: bool = True) -> str:
        """الحصول على IP العام"""
        try:
            flag = "-4" if ipv4 else "-6"
            r = subprocess.run(
                ["curl", flag, "-s", "--max-time", "10", "ifconfig.me"],
                capture_output=True, text=True, timeout=15
            )
            return r.stdout.strip() or "—"
        except Exception:
            return "—"

    def get_wg_info(self) -> dict:
        """معلومات WireGuard"""
        if not self.is_active():
            return {"active": False}

        try:
            r = subprocess.run(
                ["sudo", "wg", "show", self.interface],
                capture_output=True, text=True, timeout=5
            )
            output = r.stdout

            info = {
                "active": True,
                "interface": self.interface,
                "public_key": "—",
                "endpoint": "—",
                "latest_handshake": "—",
                "transfer": "—",
            }

            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("public key:"):
                    info["public_key"] = line.split(":", 1)[1].strip()
                elif line.startswith("endpoint:"):
                    info["endpoint"] = line.split(":", 1)[1].strip()
                elif line.startswith("latest handshake:"):
                    info["latest_handshake"] = line.split(":", 1)[1].strip()
                elif line.startswith("transfer:"):
                    info["transfer"] = line.split(":", 1)[1].strip()

            return info
        except Exception as e:
            return {"active": True, "error": str(e)}

    # ─────────────────────────────────────
    #  التحكم
    # ─────────────────────────────────────
    def connect(self) -> dict:
        """تشغيل VPN"""
        if self.is_active():
            return {"status": "already_active", "interface": self.interface}

        try:
            r = subprocess.run(
                ["sudo", "wg-quick", "up", self.interface],
                capture_output=True, text=True, timeout=30
            )
            if r.returncode == 0:
                logger.info(f"✅ VPN متصل: {self.interface}")
                return {"status": "connected", "interface": self.interface}
            else:
                logger.error(f"❌ فشل الاتصال: {r.stderr}")
                return {"status": "error", "message": r.stderr.strip()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def disconnect(self) -> dict:
        """إيقاف VPN"""
        if not self.is_active():
            return {"status": "already_down", "interface": self.interface}

        try:
            r = subprocess.run(
                ["sudo", "wg-quick", "down", self.interface],
                capture_output=True, text=True, timeout=30
            )
            if r.returncode == 0:
                logger.info(f"🛑 VPN متوقف: {self.interface}")
                return {"status": "disconnected", "interface": self.interface}
            else:
                return {"status": "error", "message": r.stderr.strip()}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def restart(self) -> dict:
        """إعادة تشغيل VPN"""
        self.disconnect()
        import time
        time.sleep(2)
        return self.connect()

    # ─────────────────────────────────────
    #  تقرير كامل
    # ─────────────────────────────────────
    def full_status(self) -> dict:
        """تقرير كامل"""
        active = self.is_active()
        result = {
            "active": active,
            "interface": self.interface,
            "ipv4": self.get_ip(ipv4=True) if active else "—",
            "ipv6": self.get_ip(ipv4=False) if active else "—",
            "timestamp": datetime.now().isoformat(),
        }
        if active:
            result.update(self.get_wg_info())
        return result

    def format_telegram(self) -> str:
        """تنسيق للتلغرام"""
        s = self.full_status()

        if not s["active"]:
            return f"""
🔴 *VPN غير نشط*

📡 الواجهة: `{self.interface}`
⏰ الوقت: `{datetime.now().strftime('%H:%M:%S')}`

_أرسل `/vpn on` للتشغيل_
"""

        return f"""
🟢 *VPN نشط*

📡 الواجهة: `{s['interface']}`
🌍 IPv4: `{s.get('ipv4', '—')}`
🌐 IPv6: `{s.get('ipv6', '—')}`
🔗 Endpoint: `{s.get('endpoint', '—')}`
🤝 Handshake: `{s.get('latest_handshake', '—')}`
📊 النقل: `{s.get('transfer', '—')}`
⏰ الوقت: `{datetime.now().strftime('%H:%M:%S')}`
"""


# ─────────────────────────────────────
#  اختبار
# ─────────────────────────────────────
if __name__ == "__main__":
    print("═" * 60)
    print("⚡ ESPRIEAETHER - VPN Agent Test")
    print("═" * 60)

    agent = VPNAgent()
    status = agent.full_status()

    print(f"\n▶ الحالة: {'🟢 نشط' if status['active'] else '🔴 غير نشط'}")
    print(f"📡 الواجهة: {status['interface']}")
    if status["active"]:
        print(f"🌍 IPv4: {status['ipv4']}")
        print(f"🌐 IPv6: {status['ipv6']}")
        print(f"🔗 Endpoint: {status.get('endpoint', '—')}")
        print(f"🤝 Handshake: {status.get('latest_handshake', '—')}")
        print(f"📊 النقل: {status.get('transfer', '—')}")

    print("\n▶ تنسيق Telegram:")
    print(agent.format_telegram())
