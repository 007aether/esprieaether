"""
⚡ EsprieAether - Autonomous Loop
الحلقة الذكية التي تشغّل كل الوكلاء تلقائياً 24/7
"""
import os
import sys
import json
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# إعداد المسار
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from jarvis_bridge import JarvisBridge
from github_agent import GitHubAgent
from vpn_agent import VPNAgent
from airdrop_agent import AirdropAgent
from email_agent import EmailAgent
from notify_agent import NotifyAgent
# ─── Logger ───
LOG_FILE = BASE_DIR / "autonomous.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("autonomous")

# ─── الوكيلات ───
jarvis = JarvisBridge()
github = GitHubAgent()
vpn = VPNAgent()
airdrop_agent = AirdropAgent()
email_agent = EmailAgent()
notify = NotifyAgent()

# ─── المسارات ───
STATE_FILE = BASE_DIR / "autonomous_state.json"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ═══════════════════════════════════════
#  الحالة
# ═══════════════════════════════════════
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "started_at": datetime.now().isoformat(),
        "cycles": 0,
        "last_run": {},
    }


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


# ═══════════════════════════════════════
#  إرسال Telegram
# ═══════════════════════════════════════
def send_telegram(message: str):
    """إرسال رسالة لبوت Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=30,
        )
    except Exception as e:
        logger.error(f"فشل إرسال Telegram: {e}")


# ═══════════════════════════════════════
#  المهام
# ═══════════════════════════════════════

def task_health_check() -> dict:
    """فحص صحة النظام"""
    result = {"name": "health_check", "status": "ok"}

    # Ollama
    ollama = jarvis.ping()
    result["ollama"] = ollama["status"]

    # الخدمات
    services = {}
    for svc in ["aether-web", "aether-bot"]:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", svc],
                capture_output=True, text=True, timeout=5
            )
            services[svc] = r.stdout.strip()
        except Exception:
            services[svc] = "unknown"
    result["services"] = services

    # psutil
    try:
        import psutil
        result["cpu"] = psutil.cpu_percent(interval=0.5)
        result["ram"] = psutil.virtual_memory().percent
    except Exception:
        pass

    return result


def task_security_scan() -> dict:
    """فحص المنافذ المفتوحة"""
    result = {"name": "security_scan", "status": "ok", "ports": []}
    try:
        r = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True, text=True, timeout=10
        )
        lines = r.stdout.strip().split("\n")[1:]
        for line in lines[:20]:
            parts = line.split()
            if len(parts) >= 4:
                result["ports"].append({
                    "local": parts[3],
                    "process": parts[5] if len(parts) > 5 else "—",
                })
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def task_github_sync() -> dict:
    """مزامنة GitHub"""
    result = {"name": "github_sync", "status": "ok"}

    if not github.gh:
        result["status"] = "skipped"
        result["reason"] = "GitHub غير متصل"
        return result

    files = [
        BASE_DIR / "src" / "jarvis_bridge.py",
        BASE_DIR / "src" / "web_interface.py",
        BASE_DIR / "src" / "bot.py",
        BASE_DIR / "src" / "github_agent.py",
        BASE_DIR / "src" / "autonomous_loop.py",
        BASE_DIR / "STATUS.md",
    ]
    existing = [f for f in files if f.exists()]

    push = github.push_files(
        existing,
        commit_message=f"⚡ Auto-sync {len(existing)} files ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    )
    result["push"] = push
    return result




def task_daily_report() -> dict:
    """تقرير يومي"""
    return {
        "name": "daily_report",
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
    }
def task_weekly_email() -> dict:
    """إرسال التقرير الأسبوعي بالبريد"""
    result = {"name": "weekly_email", "status": "ok"}

    if not email_agent.is_configured():
        result["status"] = "skipped"
        result["reason"] = "SMTP غير مُعدّ"
        return result

    # تحقق من اليوم والساعة
    import datetime
    now = datetime.datetime.now()
    target_day = os.getenv("WEEKLY_REPORT_DAY", "monday").lower()
    target_hour = int(os.getenv("WEEKLY_REPORT_HOUR", "9"))

    days_map = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    target_weekday = days_map.get(target_day, 0)

    # إذا لم يكن اليوم والساعة، تخطَّ
    if now.weekday() != target_weekday:
        result["status"] = "skipped"
        result["reason"] = f"ليس يوم {target_day}"
        return result

    if now.hour != target_hour:
        result["status"] = "skipped"
        result["reason"] = f"ليس الساعة {target_hour}"
        return result

    # أرسل البريد
    try:
        send_result = email_agent.send_weekly_report()
        result["email"] = send_result

        if send_result.get("status") == "ok":
            send_telegram("📧 *تم إرسال التقرير الأسبوعي بالبريد*")
        else:
            result["status"] = "error"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result
def task_airdrop_sync() -> dict:
    """مزامنة الإيردروبات من RSS"""
    result = {"name": "airdrop_sync", "status": "ok"}
    try:
        items = airdrop_agent.fetch_all()
        new = airdrop_agent.save_airdrops(items)
        total = airdrop_agent.count()

        result["fetched"] = len(items)
        result["new"] = new
        result["total"] = total

        # إشعار إذا كان هناك جديد
        if new > 0:
            send_telegram(
                f"📡 *إيردروبات جديدة!*\n\n"
                f"🆕 جديد: `{new}`\n"
                f"📊 الإجمالي: `{total}`\n\n"
                f"_أرسل /airdrops لعرض أحدث 5_"
            )
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        # إشعار ntfy
        if new > 0:
            notify.info(
                "📡 إيردروبات جديدة",
                f"{new} إيردروب جديد | الإجمالي: {total}"
            )  
    return result
def task_vpn_check() -> dict:
    """فحص حالة VPN وإعادة التشغيل تلقائياً إذا توقف"""
    result = {"name": "vpn_check", "status": "ok"}

    if not vpn.is_active():
        logger.warning("⚠️ VPN متوقف — جارٍ إعادة التشغيل...")
        restart_result = vpn.connect()

        if restart_result["status"] == "connected":
            result["action"] = "restarted"
            result["status"] = "restarted"
            send_telegram(
                "🔄 *VPN أُعيد تشغيله تلقائياً*\n"
                f"الواجهة: `{vpn.interface}`"
            )
            notify.warning(
                "🔐 VPN توقف",
                f"تم إعادة التشغيل: {restart_result['status']}"
            )
        else:
            result["status"] = "failed"
            result["error"] = restart_result.get("message")
            send_telegram(
                f"⚠️ *VPN متوقف ولم يُعد تشغيله*\n"
                f"السبب: `{restart_result.get('message', 'خطأ')}`"
            )
    else:
        info = vpn.get_wg_info()
        result["ip"] = vpn.get_ip(ipv4=True)
        result["handshake"] = info.get("latest_handshake", "—")

    return result
def should_run(state: dict, task_name: str, interval: int) -> bool:
    """هل يجب تشغيل المهمة الآن؟"""
    last = state["last_run"].get(task_name)
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        return (datetime.now() - last_dt).total_seconds() >= interval
    except Exception:
        return True


# ═══════════════════════════════════════
#  الحلقة الرئيسية
# ═══════════════════════════════════════

SCHEDULE = {
    "vpn_check": 5 * 60,
    "airdrop_sync": 6 * 60 * 60,
    "weekly_email": 60 * 60,
    "health_check": 5 * 60,
    "security_scan": 60 * 60,
    "github_sync": 60 * 60,
    "daily_report": 6 * 60 * 60,
}


def run_cycle(state: dict):
    """دورة واحدة"""
    logger.info(f"═══ دورة #{state['cycles']} ═══")

    tasks = {
        "vpn_check": task_vpn_check,
        "airdrop_sync": task_airdrop_sync,
        "weekly_email": task_weekly_email,
        "health_check": task_health_check,
        "security_scan": task_security_scan,
        "github_sync": task_github_sync,
            "daily_report": task_daily_report,
    }

    for name, func in tasks.items():
        interval = SCHEDULE[name]
        if not should_run(state, name, interval):
            continue

        try:
            logger.info(f"▶ تشغيل: {name}")
            result = func()
            state["last_run"][name] = datetime.now().isoformat()
            logger.info(f"✅ {name}: {result.get('status')}")

            # إشعارات خاصة
            if name == "somnia_check" and result.get("balance_stt"):
                logger.info(f"💰 Somnia: {result['balance_stt']} STT")

            if name == "daily_report":
                send_telegram(format_report(state, result))

        except Exception as e:
            logger.error(f"❌ {name}: {e}")

    state["cycles"] += 1
    save_state(state)

def format_report(state: dict, report: dict) -> str:
    """تنسيق تقرير Telegram"""
    return f"""
⚡ *EsprieAether — تقرير دوري*

📊 *الحالة العامة*
• الدورات: `{state['cycles']}`
• آخر تحديث: `{report['timestamp'][:19]}`

🔍 *آخر فحوصات:*
• Health: `{state['last_run'].get('health_check', '—')[:19]}`
• GitHub: `{state['last_run'].get('github_sync', '—')[:19]}`
• Somnia: `{state['last_run'].get('somnia_check', '—')[:19]}`

_التقرير التالي بعد 6 ساعات_
"""


def main():
    """بدء الحلقة"""
    logger.info("═" * 60)
    logger.info("⚡ ESPRIEAETHER — AUTONOMOUS LOOP")
    logger.info("═" * 60)

    state = load_state()
    logger.info(f"📂 بدء من الدورة: {state['cycles']}")
    logger.info(f"⏰ وقت البدء: {state['started_at']}")

    # إشعار البداية
    send_telegram(
        f"🚀 *EsprieAether بدأ التشغيل*\n"
        f"الدورات السابقة: `{state['cycles']}`\n"
        f"الوقت: `{datetime.now().strftime('%H:%M:%S')}`"
    )

    try:
        while True:
            try:
                run_cycle(state)
            except Exception as e:
                logger.error(f"خطأ في الدورة: {e}")

            # انتظار 60 ثانية بين الفحوصات
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("⏹️ إيقاف يدوي")
        send_telegram("⏹️ EsprieAether توقف يدوياً")


if __name__ == "__main__":
    main()
