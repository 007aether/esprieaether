#!/usr/bin/env python3
"""
==========================================
  AETHER LOOP - حلقة التشغيل الدائمة
==========================================
يعيد تشغيل كل وكيل كل 300 ثانية
"""
import subprocess
import sys
import time
from pathlib import Path

PROJECT_DIR = Path("C:/Users/ESPRIEAETHER/Desktop/esprieaether")
LOGS_DIR = PROJECT_DIR / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# الوكلاء الأساسيون
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
    "health_check.py",
    "news_agent.py",
    "wall_of_text.py",
]

# فترة التنفيذ (بالثواني)
PERIOD = 180  # كل 3 دقائق

while True:
    for name in AGENTS:
        log_path = LOGS_DIR / f"loop_{name.replace('.py', '')}.log"
        with open(log_path, 'w', encoding='utf-8') as f:
            try:
                result = subprocess.run(
                    [sys.executable, str(PROJECT_DIR / "src" / "agents" / name)],
                    stdout=f, stderr=subprocess.STDOUT, timeout=120
                )
                status = "✅" if result.returncode == 0 else "❌"
                print(f"[{time.strftime('%H:%M:%S')}] {status} {name}")
            except subprocess.TimeoutExpired:
                print(f"[{time.strftime('%H:%M:%S')}] ⏱️ {name} في انتظار")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] ❌ {name}: {e}")
    print(f"[{time.strftime('%H:%M:%S')}] ⏳ الانتظار {PERIOD} ثانية...")
    time.sleep(PERIOD)
