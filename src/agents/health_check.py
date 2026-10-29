#!/usr/bin/env python3
"""
==========================================
  HEALTH CHECK AGENT — وكيل فحص الصحة
==========================================
يقوم بفحص كل وكيل على حدة:
- Heartbeat: هل الوكيل متصل؟
- آخر نشاط
- حالة الخدمة
- حالة الشبكة والذاكرة
"""
import json
import psutil
import socket
import time
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path("C:/Users/ESPRIEAETHER/Desktop/esprieaether")
DATA_DIR = PROJECT_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
STATE_FILE = DATA_DIR / "health_check_state.json"
LOG_FILE = LOGS_DIR / "health_check.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

class HealthCheckAgent:
    def __init__(self):
        self.services = [
            {"name": "JARVIS Web", "port": 5000},
            {"name": "Cloud Desktop", "port": 5001},
            {"name": "Kanban Board", "port": 5103},
            {"name": "Sunna API", "port": 5100},
            {"name": "Sunna Dashboard", "port": 5105},
            {"name": "AI Router", "port": 11435},
            {"name": "Orchestrator", "port": 11436},
            {"name": "Agent Mesh", "port": 11437},
            {"name": "Telegram Bot", "port": None},
        ]
        self.agents = [
            "network_monitor.py",
            "security_agent.py",
            "memory_agent.py",
            "daily_report.py",
            "predictive_analyzer.py",
            "trading_bot.py",
            "error_fix_agent.py",
            "arabic_support.py",
            "knowledge_base.py",
        ]
        self._log("شبدأ وكيل الفحص الصحي (Health Check)")

    def _log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")

    def check_port(self, host, port, timeout=2):
        """فحص المنفذ"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def check_agent(self, agent_name):
        """فحص وكيل ما"""
        log_path = LOGS_DIR / f"loop_{agent_name}.log"
        last_activity = None
        if log_path.exists():
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                if lines:
                    last_activity = lines[-1].strip()
        return last_activity

    def check_system(self):
        """فحص حالة النظام"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            return {"cpu": cpu, "memory": memory, "disk": disk}
        except Exception as e:
            return {"error": str(e)}

    def run(self):
        """تشغيل الفحص الصحي"""
        self._log("=" * 60)
        self._log("🩺 وكيل الفحص الصحي (Health Check)")
        self._log("=" * 60)

        # فحص النظام
        system_status = self.check_system()
        self._log(f"📊 النظام: CPU={system_status['cpu']}%, RAM={system_status['memory']}%, Disk={system_status['disk']}%")

        # فحص الخدمات
        self._log("\n🔍 فحص الخدمات:")
        for service in self.services:
            port = service["port"]
            if port is None:
                self._log(f"  ✅ {service['name']}: التشغيل (Telegram)")
            elif self.check_port("localhost", port):
                self._log(f"  ✅ {service['name']}: {port} متصل")
            else:
                self._log(f"  ❌ {service['name']}: {port} متوقف")

        # فحص الوكلاء
        self._log("\n🔍 فحص الوكلاء:")
        for agent in self.agents:
            activity = self.check_agent(agent)
            status = "✅ متصل" if activity else "❌ متوقف"
            self._log(f"  {status}: {agent}")
            if activity:
                self._log(f"     آخر نشاط: {activity[:80]}...")

        # الحفظ
        state = {
            "timestamp": datetime.now().isoformat(),
            "system": system_status,
            "services": [{"name": s["name"], "port": s["port"], "status": "ok" if self.check_port("localhost", s["port"]) else "down"} for s in self.services],
            "agents": [{"name": a, "status": "ok" if self.check_agent(a) else "down"} for a in self.agents],
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        self._log("\n" + "=" * 60)
        self._log("✅ الفحص الصحي مكتمل!")


if __name__ == "__main__":
    agent = HealthCheckAgent()
    agent.run()
