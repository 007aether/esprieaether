"""
⚡ EsprieAether - Ask Agent
مساعد ذكي يفهم أي سؤال ويستدعي الأدوات
"""
import re
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("ask_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

TOOLS_SCHEMA = "الأدوات: get_airdrops, get_vpn_status, get_stats, get_services, get_cloud_status, get_evolve_suggestions, get_somnia_balance, get_bandwidth_status, run_backup"


import asyncio
from mcp_client import MCPClient


class AskAgent:
    """مساعد ذكي شامل"""

    def __init__(self):
        self.last_question = None
        self.last_answer = None

    # ─── التخطيط ───
    def plan(self, question: str) -> dict:
        """regex أولاً، ثم Cloud"""
        q = question.lower()

        patterns = [
            (r"ايردروب|airdrop|إيردروب", "get_airdrops"),
            (r"vpn|في بي|فيبي", "get_vpn_status"),
            (r"احصائ|إحصائ|stats|cpu|ram|ذاكرة|معالج", "get_stats"),
            (r"خدمات|services|خدمة|systemd", "get_services"),
            (r"cloud|سحاب|اونلاين", "get_cloud_status"),
            (r"اقتراح|evolve|تطوير", "get_evolve_suggestions"),
            (r"somnia|ستي|رصيد", "get_somnia_balance"),
            (r"bandwidth|مشاركة", "get_bandwidth_status"),
            (r"backup|نسخ|احتياطي", "run_backup"),
        ]

        for pattern, tool in patterns:
            if re.search(pattern, q, re.IGNORECASE):
                return {"tool": tool, "params": {}, "source": "regex"}

        # Cloud احتياطي
        try:
            from cloud_fallback import CloudFallback
            cloud = CloudFallback()

            prompt_parts = [
                "اختر الأداة المناسبة. أجب باسم الأداة فقط.",
                TOOLS_SCHEMA,
                "السؤال: " + question,
                "الأداة:",
            ]
            prompt = chr(10).join(prompt_parts)

            result = cloud.ask(prompt, prefer="auto")

            if result["status"] == "ok":
                answer = result["answer"].strip().lower()
                tools = [
                    "get_airdrops", "get_vpn_status", "get_stats",
                    "get_services", "get_cloud_status", "get_evolve_suggestions",
                    "get_somnia_balance", "get_bandwidth_status", "run_backup"
                ]
                for t in tools:
                    if t in answer:
                        return {"tool": t, "params": {}, "source": result["source"]}
        except Exception as e:
            logger.error(f"Cloud فشل: {e}")

        return {"tool": "none", "params": {}, "source": "none"}

    # ─── التنفيذ ───
    def execute(self, tool: str, params: dict) -> dict:
        try:
            if tool == "get_airdrops":
                return self._get_airdrops()
            elif tool == "get_vpn_status":
                return self._get_vpn_status()
            elif tool == "get_stats":
                return self._get_stats()
            elif tool == "get_services":
                return self._get_services()
            elif tool == "get_cloud_status":
                return self._get_cloud_status()
            elif tool == "get_evolve_suggestions":
                return self._get_evolve_suggestions()
            elif tool == "get_somnia_balance":
                return self._get_somnia_balance()
            elif tool == "get_bandwidth_status":
                return self._get_bandwidth_status()
            elif tool == "run_backup":
                return self._run_backup()
            else:
                return {"status": "no_tool"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_airdrops(self) -> dict:
        from airdrop_agent import AirdropAgent
        a = AirdropAgent()
        recent = a.get_recent(3)
        return {
            "status": "ok",
            "total": a.count(),
            "recent": [{"title": r["title"][:80], "link": r["link"]} for r in recent],
        }

    def _get_vpn_status(self) -> dict:
        from vpn_agent import VPNAgent
        v = VPNAgent()
        return {"status": "ok", "active": v.is_active(), "ip": v.get_ip()}

    def _get_stats(self) -> dict:
        import psutil
        return {
            "status": "ok",
            "cpu": psutil.cpu_percent(interval=0.5),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent,
        }

    def _get_services(self) -> dict:
        import subprocess
        services = {}
        for svc in ["aether-web", "aether-bot", "aether-core", "ollama"]:
            r = subprocess.run(
                ["/usr/bin/systemctl", "is-active", svc],
                capture_output=True, text=True, timeout=5
            )
            services[svc] = r.stdout.strip()
        return {"status": "ok", "services": services}

    def _get_cloud_status(self) -> dict:
        from cloud_fallback import CloudFallback
        s = CloudFallback().status()
        return {
            "status": "ok",
            "online": s["online"],
            "cloud_model": s["cloud_model"],
            "local_model": s["local_model"],
        }

    def _get_evolve_suggestions(self) -> dict:
        from self_evolve import SelfEvolve
        pending = SelfEvolve().list_pending()
        return {
            "status": "ok",
            "total": len(pending),
            "recent": [
                {"file": s["file"], "action": s["action"][:80]}
                for s in pending[:3]
            ],
        }

    def _get_somnia_balance(self) -> dict:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider("https://dream-rpc.somnia.network"))
        wallet = json.loads((BASE_DIR / "test_wallets.json").read_text())[0]
        stt = w3.from_wei(w3.eth.get_balance(wallet["address"]), "ether")
        return {"status": "ok", "stt": str(stt)}

    def _get_bandwidth_status(self) -> dict:
        from bandwidth_agent import BandwidthAgent
        s = BandwidthAgent().status()
        return {
            "status": "ok",
            "docker": s["docker_available"],
            "running": len(s["running_containers"]),
        }

    def _run_backup(self) -> dict:
        import subprocess
        from datetime import datetime
        fn = "/home/esprieaether/AETHER_BACKUP_" + datetime.now().strftime("%Y%m%d_%H%M") + ".tar.gz"
        r = subprocess.run(
            ["tar", "czf", fn, "--exclude=.venv", "--exclude=*.log",
             "--exclude=*.db", "--exclude=*.tar.gz", "--exclude=OpenJarvis",
             "-C", "/home/esprieaether", "AETHER_V8"],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode == 0:
            size = Path(fn).stat().st_size // 1024
            return {"status": "ok", "file": Path(fn).name, "size_kb": size}
        return {"status": "error", "error": r.stderr[:200]}

    # ─── الصياغة ───
    def format(self, tool: str, data: dict, question: str) -> str:
        if data.get("status") == "no_tool":
            return "❓ لم أفهم. جرب:\n• كم إيردروب؟\n• حالة VPN\n• إحصائيات\n• الخدمات\n• رصيد Somnia"

        if data.get("status") == "error":
            return "❌ " + str(data.get("error", "خطأ"))

        if tool == "get_airdrops":
            text = "📡 *الإيردروبات*: `" + str(data["total"]) + "`\n\n*أحدث 3:*\n"
            for i, r in enumerate(data.get("recent", []), 1):
                text += str(i) + ". " + r["title"] + "\n"
            return text

        if tool == "get_vpn_status":
            emoji = "🟢" if data.get("active") else "🔴"
            return emoji + " *VPN*: `" + str(data.get("ip", "—")) + "`"

        if tool == "get_stats":
            return (
                "📊 *الإحصائيات*\n"
                "• CPU: `" + str(data["cpu"]) + "%`\n"
                "• RAM: `" + str(data["ram"]) + "%`\n"
                "• Disk: `" + str(data["disk"]) + "%`"
            )

        if tool == "get_services":
            text = "⚙️ *الخدمات*\n"
            for name, status in data.get("services", {}).items():
                emoji = "🟢" if status == "active" else "🔴"
                text += emoji + " `" + name + "`\n"
            return text

        if tool == "get_cloud_status":
            emoji = "🟢" if data.get("online") else "🔴"
            return (
                emoji + " *Cloud*\n"
                "• Online: `" + str(data.get("online")) + "`\n"
                "• Cloud: `" + str(data.get("cloud_model")) + "`\n"
                "• Local: `" + str(data.get("local_model")) + "`"
            )

        if tool == "get_evolve_suggestions":
            text = "🧬 *اقتراحات*: `" + str(data["total"]) + "`\n\n"
            for s in data.get("recent", []):
                text += "📁 `" + s["file"] + "`\n⚙️ " + s["action"] + "\n\n"
            return text

        if tool == "get_somnia_balance":
            return "💰 *Somnia STT*: `" + str(data["stt"]) + "`"

        if tool == "get_bandwidth_status":
            emoji = "🟢" if data.get("docker") else "🔴"
            return emoji + " *Bandwidth*\n• Docker: `" + str(data.get("docker")) + "`\n• Running: `" + str(data.get("running")) + "`"

        if tool == "run_backup":
            return "💾 *Backup*\n📁 `" + str(data.get("file")) + "`\n📊 `" + str(data.get("size_kb")) + " KB`"

        return "✅ " + json.dumps(data, ensure_ascii=False)[:300]

    # ─── الوظيفة ───
    def ask_cognitive(self, question: str) -> dict:
        """استخدم الطبقة المعرفية الكاملة (Planner + Memory + Executor)"""
        try:
            from complex_executor import ComplexExecutor

            ex = ComplexExecutor()
            result = ex.execute_goal(question)

            # استخرج النص
            answer_parts = []
            for r in result.get("results", []):
                answer_parts.append(str(r.get("result", "")))

            answer = chr(10).join(answer_parts)
            if not answer:
                answer = "✅ تم التنفيذ"

            return {
                "status": "ok",
                "question": question,
                "tool": "cognitive_layer",
                "source": "planner+memory+executor",
                "answer": answer,
                "complexity": result.get("steps_count", 0),
            }
        except Exception as e:
            # fallback
            return self.ask_mcp(question)

    def ask_mcp(self, question: str) -> dict:
        """استخدم MCP للأدوات"""
        try:
            client = MCPClient()

            # اكتشف الأداة
            plan = self.plan(question)
            tool = plan.get("tool", "none")

            # حول أسماء الأدوات لتطابق MCP
            tool_map = {
                "get_airdrops": "get_airdrops",
                "get_vpn_status": "get_vpn_status",
                "get_stats": "get_stats",
                "get_services": "get_services",
                "get_somnia_balance": "get_somnia_balance",
                "get_market": "get_market",
                "get_daily_digest": "get_daily_digest",
                "get_evolve_suggestions": "get_evolve_suggestions",
                "get_cost_report": "get_cost_report",
                "get_pharos_balance": "get_pharos_balance",
            }

            mcp_tool = tool_map.get(tool)
            if not mcp_tool:
                return self.ask(question)

            # استدعِ عبر MCP
            result = asyncio.run(client.call_tool(mcp_tool))

            return {
                "status": "ok",
                "question": question,
                "tool": tool,
                "source": "mcp",
                "answer": result,
            }
        except Exception as e:
            # fallback
            return self.ask(question)

    def ask(self, question: str) -> dict:
        self.last_question = question
        plan = self.plan(question)
        tool = plan.get("tool", "none")
        params = plan.get("params", {})
        data = self.execute(tool, params)
        answer = self.format(tool, data, question)
        self.last_answer = answer

        return {
            "status": "ok",
            "question": question,
            "tool": tool,
            "source": plan.get("source", "—"),
            "answer": answer,
        }


if __name__ == "__main__":
    print("═" * 60)
    print("🤖 Ask Agent Test")
    print("═" * 60)

    agent = AskAgent()

    tests = [
        "كم إيردروب جديد؟",
        "حالة VPN",
        "إحصائيات النظام",
        "حالة الخدمات",
        "رصيد Somnia",
        "اقتراحات التطوير",
    ]

    for q in tests:
        print("\n❓ " + q)
        r = agent.ask(q)
        print("▶ " + r["answer"][:200])
