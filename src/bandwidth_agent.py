# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Bandwidth Agent
وكيل مشاركة الإنترنت (بدائل Honeygain على Linux)
"""
import os
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("bandwidth_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# ─── البدائل المتاحة على Linux ───
PROVIDERS = {
    "traffmonetizer": {
        "name": "Traffmonetizer",
        "docker_image": "traffmonetizer/cli_v2",
        "env_var": "TRAFFMONETIZER_TOKEN",
        "payout": "USDT/BTC",
        "status": "available",
    },
    "earnfm": {
        "name": "EarnFM",
        "docker_image": "earnfm/earnfm-client",
        "env_var": "EARNFM_TOKEN",
        "payout": "PayPal",
        "status": "available",
    },
    "repocket": {
        "name": "Repocket",
        "docker_image": "repocket/repocket",
        "env_var": "REPOCKET_EMAIL",
        "payout": "PayPal/Crypto",
        "status": "available",
    },
    "packetstream": {
        "name": "PacketStream",
        "docker_image": "packetstream/psclient",
        "env_var": "PACKETSTREAM_CID",
        "payout": "PayPal",
        "status": "available",
    },
}

HISTORY_FILE = BASE_DIR / "bandwidth_history.json"


class BandwidthAgent:
    """وكيل مشاركة الإنترنت"""

    def __init__(self):
        self.history = self._load_history()

    def _load_history(self) -> dict:
        if HISTORY_FILE.exists():
            try:
                return json.loads(HISTORY_FILE.read_text())
            except Exception:
                pass
        return {"installs": [], "earnings": {}, "started_at": None}

    def _save_history(self):
        HISTORY_FILE.write_text(
            json.dumps(self.history, indent=2, ensure_ascii=False)
        )

    def check_docker(self) -> bool:
        """فحص Docker"""
        try:
            r = subprocess.run(
                ["docker", "--version"],
                capture_output=True, text=True, timeout=5
            )
            return r.returncode == 0
        except Exception:
            return False

    def list_providers(self) -> list:
        """عرض المزودين"""
        result = []
        for key, info in PROVIDERS.items():
            token = os.getenv(info["env_var"], "")
            result.append({
                "key": key,
                "name": info["name"],
                "payout": info["payout"],
                "configured": bool(token),
                "status": info["status"],
            })
        return result

    def install_provider(self, provider_key: str) -> dict:
        """تثبيت مزود"""
        if provider_key not in PROVIDERS:
            return {"status": "error", "message": "مزود غير معروف"}

        if not self.check_docker():
            return {"status": "error", "message": "Docker غير مثبت"}

        info = PROVIDERS[provider_key]
        token = os.getenv(info["env_var"], "")

        if not token:
            return {"status": "error", "message": f"{info['env_var']} غير مُعدّ في .env"}

        container_name = f"aether-{provider_key}"

        # احذف أي حاوية قديمة
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True, timeout=10
        )

        try:
            # شغّل الحاوية
            r = subprocess.run(
                [
                    "docker", "run", "-d",
                    "--name", container_name,
                    "--restart", "unless-stopped",
                    "-e", f"{info['env_var']}={token}",
                    info["docker_image"],
                ],
                capture_output=True, text=True, timeout=30
            )

            if r.returncode == 0:
                self.history["installs"].append({
                    "provider": provider_key,
                    "timestamp": datetime.now().isoformat(),
                    "container_id": r.stdout.strip()[:12],
                })
                self._save_history()
                logger.info(f"✅ {info['name']} يعمل")
                return {"status": "ok", "container": r.stdout.strip()[:12]}
            else:
                return {"status": "error", "message": r.stderr.strip()[:200]}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def stop_provider(self, provider_key: str) -> dict:
        """إيقاف مزود"""
        container_name = f"aether-{provider_key}"
        try:
            r = subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True, text=True, timeout=15
            )
            return {"status": "ok" if r.returncode == 0 else "error"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def status(self) -> dict:
        """حالة كل المزودين"""
        containers = []
        if self.check_docker():
            try:
                r = subprocess.run(
                    ["docker", "ps", "--format", "{{.Names}}|{{.Status}}"],
                    capture_output=True, text=True, timeout=10
                )
                for line in r.stdout.strip().split("\n"):
                    if "aether-" in line:
                        parts = line.split("|")
                        containers.append({
                            "name": parts[0],
                            "status": parts[1] if len(parts) > 1 else "",
                        })
            except Exception:
                pass

        return {
            "docker_available": self.check_docker(),
            "providers": self.list_providers(),
            "running_containers": containers,
        }

    def format_telegram(self) -> str:
        """تنسيق للـ Telegram"""
        s = self.status()
        docker_emoji = "✅" if s["docker_available"] else "❌"

        text = "💰 *Bandwidth Sharing*" + chr(10) + chr(10)
        text += f"{docker_emoji} Docker: {'متاح' if s['docker_available'] else 'غير مثبت'}" + chr(10) + chr(10)

        text += "*المزودون:*" + chr(10)
        for p in s["providers"]:
            emoji = "✅" if p["configured"] else "❌"
            text += f"{emoji} {p['name']} — {p['payout']}" + chr(10)

        if s["running_containers"]:
            text += chr(10) + "*قيد التشغيل:*" + chr(10)
            for c in s["running_containers"]:
                text += f"🟢 {c['name']}" + chr(10)

        return text


if __name__ == "__main__":
    print("═" * 60)
    print("💰 Bandwidth Agent Test")
    print("═" * 60)

    agent = BandwidthAgent()
    print(agent.format_telegram())
