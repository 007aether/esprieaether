"""
⚡ EsprieAether - Command Router
موجّه الأوامر: regex أساسي + Needle احتياطي
"""
import re
import json
import logging
import subprocess
import requests
from pathlib import Path
from datetime import datetime

BASE_DIR = Path.home() / "AETHER_V8"

logger = logging.getLogger("command_router")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


# ═══════════════════════════════════════
#  Regex Patterns (المسار الأساسي)
# ═══════════════════════════════════════
COMMAND_PATTERNS = [
    # إرسال التقرير
    (r"(أرسل|ابعث|ارسل|بعث).*(تقرير|report|أسبوعي|weekly)", "send_report"),
    (r"(تقرير|report).*(أرسل|ابعث|ارسل)", "send_report"),

    # فحص المنافذ
    (r"(افحص|افتح|فحص|تحقق).*(منافذ|ports|بورت)", "scan_ports"),
    (r"(منافذ|ports).*(افحص|افتح|فحص)", "scan_ports"),

    # حالة VPN
    (r"(حالة|status|وضع).*(vpn|في بي|فيبي)", "get_vpn_status"),
    (r"(vpn|في بي).*(حالة|status|وضع|شغال|مشتغل)", "get_vpn_status"),

    # مزامنة GitHub
    (r"(زامن|sync|ارفع|رابط).*(github|جيتهاب|جيت|git)", "sync_github"),
    (r"(github|git|جيت).*(زامن|sync|ارفع)", "sync_github"),

    # عرض الإيردروبات
    (r"(اعرض|أظهر|اظهر|هات|جيب).*(ايردروب|airdrop|إيردروب)", "get_airdrops"),
    (r"(ايردروب|airdrop).*(اعرض|أظهر|هات|جديد|أحدث)", "get_airdrops"),

    # حالة الخدمات
    (r"(حالة|status).*(خدمات|services|خدمة|systemd)", "get_services"),
    (r"(خدمات|services).*(حالة|status)", "get_services"),

    # إعادة تشغيل core
    (r"(أعد|اعد|restart|شغل).*(تشغيل|core|نواة|النواة)", "restart_core"),
    (r"(restart|أعد).*(aether|core|esprieaether)", "restart_core"),

    # إحصائيات
    (r"(احصائيات|إحصائيات|stats|ملخص).*(نظام|system)", "get_stats"),
    (r"(نظام|system).*(احصائيات|إحصائيات|stats)", "get_stats"),
    (r"(cpu|ram|ذاكرة|معالج)", "get_stats"),

    # حالة JARVIS
    (r"(jarvis|جارفيس).*(حالة|status)", "get_jarvis_status"),

    # إحصائيات الإيردروبات
    (r"(كم|عدد).*(ايردروب|airdrop|إيردروب)", "count_airdrops"),
    (r"(ايردروب|airdrop).*(كم|عدد)", "count_airdrops"),

    # حالة JARVIS
    (r"(jarvis|جارفيس).*(حالة|status|شغال)", "get_jarvis_status"),
    (r"(حالة|status).*(jarvis|جارفيس)", "get_jarvis_status"),

    # حالة Ollama
    (r"(ollama|أولاما|اولاما).*(حالة|status)", "get_ollama_status"),
    (r"(حالة|status).*(ollama|أولاما)", "get_ollama_status"),
]


# ═══════════════════════════════════════
#  Router Class
# ═══════════════════════════════════════
class CommandRouter:
    """موجّه الأوامر"""

    def __init__(self):
        self.needle = None
        self.needle_loaded = False

    def load_needle(self):
        """تحميل Needle كاحتياطي"""
        if self.needle_loaded:
            return True
        try:
            from needle_agent import NeedleAgent, get_default_tools
            self.needle = NeedleAgent()
            for name, desc in get_default_tools():
                self.needle.register_tool(name, desc)
            self.needle_loaded = True
            logger.info("✅ Needle محمّل كاحتياطي")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Needle غير متاح: {e}")
            return False

    def match_regex(self, text: str):
        """البحث عن تطابق regex"""
        for pattern, action in COMMAND_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return action
        return None

    def route(self, text: str) -> dict:
        """توجيه الأمر"""
        # 1. المسار الأساسي: regex
        action = self.match_regex(text)
        if action:
            logger.info(f"✅ regex → {action}")
            return {
                "status": "ok",
                "source": "regex",
                "action": action,
                "input": text,
            }

        # 2. المسار الاحتياطي: Needle
        logger.info("⚠️ regex فشل — جاري Needle...")
        if self.load_needle() and self.needle:
            result = self.needle.parse_command(text)
            if result["status"] == "ok":
                action = result["tool_calls"][0]["name"]
                logger.info(f"✅ Needle → {action}")
                return {
                    "status": "ok",
                    "source": "needle",
                    "action": action,
                    "input": text,
                }

        # 3. الفشل
        return {
            "status": "no_match",
            "message": "لم أفهم الأمر",
            "input": text,
        }


# ═══════════════════════════════════════
#  Executor (تنفيذ الأوامر)
# ═══════════════════════════════════════
class CommandExecutor:
    """منفّذ الأوامر"""

    def execute(self, action: str) -> dict:
        """تنفيذ الأمر"""
        handlers = {
            "send_report": self.send_report,
            "scan_ports": self.scan_ports,
            "get_vpn_status": self.get_vpn_status,
            "sync_github": self.sync_github,
            "get_airdrops": self.get_airdrops,
            "get_services": self.get_services,
            "restart_core": self.restart_core,
            "get_stats": self.get_stats,
            "get_jarvis_status": self.get_jarvis_status,
            "count_airdrops": self.count_airdrops,
            "get_ollama_status": self.get_ollama_status,
        }

        handler = handlers.get(action)
        if not handler:
            return {"status": "error", "message": f"أداة غير معروفة: {action}"}

        try:
            return handler()
        except Exception as e:
            logger.error(f"❌ {action}: {e}")
            return {"status": "error", "message": str(e)}

    def send_report(self) -> dict:
        """إرسال التقرير"""
        from email_agent import EmailAgent
        agent = EmailAgent()
        if not agent.is_configured():
            return {"status": "error", "message": "SMTP غير مُعدّ"}
        result = agent.send_weekly_report()
        return {"status": result.get("status"), "message": "تم إرسال التقرير"}

    def scan_ports(self) -> dict:
        """فحص المنافذ"""
        r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=10)
        lines = r.stdout.strip().split("\n")[1:]
        ports = [l.split()[3] for l in lines if len(l.split()) >= 4]
        return {"status": "ok", "ports": ports[:10], "count": len(ports)}

    def get_vpn_status(self) -> dict:
        """حالة VPN"""
        from vpn_agent import VPNAgent
        vpn = VPNAgent()
        return {
            "status": "ok",
            "active": vpn.is_active(),
            "ip": vpn.get_ip(),
        }

    def sync_github(self) -> dict:
        """مزامنة GitHub"""
        from github_agent import GitHubAgent
        agent = GitHubAgent()
        files = [
            BASE_DIR / "src" / "jarvis_bridge.py",
            BASE_DIR / "src" / "web_interface.py",
            BASE_DIR / "src" / "bot.py",
            BASE_DIR / "src" / "autonomous_loop.py",
        ]
        existing = [f for f in files if f.exists()]
        result = agent.push_files(existing, "🤖 Auto-sync from /run")
        return {"status": result.get("status"), "sha": result.get("sha", "")}

    def get_airdrops(self) -> dict:
        """عرض الإيردروبات"""
        from airdrop_agent import AirdropAgent
        agent = AirdropAgent()
        recent = agent.get_recent(5)
        return {"status": "ok", "total": agent.count(), "recent": recent}

    def get_services(self) -> dict:
        """حالة الخدمات"""
        services = {}
        for svc in ["aether-web", "aether-bot", "aether-core", "ollama"]:
            r = subprocess.run(["systemctl", "is-active", svc],
                             capture_output=True, text=True, timeout=5)
            services[svc] = r.stdout.strip()
        return {"status": "ok", "services": services}

    def restart_core(self) -> dict:
        """إعادة تشغيل core"""
        r = subprocess.run(["sudo", "systemctl", "restart", "aether-core"],
                         capture_output=True, text=True, timeout=15)
        return {"status": "ok" if r.returncode == 0 else "error"}

    def get_stats(self) -> dict:
        """إحصائيات النظام"""
        import psutil
        return {
            "status": "ok",
            "cpu": psutil.cpu_percent(interval=0.5),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent,
        }

    def get_jarvis_status(self) -> dict:
        """حالة JARVIS"""
        from jarvis_bridge import JarvisBridge
        return {"status": "ok", "jarvis": JarvisBridge().ping()["status"]}

    def count_airdrops(self) -> dict:
        """عدّ الإيردروبات"""
        from airdrop_agent import AirdropAgent
        return {"status": "ok", "count": AirdropAgent().count()}

    def get_ollama_status(self) -> dict:
        """حالة Ollama"""
        from jarvis_bridge import JarvisBridge
        result = JarvisBridge().ping()
        return {
            "status": "ok",
            "ollama": result["status"],
            "models": result.get("models", []),
        }


# ═══════════════════════════════════════
#  CLI Test
# ═══════════════════════════════════════
if __name__ == "__main__":
    print("═" * 60)
    print("⚡ Command Router Test")
    print("═" * 60)

    router = CommandRouter()
    executor = CommandExecutor()

    tests = [
        "أرسل التقرير",
        "افحص المنافذ",
        "حالة VPN",
        "زامن GitHub",
        "اعرض الإيردروبات",
        "حالة الخدمات",
        "أعد تشغيل core",
        "إحصائيات النظام",
        "كم عدد الإيردروبات؟",
        "حالة jarvis",
    ]

    for q in tests:
        route = router.route(q)
        print(f"\n❓ {q}")
        print(f"   ▶ {route['status']} | {route.get('source', '—')} | {route.get('action', route.get('message', ''))}")
