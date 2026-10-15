# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

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
from self_evolve import SelfEvolve
from cloud_fallback import CloudFallback
from github_evolve import GitHubEvolve
from guardian_agent import GuardianAgent
from log_analyzer import LogAnalyzer
from daily_digest import DailyDigest
from pharos_agent import PharosAgent
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
evolve = SelfEvolve()
cloud = CloudFallback()
github_evolve = GitHubEvolve()
guardian = GuardianAgent()
analyzer = LogAnalyzer()
digest = DailyDigest()
pharos = PharosAgent()

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
    """مزامنة GitHub (git CLI)"""
    result = {"name": "github_sync", "status": "ok"}

    # git CLI شغال دايماً (PyGithub اختياري)
    if not github.git_status().get("remote"):
        result["status"] = "skipped"
        result["reason"] = "GitHub remote ناقص"
        return result

    # git CLI كيدير add -A (المشروع كامل)
    push = github.push_files(
        message=f"⚡ Auto-sync ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
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
    """مزامنة الإيردروبات من RSS + scrapers + scoring ذكي"""
    result = {"name": "airdrop_sync", "status": "ok"}
    try:
        # ── RSS feeds ──
        items = airdrop_agent.fetch_all()
        new = airdrop_agent.save_airdrops(items)
        total = airdrop_agent.count()

        result["fetched"] = len(items)
        result["new"] = new
        result["total"] = total

        # ── Specialized scrapers (airdrops.io, CMC, GitHub) ──
        try:
            from airdrop_scraper import scrape_all
            scraped = scrape_all()
            result["scraped"] = len(scraped)
            items = items + scraped
        except Exception as se:
            result["scrape_error"] = str(se)

        # ── Smart scoring with deep enrichment ──
        from airdrop_scorer import score_all, top_candidates, format_telegram
        score_all(items, enrich=True, enrich_limit=20, deep_enrich=True)
        cands = top_candidates(limit=5, min_grade="B")
        result["grade_A"] = sum(1 for c in cands if c["grade"] == "A")
        result["grade_B"] = sum(1 for c in cands if c["grade"] == "B")
        result["deep_enriched"] = True

        # إشعار إذا كان هناك جديد
        if new > 0:
            send_telegram(
                f"📡 *إيردروبات جديدة!*\n\n"
                f"🆕 جديد: `{new}`\n"
                f"📊 الإجمالي: `{total}`\n\n"
                f"_أرسل /airdrops لعرض أحدث 5_"
            )

        # ── إشعار الفرص المؤهلة (Grade A/B) ──
        if cands:
            digest = format_telegram(limit=5)
            send_telegram(digest)
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
def task_github_evolve() -> dict:
    """البحث في GitHub عن تحسينات - كل 24 ساعة"""
    result = {"name": "github_evolve", "status": "ok"}
    try:
        run_result = github_evolve.run()
        result.update(run_result)

        if run_result.get("status") == "ok" and run_result.get("suggestions_count", 0) > 0:
            count = run_result["suggestions_count"]
            send_telegram(
                f"🔍 *GitHub Evolve*\n\n"
                f"📊 مستودعات: `{run_result['results_count']}`\n"
                f"🧬 اقتراحات جديدة: `{count}`\n\n"
                f"_استخدم /evolve للعرض_"
            )
            notify.info(
                "🔍 GitHub Evolve",
                f"{count} اقتراح جديد من GitHub"
            )
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result

def task_self_evolve() -> dict:
    """تحليل وتوليد اقتراحات التطوير الذاتي"""
    result = {"name": "self_evolve", "status": "ok"}
    try:
        suggestions = evolve.suggest_improvements()
        result["suggestions_count"] = len(suggestions)

        if suggestions:
            notify.info(
                "🧠 اقتراحات تطوير جديدة",
                f"{len(suggestions)} اقتراح | استخدم /evolve في Telegram"
            )
            send_telegram(
                f"🧠 *اقتراحات تطوير جديدة*\n\n"
                f"📊 عدد: `{len(suggestions)}`\n\n"
                f"_استخدم /evolve للعرض_"
            )
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def task_cloud_health() -> dict:
    """مراقبة حالة Cloud/Internet"""
    result = {"name": "cloud_health", "status": "ok"}
    try:
        online = cloud.is_online(force=True)
        result["online"] = online

        if not online:
            # إشعار عند انقطاع الإنترنت
            notify.warning(
                "⚠️ الإنترنت مقطوع",
                "التبديل إلى Local (qwen2.5:3b)"
            )
            result["status"] = "offline"
        else:
            result["cloud_model"] = cloud.state.get("cloud_requests", 0)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def task_guardian() -> dict:
    """حراسة وإصلاح تلقائي - كل 5 دقائق"""
    result = {"name": "guardian", "status": "ok"}
    try:
        check = guardian.full_check()
        result["errors"] = check["errors_count"]
        result["fixes"] = len(check["fixes"])

        # إشعار فقط عند وجود إصلاحات
        if check["fixes"]:
            fixes_text = chr(10).join("- " + f["action"] for f in check["fixes"])
            send_telegram(
                "🛡️ *Guardian أصلح أخطاء*" + chr(10) + chr(10) +
                "🔧 " + str(len(check["fixes"])) + " إصلاح" + chr(10) +
                fixes_text
            )
            notify.info(
                "🛡️ Guardian",
                str(len(check["fixes"])) + " إصلاح تلقائي"
            )

        # إشعار عند أخطاء لم تُصلح
        if check["errors_count"] > 0 and not check["fixes"]:
            logger.warning(f"⚠️ {check['errors_count']} خطأ بدون إصلاح")
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result

def task_log_analysis() -> dict:
    """تحليل السجلات - يومياً"""
    result = {"name": "log_analysis", "status": "ok"}
    try:
        r = analyzer.analyze()
        result["status"] = r.get("status", "unknown")

        if r.get("status") == "ok":
            stats = r["report"]["stats"]
            analysis = r["report"].get("analysis", "")[:300]

            send_telegram(
                "📊 *تحليل السجلات*" + chr(10) + chr(10) +
                f"أخطاء: `{stats['errors']}`" + chr(10) +
                f"تحذيرات: `{stats['warnings']}`" + chr(10) + chr(10) +
                analysis
            )
            notify.info(
                "📊 تحليل السجلات",
                f"{stats['errors']} خطأ، {stats['warnings']} تحذير"
            )
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result

def task_daily_digest() -> dict:
    """تقرير يومي شامل - كل 24 ساعة"""
    result = {"name": "daily_digest", "status": "ok"}
    try:
        text = digest.format_telegram()
        send_telegram(text)

        # نسخة بالبريد
        email_result = digest.send_email()
        result["email"] = email_result.get("status", "unknown")

        notify.info("📊 التقرير اليومي", "تم الإرسال")
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result

def task_pharos() -> dict:
    """مراقبة Pharos Testnet - كل ساعة"""
    result = {"name": "pharos", "status": "ok"}
    try:
        balance = pharos.get_balance()
        result["balance"] = balance.get("balance", "0")
        result["connected"] = balance.get("connected", False)

        # إشعار إذا كان Faucet جاهزاً
        if pharos.can_claim():
            notify.info(
                "🔷 Pharos Faucet جاهز",
                "افتح: https://testnet.pharosnetwork.xyz"
            )
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
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
    "cloud_health": 5 * 60,
    "guardian": 5 * 60,
    "log_analysis": 24 * 60 * 60,
    "pharos": 60 * 60,
    "airdrop_sync": 6 * 60 * 60,
    "agent_mesh": 3 * 60 * 60,
    "cloud_bridge": 10 * 60,
    "weekly_email": 60 * 60,
    "self_evolve": 24 * 60 * 60,
    "github_evolve": 24 * 60 * 60,
    "daily_digest": 24 * 60 * 60,
    "health_check": 5 * 60,
    "security_scan": 60 * 60,
    "github_sync": 60 * 60,
    "daily_report": 6 * 60 * 60,
    # ═══ المهام الجديدة v2 ═══
    "research_monitor": 6 * 60 * 60,       # كل 6 ساعات
    "semantic_memory": 60 * 60,            # كل ساعة
    "analytics_report": 12 * 60 * 60,      # كل 12 ساعة
    "guardian_check": 60 * 60,             # كل ساعة
    "inference_test": 2 * 60 * 60,         # كل ساعتين
    # ═══ Sunna bots ═══
    "sunna_veille": 6 * 60 * 60,           # كل 6 ساعات
    "sunna_prices": 24 * 60 * 60,          # يومياً
    "sunna_facture_check": 24 * 60 * 60,   # يومياً
    "sunna_offres": 12 * 60 * 60,          # كل 12 ساعة
}


def task_research_monitor() -> dict:
    try:
        from research_monitor import ResearchMonitor
        rm = ResearchMonitor()
        report = rm.run()
        return {"status": "ok", "new_items": report["total_new"]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def task_semantic_memory() -> dict:
    try:
        from semantic_memory_v2 import SemanticMemory
        from datetime import datetime
        sm = SemanticMemory()
        sm.remember(f"دورة {datetime.now().isoformat()}", category="conversation", tags=["auto"], importance=0.3)
        return {"status": "ok", "total": sm.stats()["total"]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def task_analytics_report() -> dict:
    try:
        from analytics import Analytics
        a = Analytics()
        return {"status": "ok", "total_events": a.report(days=1)["total_events"]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def task_guardian_check() -> dict:
    try:
        from guardian_v2 import Guardian
        g = Guardian()
        return {"status": "ok", "stats": g.stats()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def task_inference_test() -> dict:
    try:
        from inference_router import get_provider
        return {"status": "ok", "routing": {
            "simple": get_provider("hi")["provider"],
            "medium": get_provider("مقالة")["provider"],
            "complex": get_provider("حلل")["provider"],
            "sensitive": get_provider("محفظة")["provider"],
        }}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════
#  Sunna bot tasks (wired from ~/Desktop/Sunna-Equipe-Industrial/bots)
# ═══════════════════════════════════════
SUNNA_BOTS = Path.home() / "Desktop" / "Sunna-Equipe-Industrial" / "bots"
PY = str(BASE_DIR / ".venv" / "Scripts" / "python.exe")


def _run_sunna_bot(script: str, args: list = None, timeout: int = 180) -> dict:
    """Run a Sunna bot script and return its output."""
    script_path = SUNNA_BOTS / script
    if not script_path.exists():
        return {"status": "error", "error": f"not found: {script}"}
    cmd = [PY, str(script_path)] + (args or [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(SUNNA_BOTS.parent))
        out = (r.stdout or "").strip()
        return {"status": "ok" if r.returncode == 0 else "error",
                "output": out[-2000:], "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def task_sunna_veille() -> dict:
    """Veille — GitHub repo monitoring (187→500 repos)."""
    result = {"name": "sunna_veille", "status": "ok"}
    try:
        run_result = _run_sunna_bot("veille_bot.py", ["run"])
        result.update(run_result)
        if run_result.get("status") == "ok":
            out = run_result.get("output", "")
            # extract total line if present
            for line in out.splitlines():
                if "المجموع" in line or "جديد" in line:
                    result["summary"] = line.strip()
                    break
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def task_sunna_prices() -> dict:
    """Live steel/galva/zinc price tracker."""
    result = {"name": "sunna_prices", "status": "ok"}
    try:
        run_result = _run_sunna_bot("sunna_price_tracker.py", ["run"])
        result.update(run_result)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def task_sunna_facture_check() -> dict:
    """Check factures built today (facture_builder.py list)."""
    result = {"name": "sunna_facture_check", "status": "ok"}
    try:
        run_result = _run_sunna_bot("facture_builder.py", ["--list"])
        result.update(run_result)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def task_sunna_offres() -> dict:
    """Offres bot — offers/scraping."""
    result = {"name": "sunna_offres", "status": "ok"}
    try:
        run_result = _run_sunna_bot("offres_bot.py", ["run"])
        result.update(run_result)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def task_agent_mesh() -> dict:
    """Agent mesh cycle — agents talk to each other and evolve the system."""
    result = {"name": "agent_mesh", "status": "ok"}
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://127.0.0.1:11437/cycle",
            data=json.dumps({"rounds": 1}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=540) as r:
            mesh = json.loads(r.read())
        result["agents_thought"] = mesh.get("agents_thought", 0)
        result["board_total"] = mesh.get("board_total", 0)
        # surface any proposed tasks
        tasks = [r for r in mesh.get("results", []) if r.get("task")]
        if tasks:
            result["proposed_tasks"] = [
                {"agent": t["agent"], "title": t["task"]["title"][:100]}
                for t in tasks
            ]
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]
    return result


def task_cloud_bridge() -> dict:
    """GitHub cloud bridge — pull cloud commands, execute them, push results."""
    result = {"name": "cloud_bridge", "status": "ok"}
    try:
        sys.path.insert(0, str(BASE_DIR))
        import cloud_poller
        report = cloud_poller.poll_once()
        result["pulled"] = report.get("pull", False)
        result["executed"] = len(report.get("executed", []))
        result["pushed"] = report.get("pushed", False)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]
    return result


def run_cycle(state: dict):
    """دورة واحدة"""
    logger.info(f"═══ دورة #{state['cycles']} ═══")

    tasks = {
        "vpn_check": task_vpn_check,
        "guardian": task_guardian,
        "log_analysis": task_log_analysis,
        "pharos": task_pharos,
        "daily_digest": task_daily_digest,
        "cloud_health": task_cloud_health,
        "airdrop_sync": task_airdrop_sync,
        "agent_mesh": task_agent_mesh,
        "cloud_bridge": task_cloud_bridge,
        "weekly_email": task_weekly_email,
        "self_evolve": task_self_evolve,
        "github_evolve": task_github_evolve,
        "health_check": task_health_check,
        "security_scan": task_security_scan,
        "github_sync": task_github_sync,
        "research_monitor": task_research_monitor,
        "semantic_memory": task_semantic_memory,
        "analytics_report": task_analytics_report,
        "guardian_check": task_guardian_check,
        "inference_test": task_inference_test,
        "sunna_veille": task_sunna_veille,
        "sunna_prices": task_sunna_prices,
        "sunna_facture_check": task_sunna_facture_check,
        "sunna_offres": task_sunna_offres,
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
            time.sleep(300)
    except KeyboardInterrupt:
        logger.info("⏹️ إيقاف يدوي")
        send_telegram("⏹️ EsprieAether توقف يدوياً")


if __name__ == "__main__":
    main()


