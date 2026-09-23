import os
import subprocess
from pathlib import Path

def take_system_screenshot():
    try:
        import pyautogui
        screenshot_path = Path.home() / "AETHER_V8" / "screenshot.png"
        pyautogui.screenshot(screenshot_path)
        return str(screenshot_path)
    except Exception as e:
        return None

def execute_shell_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return f"✅ **نتيجة التنفيذ:**\n{result.stdout[:500]}"
        else:
            return f"❌ **خطأ في التنفيذ:**\n{result.stderr[:500]}"
    except Exception as e:
        return f"❌ استثناء: {e}"
