"""نص رفع الملفات إلى GitHub"""
from github_agent import GitHubAgent
from pathlib import Path
import datetime

BASE = Path.home() / "AETHER_V8"

# 1) فحص الاتصال
agent = GitHubAgent()
status = agent.ping()
print(f"▶ الحالة: {status}\n")

if status["status"] != "online":
    print("❌ GitHub غير متصل")
    exit(1)

# 2) إنشاء README.md
readme = BASE / "README.md"
readme.write_text("""# ⚡ EsprieAether

نظام سيبراني محلي متكامل مع JARVIS Command Center.

## المكونات
- 🤖 JARVIS (Ollama + qwen2.5:3b)
- 💬 Telegram Bot (@Esprieaether_bot)
- 🌐 Web Dashboard (Flask على localhost:5000)
- 🔐 Security Agent
- 💰 Somnia Testnet Automation
- 📡 Airdrop Tracker

## التشغيل
sudo systemctl status aether-web aether-bot

## الروابط
- Dashboard: http://localhost:5000
- Telegram: @Esprieaether_bot

---
آخر تحديث تلقائي: """ + datetime.datetime.now().isoformat())

# 3) رفع README
print("▶ رفع README.md...")
result = agent.push_file(str(readme), "README.md")
print(f"   النتيجة: {result}\n")

# 4) رفع ملفات المشروع
print("▶ رفع ملفات المشروع الأساسية...")
files = [
    BASE / "src" / "jarvis_bridge.py",
    BASE / "src" / "web_interface.py",
    BASE / "src" / "bot.py",
    BASE / "src" / "github_agent.py",
    BASE / "run.sh",
    BASE / "STATUS.md",
]
existing = [f for f in files if f.exists()]
print(f"   عدد الملفات: {len(existing)}")

result2 = agent.push_files(existing)
print(f"   النتيجة: {result2}")
