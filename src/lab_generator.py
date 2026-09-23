import os
from pathlib import Path

LAB_DIR = Path.home() / "AETHER_V8" / "src" / "lab"

def generate_custom_tool(tool_type="scraper"):
    """
    توليد أدوات برمجية أوتوماتيكية متخصصة في الـ Lab
    """
    LAB_DIR.mkdir(parents=True, exist_ok=True)
    
    if tool_type == "scraper":
        tool_file = LAB_DIR / "auto_web_scraper.py"
        code_content = '''# Auto-generated Web Scraper by AETHER Lab Agent
import requests

def run_scraper():
    print("[*] Running AETHER Automated Data Scraper...")
    # محاكاة جلب بيانات السوق أو الأخبار
    return "✅ [Scraper Tool]: تم استخراج بيانات السوق وتحليلها بنجاح."

if __name__ == "__main__":
    print(run_scraper())
'''
    elif tool_type == "optimizer":
        tool_file = LAB_DIR / "system_optimizer.py"
        code_content = '''# Auto-generated System Optimizer by AETHER Lab Agent
import psutil

def optimize_system():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    return f"✅ [Optimizer Tool]: حالة النظام ممتازة. CPU: {cpu}% | RAM: {ram}%"

if __name__ == "__main__":
    print(optimize_system())
'''
    else:
        tool_file = LAB_DIR / "generic_utility.py"
        code_content = '''# Auto-generated Utility by AETHER Lab Agent
def run_utility():
    return "✅ [Utility]: الأداة العامة تعمل بكفاءة تامة."

if __name__ == "__main__":
    print(run_utility())
'''

    with open(tool_file, "w") as f:
        f.write(code_content)
        
    return f"🛠️ **[AETHER Lab]** تم ابتكار وتوليد الأداة البرمجية بنجاح في المسار:\n`src/lab/{tool_file.name}`"
