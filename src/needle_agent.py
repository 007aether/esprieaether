# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Needle Agent (v2)
وكيل تحويل الأوامر إلى أفعال عبر Needle 2
"""
import json
import logging
from pathlib import Path

BASE_DIR = Path.home() / "AETHER_V8"
WEIGHTS = BASE_DIR / "weights" / "needle2.cact"

logger = logging.getLogger("needle_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class NeedleAgent:
    """وكيل Needle 2 لتحويل الأوامر إلى استدعاءات دوال"""

    def __init__(self):
        self.engine = None
        self.tools = []
        self.loaded = False

    def load(self):
        if self.loaded:
            return True
        try:
            from needle_rs import V2Engine
            if not WEIGHTS.exists():
                logger.error(f"❌ لم أجد: {WEIGHTS}")
                return False
            self.engine = V2Engine.load(str(WEIGHTS))
            self.loaded = True
            logger.info("✅ Needle 2 محمّل")
            return True
        except Exception as e:
            logger.error(f"❌ فشل تحميل Needle: {e}")
            return False

    def register_tool(self, name: str, description: str):
        self.tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        })

    def parse_command(self, text: str) -> dict:
        if not self.loaded:
            if not self.load():
                return {"status": "error", "message": "Needle غير محمّل"}

        if not self.tools:
            return {"status": "error", "message": "لا توجد أدوات مسجّلة"}

        try:
            tools_json = json.dumps(self.tools)
            result = self.engine.run(text, tools_json)

            if "<tool_call>" in result:
                start = result.find("<tool_call>") + len("<tool_call>")
                end = result.find("</tool_call>")
                json_str = result[start:end].strip()
                tool_call = json.loads(json_str)

                if not tool_call:
                    return {"status": "no_tool", "raw": result}

                return {
                    "status": "ok",
                    "tool_calls": tool_call if isinstance(tool_call, list) else [tool_call],
                    "raw": result,
                }
            else:
                return {"status": "no_tool", "raw": result}

        except Exception as e:
            logger.error(f"❌ خطأ: {e}")
            return {"status": "error", "message": str(e)}


# ─── أدوات EsprieAether (أسماء وأوصاف دقيقة) ───
def get_default_tools():
    """الأدوات الافتراضية - أسماء واضحة، أوصاف مفصّلة"""
    return [
        ("send_weekly_email_report", 
         "Send the weekly email report to the admin. Takes no inputs. Triggers the email immediately."),
        
        ("check_open_network_ports", 
         "Check and list all currently open network ports on this machine. Takes no inputs."),
        
        ("read_vpn_connection_status", 
         "Read the current VPN connection status and public IP address. Takes no inputs."),
        
        ("upload_files_to_github_repository", 
         "Upload and sync all project files to the GitHub repository. Takes no inputs."),
        
        ("fetch_latest_crypto_airdrops", 
         "Fetch and list the latest cryptocurrency airdrops from RSS feeds. Takes no inputs."),
        
        ("list_running_aether_services", 
         "List all running aether systemd services and their status. Takes no inputs."),
        
        ("restart_aether_autonomous_core", 
         "Restart the aether autonomous core service. Takes no inputs."),
        
        ("display_system_resource_statistics", 
         "Display system resource statistics (CPU, RAM, Disk, Uptime). Takes no inputs."),
    ]


if __name__ == "__main__":
    print("═" * 60)
    print("⚡ Needle Agent Test v2")
    print("═" * 60)

    agent = NeedleAgent()
    for name, desc in get_default_tools():
        agent.register_tool(name, desc)

    tests = [
        "Send the report",
        "Scan the ports",
        "What is the VPN status?",
        "Sync to GitHub",
        "Show me airdrops",
        "System stats",
        "Restart the core",
    ]

    success = 0
    for q in tests:
        print(f"\n❓ {q}")
        result = agent.parse_command(q)
        if result["status"] == "ok":
            for tc in result["tool_calls"]:
                print(f"▶ ✅ {tc['name']}")
                success += 1
        else:
            print(f"▶ ❌ {result['status']}")

    print(f"\n═══ النتيجة: {success}/{len(tests)} ═══")
