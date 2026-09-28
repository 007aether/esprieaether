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
    """الصفحة الرئيسية — لوحة القيادة"""
    return render_template(
        "index.html",
        metrics=get_system_metrics(),
        ollama=get_ollama_status(),
        wallet=get_wallet_info(),
        aether_id=os.getenv("AETHER_ID", "007aether"),
    )


@app.route("/jarvis")
def jarvis_page():
    """صفحة المحادثة مع JARVIS"""
    return render_template("jarvis.html", aether_id=os.getenv("AETHER_ID", "007aether"))


@app.route("/metrics")
def metrics_page():
    """صفحة المقاييس الحية"""
    return render_template("metrics.html")


@app.route("/security")
def security_page():
    """صفحة الأمن"""
    return render_template("security.html")


@app.route("/wallet")
def wallet_page():
    """صفحة المحفظة"""
    return render_template("wallet.html", wallet=get_wallet_info())




@app.route("/somnia")
def somnia_page():
    """صفحة Somnia (للعرض فقط)"""
    return render_template("somnia.html", aether_id=os.getenv("AETHER_ID", "007aether"))


@app.route("/api/somnia")
def api_somnia():
    """API لحالة Somnia (للعرض فقط)"""
    try:
        import json
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider("https://dream-rpc.somnia.network"))
        wallet_file = BASE_DIR / "test_wallets.json"

        if not wallet_file.exists():
            return jsonify({"status": "error", "error": "لا توجد محفظة"})

        wallet = json.loads(wallet_file.read_text())[0]
        address = wallet["address"]
        stt_balance = w3.from_wei(w3.eth.get_balance(address), "ether")

        return jsonify({
            "status": "ok",
            "address": address,
            "stt": str(stt_balance),
            "network": {
                "connected": w3.is_connected(),
                "block": w3.eth.block_number,
                "chain_id": w3.eth.chain_id,
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})


@app.route("/stats")
def stats_page():
    """صفحة الإحصائيات"""
    return render_template("stats.html", aether_id=os.getenv("AETHER_ID", "007aether"))


@app.route("/api/stats/full")
def api_stats_full():
    """API الإحصائيات الشاملة"""
    try:
        import json
        from datetime import datetime
        from pathlib import Path as P

        result = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "system": {},
            "agents": {},
            "airdrops": {},
            "github": {},
            "vpn": {},
        }

        # النظام
        try:
            import psutil
            result["system"] = {
                "cpu": psutil.cpu_percent(interval=0.5),
                "ram": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage("/").percent,
                "uptime_seconds": int(datetime.now().timestamp() - psutil.boot_time()),
            }
        except Exception:
            pass

        # Airdrops
        try:
            from airdrop_agent import AirdropAgent
            a = AirdropAgent()
            result["airdrops"] = {
                "total": a.count(),
                "recent": len(a.get_recent(10)),
            }
        except Exception:
            pass

        # GitHub
        try:
            from github_agent import GitHubAgent
            gh = GitHubAgent().ping()
            result["github"] = {
                "status": gh.get("status"),
                "repo": gh.get("repo"),
            }
        except Exception:
            pass

        # VPN
        try:
            from vpn_agent import VPNAgent
            v = VPNAgent()
            result["vpn"] = {
                "active": v.is_active(),
                "ip": v.get_ip(),
            }
        except Exception:
            pass

        # Autonomous state
        try:
            state_file = BASE_DIR / "autonomous_state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                result["agents"] = {
                    "cycles": state.get("cycles", 0),
                    "started_at": state.get("started_at", "—"),
                    "tasks_count": len(state.get("last_run", {})),
                }
        except Exception:
            pass

        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})


@app.route("/earnings")
def earnings_page():
    """صفحة الأرباح"""
    return render_template("earnings.html", aether_id=os.getenv("AETHER_ID", "007aether"))


@app.route("/api/earnings")
def api_earnings():
    """API الأرباح"""
    try:
        import json
        from airdrop_agent import AirdropAgent

        airdrop = AirdropAgent()

        result = {
            "status": "ok",
            "airdrops": {
                "total": airdrop.count(),
                "recent": airdrop.get_recent(10),
            },
            "bandwidth": {},
        }

        # Bandwidth
        try:
            from bandwidth_agent import BandwidthAgent
            bw = BandwidthAgent()
            result["bandwidth"] = bw.status()
        except Exception:
            pass

        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})


@app.route("/settings")
def settings_page():
    """صفحة الإعدادات"""
    env_file = BASE_DIR / ".env"
    env_content = env_file.read_text() if env_file.exists() else ""
    return render_template("settings.html", env_content=env_content)


# ─── API ───

@app.route("/api/metrics")
def api_metrics():
    """API للمقاييس (JSON)"""
    return jsonify(get_system_metrics())


@app.route("/api/ollama")
def api_ollama():
    """API لحالة Ollama"""
    return jsonify(get_ollama_status())


@app.route("/api/wallet")
def api_wallet():
    """API للمحفظة"""
    return jsonify(get_wallet_info())


@app.route("/api/jarvis/chat", methods=["POST"])
def api_jarvis_chat():
    """محادثة عادية (بدون streaming)"""
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "الرجاء كتابة سؤال"}), 400

    answer = jarvis.ask(prompt)
    return jsonify({
        "prompt": prompt,
        "answer": answer,
        "history_size": len(jarvis.get_history()),
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/jarvis/stream", methods=["POST"])
def api_jarvis_stream():
    """محادثة متدفقة (streaming)"""
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "الرجاء كتابة سؤال"}), 400

    def generate():
        try:
            for token in jarvis.ask_stream(prompt):
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/jarvis/clear", methods=["POST"])
def api_jarvis_clear():
    """مسح سجل المحادثة"""
    jarvis.clear_history()
    return jsonify({"status": "cleared"})


@app.route("/api/jarvis/history")
def api_jarvis_history():
    """إرجاع السجل"""
    return jsonify({"history": jarvis.get_history()})


@app.route("/api/security/ports")
def api_security_ports():
    """فحص المنافذ المفتوحة"""
    try:
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.strip().split("\n")[1:]
        ports = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                ports.append({
                    "state": parts[0],
                    "local": parts[3],
                    "process": parts[5] if len(parts) > 5 else "—",
                })
        return jsonify({"status": "ok", "count": len(ports), "ports": ports})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})


# ═══════════════════════════════════════
#  Main
# ═══════════════════════════════════════

if __name__ == "__main__":
    print("═" * 60)
    print("⚡ ESPRIEAETHER - JARVIS COMMAND CENTER")
    print("═" * 60)
    print(f"🌐 http://{WEB_HOST}:{WEB_PORT}")
    print(f"🤖 Ollama: {os.getenv('OLLAMA_HOST')}")
    print(f"🧠 Model: {os.getenv('OLLAMA_MODEL')}")
    print("═" * 60)

    # فحص Ollama عند البدء
    status = jarvis.ping()
    if status["status"] == "online":
        print(f"✅ Ollama: متصل | النماذج: {status.get('models', [])}")
    else:
        print(f"⚠️ Ollama: غير متصل | {status.get('error', '')}")
    print("═" * 60)

    app.run(host=WEB_HOST, port=WEB_PORT, debug=False, threaded=True)
