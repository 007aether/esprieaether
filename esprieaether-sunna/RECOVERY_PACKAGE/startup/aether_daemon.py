#!/usr/bin/env python3
"""
==========================================
  AETHER DAEMON - نظام تشغيل دائم
  مستقل ذاتياً - يعيد التشغيل التلقائي
==========================================
"""
import subprocess
import os
import sys
import time
from pathlib import Path

PROJECT_DIR = Path("C:/Users/ESPRIEAETHER/Desktop/esprieaether")
LOGS_DIR = PROJECT_DIR / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

AGENTS = [
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

class AetherDaemon:
    def __init__(self):
        self.processes = {}
        self.is_running = True

    def log(self, msg):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {msg}")

    def start_agent(self, name):
        log_path = LOGS_DIR / f"agent_{name.replace('.py', '')}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.Popen(
                [sys.executable, str(PROJECT_DIR / "src" / "agents" / name)],
                stdout=open(log_path, 'w', encoding='utf-8'),
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
            self.processes[name] = proc
            self.log(f"  ✅ {name} متصل")
            return True
        except Exception as e:
            self.log(f"  ❌ فشل {name}: {e}")
            return False

    def check_agents(self):
        """التحقق من العمليات النشيطة"""
        for name in list(self.processes.keys()):
            proc = self.processes[name]
            if proc.poll() is not None:
                self.log(f"  ⚠️ {name} توقف (exit code: {proc.returncode})")
                del self.processes[name]
                self.start_agent(name)

    def start_all(self):
        self.log("=" * 50)
        self.log("🚀 تشغيل نظام AETHER الدائم (Daemon)")
        self.log("=" * 50)
        for agent in AGENTS:
            self.start_agent(agent)
        self.log("")
        self.log("📊 جميع الوكلاء متصلون")
        self.log("🔄 النظام سيعمل دائماً ويعيد التشغيل تلقائياً")

    def run(self):
        self.start_all()
        self.log("")
        self.log("⏳ الانتظار... (Ctrl+C للخروج)")
        self.log("=" * 50)
        try:
            while self.is_running:
                self.check_agents()
                time.sleep(10)
        except KeyboardInterrupt:
            self.log("👋 إيقاف النظام")

if __name__ == "__main__":
    daemon = AetherDaemon()
    daemon.run()
