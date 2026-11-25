#!/usr/bin/env python3
"""
نظام التشغيل الذاتي الكامل لـ ESPRIEAETHER
- يعمل بشكل كامل مستقل، لا يعتمد على أي شيء
- يعيد التشغيل تلقائياً إذا توقف
- لا يتوقف أبداً
- لا يعتمد على أي شخص أو عملية
"""

import os, sys, time, subprocess, signal, atexit, logging
from pathlib import Path

class AutonomousSystem:
    def __init__(self):
        self.workspace = Path("C:/Users/ESPRIEAETHER/Desktop/esprieaether")
        self.pid_file = self.workspace / "data" / "autonomous_system.pid"
        self.daemon_running = True
        self.restart_count = 0
        log_path = self.workspace / "data" / "autonomous_selfheal.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=str(log_path), level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger("autonomous_selfheal")

    def cleanup(self):
        self.daemon_running = False
        self.pid_file.unlink(missing_ok=True)
        self.logger.info("نظام التشغيل الذاتي توقف")

    def is_autonomous_evolve_running(self):
        try:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
            for line in result.stdout.split("\n"):
                if "autonome_evolve.py" in line and "grep" not in line:
                    return True
        except:
            pass
        return False

    def is_running(self, pattern):
        """Check if a process with given pattern is running (Windows-compatible)"""
        try:
            # Use CimInstance to get command line and check patterns
            cmd = 'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "' + pattern + '" } | Select-Object -First 5 | Format-Table -AutoSize'
            result = subprocess.run(['powershell', '-Command', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            stdout = result.stdout.decode('utf-8', errors='ignore')
            if stdout and ('python' in stdout.lower() or 'hermes' in stdout.lower() or 'autonome' in stdout.lower()):
                return True
        except Exception:
            pass
        return False

    def start_evolve(self):
        if not self.is_running("autonome_evolve.py"):
            self.logger.info("=== البدء بنظام التطور الذاتي ===")
            try:
                subprocess.Popen([sys.executable, "src/autonome_evolve.py", "--daemon"],
                    cwd=str(self.workspace), stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True)
                self.logger.info("✅ نظام التطور الذاتي في العمل")
            except Exception as e:
                self.logger.error(f"خطأ في بدء التطور: {e}")

    def start_hermes(self):
        hermes_patterns = ["hermes_agent.py", "hermes", "ai_router.py", "agent_kernel.py", "agent_mesh.py"]
        for pat in hermes_patterns:
            if self.is_running(pat):
                return True
        self.logger.info("=== البدء بالنظام الهرمي (Hermes Agent) ===")
        try:
            hermes_script = self.workspace / "src" / "hermes_agent.py"
            if not hermes_script.exists():
                hermes_script = self.workspace / "src" / "agent_mesh.py"
            if hermes_script.exists():
                subprocess.Popen([sys.executable, str(hermes_script)],
                    cwd=str(self.workspace), stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True)
                self.logger.info("✅ System Hermes Agent في العمل")
            else:
                self.start_evolve()
        except Exception as e:
            self.logger.error(f"خطأ في بدء Hermes: {e}")

    def start_services(self):
        services = [
            ("src/ai_router.py", "AI Router"),
            ("src/agent_mesh.py", "Agent Mesh"),
            ("src/bot.py", "Telegram Bot"),
            ("src/brain", "Brain System"),
            ("src/watcher.py", "Watcher System"),
        ]
        for script, name in services:
            if not self.is_running(script):
                self.logger.info(f"🚀 بدء {name}...")
                try:
                    subprocess.Popen([sys.executable, script],
                        cwd=str(self.workspace), stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, start_new_session=True)
                    self.logger.info(f"✅ {name} في العمل")
                except Exception as e:
                    self.logger.error(f"خطأ في بدء {name}: {e}")

    def monitor(self):
        while self.daemon_running:
            try:
                if not self.is_running("autonome_evolve.py"):
                    self.restart_count += 1
                    self.logger.warning(f"🔄 إعادة تشغيل النظام (المرة {self.restart_count})")
                    self.start_evolve()

                hermes_patterns = ["hermes_agent.py", "hermes", "ai_router.py", "agent_kernel.py", "agent_mesh.py"]
                if not any(self.is_running(p) for p in hermes_patterns):
                    self.logger.warning("⚠️  Hermes Agent متوقف، يتم إعادة التشغيل التلقائي...")
                    self.start_hermes()

                if not self.is_running("bot.py"):
                    self.logger.warning("⚠️  Telegram Bot متوقف، يتم إعادة التشغيل التلقائي...")
                    self.start_services()

                # Trade Cycle (loop.py --daemon) supervision: restart if the live 6-agent cycle dies
                if not self.is_running("loop.py"):
                    self.logger.info("🚀 بدء Trade Cycle loop (work/agents/trade_cycle/loop.py --daemon)...")
                    try:
                        subprocess.Popen(
                            [sys.executable, str(self.workspace / "work" / "agents" / "trade_cycle" / "loop.py"), "--daemon"],
                            cwd=str(self.workspace / "work" / "agents" / "trade_cycle"),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True,
                        )
                        self.logger.info("✅ Trade Cycle في العمل")
                    except Exception as e:
                        self.logger.error(f"خطأ في بدء Trade Cycle: {e}")

                time.sleep(180)
            except Exception as e:
                self.logger.error(f"خطأ في المراقبة: {e}")
                time.sleep(60)

    def run(self):
        atexit.register(self.cleanup)
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(str(os.getpid()))
        self.logger.info("🚀 بدء نظام التشغيل الذاتي لـ ESPRIEAETHER")
        self.logger.info("✅ الإعداد: يراقب كل الخدمات ويبدأها تلقائياً")
        self.start_evolve()
        self.start_hermes()
        self.start_services()
        # trade_cycle loop (loop.py --daemon) - a live 6-agent trading cycle
        if not self.is_running("loop.py --daemon"):
            self.logger.info("🚀 بدء Trade Cycle loop (work/agents/trade_cycle/loop.py --daemon)...")
            try:
                subprocess.Popen(
                    [sys.executable, str(self.workspace / "work" / "agents" / "trade_cycle" / "loop.py"), "--daemon"],
                    cwd=str(self.workspace / "work" / "agents" / "trade_cycle"),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                self.logger.info("✅ Trade Cycle في العمل")
            except Exception as e:
                self.logger.error(f"خطأ في بدء Trade Cycle: {e}")

        self.monitor()

if __name__ == "__main__":
    system = AutonomousSystem()
    system.run()
