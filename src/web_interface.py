# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - JARVIS Command Center
Flask Web Interface
"""
import os
import json
import time
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from functools import wraps

import psutil
from flask import (
    Flask, render_template, request, jsonify,
    Response, redirect, url_for, session
)
from dotenv import load_dotenv

# ─── تحميل الإعدادات ───
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
SECRET_KEY = os.getenv("WEB_SECRET_KEY", "aether_default_secret")

# ─── استيراد الجسر ───
import sys
sys.path.insert(0, str(BASE_DIR / "src"))
from jarvis_bridge import JarvisBridge

# ─── إعداد Flask ───
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "src" / "templates"),
    static_folder=str(BASE_DIR / "src" / "static"),
)
app.secret_key = SECRET_KEY

jarvis = JarvisBridge()

# ─── متتبع وقت البدء ───
START_TIME = time.time()


# ═══════════════════════════════════════
#  helpers
# ═══════════════════════════════════════

def get_system_metrics() -> dict:
    """جلب مقاييس النظام الحية"""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    boot = datetime.fromtimestamp(psutil.boot_time())

    try:
        cpu_freq = psutil.cpu_freq()
        freq_current = round(cpu_freq.current, 0) if cpu_freq else 0
    except Exception:
        freq_current = 0

    return {
        "cpu": {
            "percent": cpu_percent,
            "cores": psutil.cpu_count(logical=True),
            "physical": psutil.cpu_count(logical=False),
            "freq_mhz": freq_current,
        },
        "memory": {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent,
        },
        "network": {
            "bytes_sent_mb": round(net.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net.bytes_recv / (1024**2), 2),
        },
        "system": {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "arch": platform.machine(),
            "python": platform.python_version(),
            "boot_time": boot.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime_seconds": int(time.time() - START_TIME),
        },
    }


def get_wallet_info() -> dict:
    """قراءة ملف المحفظة"""
    wallet_file = BASE_DIR / "aether_wallet.json"
    if wallet_file.exists():
        try:
            with open(wallet_file, "r") as f:
                data = json.load(f)
                # أخفِ المفتاح الخاص
                if "private_key" in data:
                    data["private_key"] = "***hidden***"
                return data
        except Exception as e:
            return {"error": str(e)}
    return {"status": "not_found", "message": "لم يتم العثور على محفظة"}


def get_ollama_status() -> dict:
    """حالة Ollama"""
    return jarvis.ping()


# ═══════════════════════════════════════
#  Routes
# ═══════════════════════════════════════

@app.route("/airdrops")
def airdrops_page():
    """صفحة الإيردروبات"""
    return render_template("airdrops.html", aether_id=os.getenv("AETHER_ID", "007aether"))


@app.route("/api/airdrops")
def api_airdrops():
    """API للإيردروبات"""
    try:
        from airdrop_agent import AirdropAgent
        agent = AirdropAgent()
        limit = int(request.args.get("limit", 20))
        items = agent.get_recent(limit)
        return jsonify({
            "status": "ok",
            "total": agent.count(),
            "count": len(items),
            "items": items,
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})


@app.route("/api/airdrops/sync", methods=["POST"])
def api_airdrops_sync():
    """جلب الإيردروبات فوراً"""
    try:
        from airdrop_agent import AirdropAgent
        agent = AirdropAgent()
        items = agent.fetch_all()
        new = agent.save_airdrops(items)
        return jsonify({
            "status": "ok",
            "fetched": len(items),
            "new": new,
            "total": agent.count(),
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})


@app.route("/")
def index():
    try:
        return render_template(
            "index.html",
            metrics=get_system_metrics(),
            ollama=get_ollama_status(),
            wallet=get_wallet_info(),
            aether_id=os.getenv("AETHER_ID", "007aether"),
        )
    except Exception as e:
        return f"خطأ: {e}", 500


@app.route("/metrics")
def metrics_page():
    """صفحة المقاييس"""
    try:
        return render_template(
            "metrics.html",
            metrics=get_system_metrics(),
            ollama=get_ollama_status(),
        )
    except Exception as e:
        return render_template("metrics.html", metrics={}, ollama={}), 200


@app.route("/stats")
def stats_page():
    """صفحة الإحصائيات"""
    try:
        from analytics import Analytics
        a = Analytics()
        report = a.report(days=7)
        return render_template("stats.html", report=report, stats=report)
    except Exception as e:
        return render_template("stats.html", report={}, stats={}), 200


@app.route("/health")
def health_page():
    """صفحة صحة النظام"""
    try:
        import psutil
        metrics = get_system_metrics()
        return render_template(
            "health.html",
            metrics=metrics,
            system_metrics=metrics,
            health=metrics,
        )
    except Exception as e:
        return render_template("health.html", metrics={}, system_metrics={}, health={}), 200


@app.route("/wallet")
def wallet_page():
    """صفحة المحفظة"""
    try:
        wallet = get_wallet_info()
        return render_template("wallet.html", wallet=wallet)
    except Exception as e:
        return render_template("wallet.html", wallet={}), 200


@app.route("/earnings")
def earnings_page():
    """صفحة الأرباح"""
    try:
        return render_template("earnings.html", earnings={})
    except Exception as e:
        return render_template("earnings.html", earnings={}), 200


@app.route("/monitoring")
def monitoring_page():
    """صفحة المراقبة — تستخدم stats.html"""
    try:
        from analytics import Analytics
        a = Analytics()
        report = a.report(days=1)
        return render_template("stats.html", report=report, stats=report)
    except Exception as e:
        return render_template("stats.html", report={}, stats={}), 200


@app.route("/notifications")
def notifications_page():
    """صفحة التنبيهات"""
    try:
        return render_template("notifications.html", notifications=[])
    except Exception as e:
        return render_template("notifications.html", notifications=[]), 200


@app.route("/security")
def security_page():
    """صفحة الأمن"""
    try:
        from guardian_v2 import Guardian
        g = Guardian()
        return render_template(
            "security.html",
            guardian_stats=g.stats(),
            stats=g.stats(),
        )
    except Exception as e:
        return render_template("security.html", guardian_stats={}, stats={}), 200


@app.route("/somnia")
def somnia_page():
    """صفحة Somnia"""
    try:
        return render_template("somnia.html", somnia={})
    except Exception as e:
        return render_template("somnia.html", somnia={}), 200


@app.route("/api/ollama")
def api_ollama():
    """API حالة Ollama"""
    return jsonify(get_ollama_status())


@app.route("/api/jarvis", methods=["POST"])
def api_jarvis():
    """API محادثة JARVIS"""
    try:
        data = request.get_json(silent=True) or {}
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            return jsonify({"error": "empty prompt"}), 400
        from jarvis_bridge import JarvisBridge
        bridge = JarvisBridge()
        response = bridge.ask(prompt)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
#  🚀 Main Entry Point — يجب أن يكون في نهاية الملف
# ═══════════════════════════════════════════════════════════════




@app.route("/analytics")
def analytics_page():
    """صفحة التحليلات"""
    try:
        from analytics import Analytics
        from semantic_memory_v2 import SemanticMemory
        from guardian_v2 import Guardian
        a = Analytics()
        sm = SemanticMemory()
        g = Guardian()
        return render_template(
            "analytics.html",
            total_events=len(a.data.get("events", [])),
            memory_count=sm.stats()["total"],
            guardian_stats=g.stats(),
        )
    except Exception as e:
        return render_template("analytics.html",
            total_events=0, memory_count=0,
            guardian_stats={"blocked": 0, "total_checks": 0}), 200



# ═══════════════════════════════════════════════════════════════
#  ⚙️ Settings Page
# ═══════════════════════════════════════════════════════════════

@app.route("/settings")
def settings_page():
    """صفحة الإعدادات"""
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv(os.path.expanduser("~/AETHER_V8/.env"), override=True)
        
        # اقرأ الإعدادات (بدون كشف المفاتيح)
        settings = {
            "aether_id": os.getenv("AETHER_ID", "007aether"),
            "aether_email": os.getenv("AETHER_EMAIL", ""),
            "ollama_host": os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            "ollama_model": os.getenv("OLLAMA_MODEL", ""),
            "web_host": os.getenv("WEB_HOST", "127.0.0.1"),
            "web_port": os.getenv("WEB_PORT", "5000"),
            "github_user": os.getenv("GITHUB_USERNAME", ""),
            "github_repo": os.getenv("GITHUB_REPO", ""),
            "github_branch": os.getenv("GITHUB_BRANCH", "main"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "ntfy_topic": os.getenv("NTFY_TOPIC", ""),
            "vpn_interface": os.getenv("VPN_INTERFACE", ""),
            # حالات المفاتيح (بدون كشف القيم)
            "has_openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
            "has_groq": bool(os.getenv("GROQ_API_KEY")),
            "has_telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
            "has_github_token": bool(os.getenv("GITHUB_TOKEN")),
            "has_smtp": bool(os.getenv("SMTP_PASSWORD")),
        }
        
        return render_template("settings.html", settings=settings)
    except Exception as e:
        return render_template("settings.html", settings={}), 200


# ═══════════════════════════════════════════════════════════════
#  🤖 JARVIS Page
# ═══════════════════════════════════════════════════════════════

@app.route("/jarvis")
def jarvis_page():
    """صفحة JARVIS"""
    try:
        # جرّب تحميل JarvisBridge إذا كان موجودًا
        try:
            from src.jarvis_bridge import JarvisBridge
            bridge = JarvisBridge()
            jarvis_status = bridge.ping()
        except Exception:
            jarvis_status = {}
        
        return render_template(
            "jarvis.html",
            jarvis=jarvis_status,
            status=jarvis_status,
            aether_id=os.getenv("AETHER_ID", "007aether"),
        )
    except Exception as e:
        return render_template("jarvis.html", jarvis={}, status={}), 200


if __name__ == "__main__":
    print(f"🚀 Server running on http://{WEB_HOST}:{WEB_PORT}")
    print(f"📊 Total routes: {len(list(app.url_map.iter_rules()))}")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False, use_reloader=False)
