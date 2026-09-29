# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

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

    # إعادة تشغيل (محددة أولاً)
    (r"(أعد|اعد|restart).*(تشغيل).*(بوت|bot)", "restart_bot"),
    (r"(أعد|اعد|restart).*(تشغيل).*(ويب|web|dashboard)", "restart_web"),
    (r"(أعد|اعد|restart).*(تشغيل).*(core|نواة|النواة)", "restart_core"),
    (r"(أعد|اعد|restart).*(core|نواة)", "restart_core"),

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

    # السجلات والمهام
    (r"(اعرض|أظهر|هات|أرني|وريني).*(سجل|سجلات|logs)", "view_logs"),
    (r"(اعرض|أظهر|هات).*(مهام|tasks|جدول)", "view_tasks"),
    (r"(كم|ما).*(الساعة|الوقت|time)", "current_time"),
    (r"(اعرض|أظهر|من).*(متصل|جلسات|sessions|users)", "view_sessions"),
    (r"(فحص|حرارة|حراره|temp).*(حرارة|cpu|درجة)", "check_temperature"),

    # الشبكة والبلوكشين
    (r"(اعرض|هات|ما).*(ال ip|الايبي|ip|ايبي)", "get_ip"),
    (r"(افحص|اختبر|test).*(اتصال|شبكة|net|ping)", "test_connection"),
    (r"(اعرض|هات|جيب).*(ايردروب|airdrop).*(جديد|جديدة|حديث|أحدث)", "get_new_airdrops"),

    # الملفات والنسخ
    (r"(خذ|اعمل|سوي|انسخ).*(نسخة|backup|باكان)", "create_backup"),
    (r"(اعرض|هات|كم).*(مساحة|space|disk|تخزين)", "get_space"),
    (r"(نظف|امسح|قطع).*(سجل|سجلات|logs)", "clean_logs"),

    # VPN
    (r"(أوقف|اطفي|اقفل|stop|off).*(vpn|في بي)", "vpn_off"),
    (r"(شغل|فعل|on|افتح).*(vpn|في بي)", "vpn_on"),
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
            "view_logs": self.view_logs,
            "view_tasks": self.view_tasks,
            "current_time": self.current_time,
            "view_sessions": self.view_sessions,
            "check_temperature": self.check_temperature,
            "get_ip": self.get_ip,
            "test_connection": self.test_connection,
            "get_new_airdrops": self.get_new_airdrops,
            "create_backup": self.create_backup,
            "get_space": self.get_space,
            "clean_logs": self.clean_logs,
            "restart_bot": self.restart_bot,
            "restart_web": self.restart_web,
            "vpn_off": self.vpn_off,
            "vpn_on": self.vpn_on,
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
#  دوال إضافية (v2)
# ═══════════════════════════════════════

def _view_logs(self) -> dict:
    """آخر 20 سطر من autonomous.log"""
    log_file = BASE_DIR / "autonomous.log"
    if not log_file.exists():
        return {"status": "error", "message": "لا يوجد سجل"}
    lines = log_file.read_text().split("\n")[-20:]
    return {"status": "ok", "lines": lines}

def _view_tasks(self) -> dict:
    """المهام المجدولة"""
    import json
    state_file = BASE_DIR / "autonomous_state.json"
    if not state_file.exists():
        return {"status": "error", "message": "لا توجد حالة"}
    state = json.loads(state_file.read_text())
    return {
        "status": "ok",
        "cycles": state.get("cycles", 0),
        "tasks": list(state.get("last_run", {}).keys()),
    }

def _current_time(self) -> dict:
    """الوقت الحالي"""
    from datetime import datetime
    import psutil
    uptime = datetime.now().timestamp() - psutil.boot_time()
    hours = int(uptime // 3600)
    mins = int((uptime % 3600) // 60)
    return {
        "status": "ok",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uptime": f"{hours}h {mins}m",
    }

def _view_sessions(self) -> dict:
    """المستخدمون المتصلون"""
    r = subprocess.run(["who"], capture_output=True, text=True, timeout=5)
    lines = [l for l in r.stdout.strip().split("\n") if l]
    return {"status": "ok", "sessions": lines, "count": len(lines)}

def _check_temperature(self) -> dict:
    """حرارة CPU"""
    try:
        import psutil
        temps = psutil.sensors_temperatures()
        if not temps:
            return {"status": "error", "message": "لا توجد حساسات"}
        result = {}
        for name, entries in temps.items():
            result[name] = [{"label": e.label or "core", "current": e.current} for e in entries]
        return {"status": "ok", "temps": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _get_ip(self) -> dict:
    """IP العام + VPN"""
    try:
        ip = requests.get("https://ifconfig.me", timeout=10).text.strip()
        from vpn_agent import VPNAgent
        vpn = VPNAgent()
        return {
            "status": "ok",
            "public_ip": ip,
            "vpn_active": vpn.is_active(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _test_connection(self) -> dict:
    """اختبار الاتصال"""
    try:
        r = subprocess.run(
            ["ping", "-c", "3", "1.1.1.1"],
            capture_output=True, text=True, timeout=15
        )
        lines = r.stdout.split("\n")
        stats = [l for l in lines if "packets transmitted" in l or "rtt" in l]
        return {"status": "ok", "result": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _get_new_airdrops(self) -> dict:
    """أحدث 10 إيردروبات"""
    from airdrop_agent import AirdropAgent
    agent = AirdropAgent()
    return {
        "status": "ok",
        "items": agent.get_recent(10),
        "total": agent.count(),
    }

def _create_backup(self) -> dict:
    """نسخة احتياطية"""
    import subprocess
    from datetime import datetime
    filename = f"/home/esprieaether/AETHER_BACKUP_{datetime.now().strftime('%Y%m%d_%H%M')}.tar.gz"
    r = subprocess.run(
        ["tar", "czf", filename, "--exclude=.venv", "--exclude=*.log",
         "--exclude=*.db", "--exclude=*.tar.gz", "--exclude=OpenJarvis",
         "-C", "/home/esprieaether", "AETHER_V8"],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode == 0:
        size = Path(filename).stat().st_size
        return {"status": "ok", "file": filename, "size_kb": size // 1024}
    return {"status": "error", "message": r.stderr}

def _get_space(self) -> dict:
    """المساحة"""
    import psutil
    disk = psutil.disk_usage("/")
    aether_size = subprocess.run(
        ["du", "-sh", str(BASE_DIR)],
        capture_output=True, text=True, timeout=10
    ).stdout.split()[0]
    return {
        "status": "ok",
        "aether_size": aether_size,
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "disk_free_gb": round(disk.free / (1024**3), 1),
        "disk_percent": disk.percent,
    }

def _clean_logs(self) -> dict:
    """قطع السجلات"""
    logs = [BASE_DIR / "bot.log", BASE_DIR / "autonomous.log"]
    result = {}
    for log in logs:
        if log.exists():
            size_before = log.stat().st_size
            lines = log.read_text().split("\n")[-1000:]
            log.write_text("\n".join(lines))
            size_after = log.stat().st_size
            result[log.name] = {
                "before_kb": size_before // 1024,
                "after_kb": size_after // 1024,
            }
    return {"status": "ok", "logs": result}

def _restart_bot(self) -> dict:
    r = subprocess.run(["sudo", "systemctl", "restart", "aether-bot"],
                     capture_output=True, timeout=15)
    return {"status": "ok" if r.returncode == 0 else "error"}

def _restart_web(self) -> dict:
    r = subprocess.run(["sudo", "systemctl", "restart", "aether-web"],
                     capture_output=True, timeout=15)
    return {"status": "ok" if r.returncode == 0 else "error"}

def _vpn_off(self) -> dict:
    from vpn_agent import VPNAgent
    return VPNAgent().disconnect()

def _vpn_on(self) -> dict:
    from vpn_agent import VPNAgent
    return VPNAgent().connect()


# ربط الدوال بالفئة
CommandExecutor.view_logs = _view_logs
CommandExecutor.view_tasks = _view_tasks
CommandExecutor.current_time = _current_time
CommandExecutor.view_sessions = _view_sessions
CommandExecutor.check_temperature = _check_temperature
CommandExecutor.get_ip = _get_ip
CommandExecutor.test_connection = _test_connection
CommandExecutor.get_new_airdrops = _get_new_airdrops
CommandExecutor.create_backup = _create_backup
CommandExecutor.get_space = _get_space
CommandExecutor.clean_logs = _clean_logs
CommandExecutor.restart_bot = _restart_bot
CommandExecutor.restart_web = _restart_web
CommandExecutor.vpn_off = _vpn_off
CommandExecutor.vpn_on = _vpn_on


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
