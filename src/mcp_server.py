# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - MCP Server (MCP v2)
يحول الوكلاء إلى MCP tools قياسية
"""
import json
import logging
from pathlib import Path

try:
    from mcp.server.mcpserver import MCPServer
    MCP_VERSION = "v2"
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer
        MCP_VERSION = "v1"
    except ImportError:
        raise ImportError("MCP not installed. Run: pip install mcp")

BASE_DIR = Path.home() / "AETHER_V8"

logger = logging.getLogger("mcp_server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# ─── إنشاء Server ───
mcp = MCPServer("esprieaether")

logger.info("MCP " + MCP_VERSION + " loaded")


# ═══════════════════════════════════════
#  الأدوات
# ═══════════════════════════════════════

@mcp.tool()
def get_airdrops(limit: int = 5) -> str:
    """احصل على أحدث الإيردروبات"""
    try:
        from airdrop_agent import AirdropAgent
        a = AirdropAgent()
        recent = a.get_recent(limit)
        text = "📡 الإيردروبات (" + str(a.count()) + "):" + chr(10)
        for i, item in enumerate(recent, 1):
            text += str(i) + ". " + item["title"][:80] + chr(10)
        return text
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def get_vpn_status() -> str:
    """حالة VPN + IP الحالي"""
    try:
        from vpn_agent import VPNAgent
        v = VPNAgent()
        status = "🟢 نشط" if v.is_active() else "🔴 متوقف"
        return status + " | IP: " + v.get_ip()
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def get_stats() -> str:
    """إحصائيات النظام (CPU/RAM/Disk)"""
    try:
        import psutil
        return (
            "📊 CPU: " + str(psutil.cpu_percent(interval=0.5)) + "%" + chr(10) +
            "💾 RAM: " + str(psutil.virtual_memory().percent) + "%" + chr(10) +
            "💿 Disk: " + str(psutil.disk_usage("/").percent) + "%"
        )
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def get_services() -> str:
    """حالة الخدمات الأربع"""
    try:
        import subprocess
        text = "⚙️ الخدمات:" + chr(10)
        for svc in ["aether-web", "aether-bot", "aether-core", "ollama"]:
            r = subprocess.run(
                ["/usr/bin/systemctl", "is-active", svc],
                capture_output=True, text=True, timeout=5
            )
            emoji = "🟢" if r.stdout.strip() == "active" else "🔴"
            text += emoji + " " + svc + ": " + r.stdout.strip() + chr(10)
        return text
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def get_somnia_balance() -> str:
    """رصيد Somnia STT"""
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider("https://dream-rpc.somnia.network"))
        wallet = json.loads((BASE_DIR / "test_wallets.json").read_text())[0]
        stt = w3.from_wei(w3.eth.get_balance(wallet["address"]), "ether")
        return "💰 Somnia STT: " + str(stt)
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def get_market() -> str:
    """أسعار العملات الرقمية"""
    try:
        from market_watcher import MarketWatcher
        m = MarketWatcher()
        m.fetch_prices()
        text = "📈 أعلى التحركات:" + chr(10)
        for mover in m.get_top_movers(5):
            arrow = "🟢" if mover["change"] > 0 else "🔴"
            text += arrow + " " + mover["coin"] + ": " + str(mover["change"]) + "%" + chr(10)
        return text
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def get_daily_digest() -> str:
    """التقرير اليومي الشامل"""
    try:
        from daily_digest import DailyDigest
        d = DailyDigest()
        return d.format_telegram()
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def get_evolve_suggestions() -> str:
    """اقتراحات التطوير الذاتي"""
    try:
        from self_evolve import SelfEvolve
        evo = SelfEvolve()
        pending = evo.list_pending()
        text = "🧬 اقتراحات (" + str(len(pending)) + "):" + chr(10)
        for s in pending[:5]:
            text += "• " + s["file"] + ": " + s["action"][:60] + chr(10)
        return text
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def get_cost_report() -> str:
    """تقرير استخدام المزودين"""
    try:
        from cloud_fallback import CloudFallback
        c = CloudFallback()
        return c.format_cost_report()
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def get_pharos_balance() -> str:
    """رصيد Pharos Testnet"""
    try:
        from pharos_agent import PharosAgent
        p = PharosAgent()
        b = p.get_balance()
        return "🔷 Pharos: " + str(b.get("balance", "0")) + " PHRS"
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def apply_suggestion(suggestion_id: str) -> str:
    """تطبيق اقتراح تطوير"""
    try:
        from auto_apply import AutoApply
        aa = AutoApply()
        result = aa.apply(suggestion_id)
        return str(result)[:500]
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def restart_service(service_name: str) -> str:
    """إعادة تشغيل خدمة"""
    try:
        import subprocess
        # حماية
        allowed = ["aether-web", "aether-bot", "aether-core", "ollama"]
        if service_name not in allowed:
            return "⛔ خدمة غير مسموحة: " + service_name
        r = subprocess.run(
            ["/usr/bin/sudo", "-n", "/usr/bin/systemctl", "restart", service_name],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            return "✅ تم إعادة تشغيل " + service_name
        return "❌ فشل: " + r.stderr[:200]
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


@mcp.tool()
def run_command(command: str) -> str:
    """تنفيذ أمر shell آمن"""
    try:
        import subprocess
        forbidden = ["rm -rf /", "mkfs", "dd if=", ":(){:|:&};:", "> /dev/sda"]
        if any(f in command for f in forbidden):
            return "⛔ أمر محظور"

        r = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30,
            cwd=str(BASE_DIR)
        )
        output = (r.stdout + r.stderr)[:2000]
        return output or "(no output)"
    except Exception as e:
        return "❌ خطأ: " + str(e)[:200]


# ═══════════════════════════════════════
#  Main
# ═══════════════════════════════════════
if __name__ == "__main__":
    if MCP_VERSION == "v2":
        mcp.run(transport="stdio")
    else:
        mcp.run()
