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
from datetime import datetime, timedelta
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
FIX_COOLDOWN_SECONDS = 300  # 5 دقائق بين كل إصلاح
GUARDIAN_STATE = BASE_DIR / "guardian_state.json"


class GuardianAgent:
    """وكيل مراقبة وإصلاح"""

    def __init__(self):
        self.state = self._load_state()

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
    #  فحص الخدمات
    # ─────────────────────────────────────
    def check_services(self) -> dict:
        """فحص حالة كل الخدمات"""
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
    #  فحص الكود
    # ─────────────────────────────────────
    def check_code(self) -> list:
        """فحص أن كل ملفات Python صحيحة"""
        errors = []
        src_dir = BASE_DIR / "src"

        for py_file in src_dir.glob("*.py"):
            try:
                r = subprocess.run(
                    ["python3", "-m", "py_compile", str(py_file)],
                    capture_output=True, text=True, timeout=15
                )
                if r.returncode != 0:
                    errors.append({
                        "file": py_file.name,
                        "error": r.stderr.strip()[:200],
                    })
            except Exception as e:
                errors.append({
                    "file": py_file.name,
                    "error": str(e)[:200],
                })

        return errors

    # ─────────────────────────────────────
    #  فحص السجلات
    # ─────────────────────────────────────
    def check_logs(self, minutes: int = 5) -> list:
        """ابحث عن أخطاء حديثة في السجلات"""
        errors = []

        log_files = [
            BASE_DIR / "autonomous.log",
            BASE_DIR / "bot.log",
        ]

        cutoff = datetime.now() - timedelta(minutes=minutes)

        for log in log_files:
            if not log.exists():
                continue

            try:
                content = log.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")[-500:]  # آخر 500 سطر

                for line in lines:
                    if "ERROR" in line or "Traceback" in line:
                        errors.append({
                            "log": log.name,
                            "line": line.strip()[:200],
                        })
            except Exception:
                pass

        return errors[-20:]  # آخر 20 خطأ

    # ─────────────────────────────────────
    #  الإصلاحات التلقائية
    # ─────────────────────────────────────
    def can_fix(self) -> bool:
        """هل يمكن الإصلاح الآن؟"""
        # فحص الحد اليومي
        recent_fixes = [
            f for f in self.state["fixes"]
            if datetime.fromisoformat(f["timestamp"]) > datetime.now() - timedelta(hours=1)
        ]

        if len(recent_fixes) >= MAX_FIXES_PER_HOUR:
            return False

        # فحص cooldown
        if recent_fixes:
            last_fix = max(
                datetime.fromisoformat(f["timestamp"]) for f in recent_fixes
            )
            if (datetime.now() - last_fix).seconds < FIX_COOLDOWN_SECONDS:
                return False

        return True

    def fix_service(self, service: str) -> dict:
        """إصلاح خدمة متوقفة"""
        if not self.can_fix():
            return {"status": "cooldown"}

        try:
            r = subprocess.run(
                ["sudo", "systemctl", "restart", service],
                capture_output=True, text=True, timeout=30
            )

            self.state["fixes"].append({
                "timestamp": datetime.now().isoformat(),
                "type": "restart_service",
                "target": service,
                "result": "ok" if r.returncode == 0 else "failed",
            })
            self._save_state()

            if r.returncode == 0:
                self.state["errors_fixed"] += 1
                logger.info(f"✅ إعادة تشغيل {service}")
                return {"status": "ok", "action": f"restart {service}"}
            else:
                self.state["errors_failed"] += 1
                return {"status": "error", "message": r.stderr[:200]}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ─────────────────────────────────────
    #  الفحص الشامل
    # ─────────────────────────────────────
    def full_check(self) -> dict:
        """فحص شامل + إصلاح تلقائي"""
        self.state["checks"] += 1

        result = {
            "timestamp": datetime.now().isoformat(),
            "services": self.check_services(),
            "code_errors": self.check_code(),
            "log_errors": self.check_logs(),
            "fixes": [],
        }

        # احسب الأخطاء
        result["errors_count"] = (
            len([s for s in result["services"].values() if s != "active"]) +
            len(result["code_errors"]) +
            len(result["log_errors"])
        )
        self.state["errors_detected"] += result["errors_count"]

        # حاول الإصلاح
        for svc, status in result["services"].items():
            if status != "active":
                fix = self.fix_service(svc)
                if fix.get("status") == "ok":
                    result["fixes"].append(fix)

        self._save_state()
        return result

    def format_telegram(self) -> str:
        """تنسيق للـ Telegram"""
        s = self.state
        recent_fixes = s["fixes"][-5:]

        text = "🛡️ *Guardian Agent*" + chr(10) + chr(10)
        text += f"📊 فحوصات: `{s['checks']}`" + chr(10)
        text += f"⚠️ أخطاء مكتشفة: `{s['errors_detected']}`" + chr(10)
        text += f"✅ أخطاء مُصلحة: `{s['errors_fixed']}`" + chr(10)
        text += f"❌ فشل: `{s['errors_failed']}`" + chr(10)

        if recent_fixes:
            text += chr(10) + "*آخر 5 إصلاحات:*" + chr(10)
            for f in recent_fixes:
                emoji = "✅" if f["result"] == "ok" else "❌"
                text += f"{emoji} {f['target']} ({f['timestamp'][11:19]})" + chr(10)

        return text


# ─── اختبار ───
if __name__ == "__main__":
    print("═" * 60)
    print("🛡️ Guardian Agent Test")
    print("═" * 60)

    g = GuardianAgent()
    result = g.full_check()

    print(f"\n▶ الخدمات:")
    for svc, status in result["services"].items():
        emoji = "🟢" if status == "active" else "🔴"
        print(f"  {emoji} {svc}: {status}")

    print(f"\n▶ أخطاء الكود: {len(result['code_errors'])}")
    print(f"▶ أخطاء السجلات: {len(result['log_errors'])}")
    print(f"▶ إصلاحات: {len(result['fixes'])}")
    print(f"\n📊 الإجمالي: {result['errors_count']} خطأ")

    print(f"\n{g.format_telegram()}")
