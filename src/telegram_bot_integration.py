import json
from pathlib import Path
from lab_generator import generate_custom_tool
from real_mainnet_bridge import check_mainnet_readiness

def telegram_command_handler(command):
    print(f"==================================================")
    print(f"📱 [TELEGRAM COMMAND RECEIVED]: {command}")
    print(f"==================================================")
    
    if command == "/scan":
        result = generate_custom_tool("security_scanner")
        print(f"[+] النتيجة: {result}")
        return result
    elif command == "/mainnet":
        result = check_mainnet_readiness()
        print(f"[+] النتيجة: {result}")
        return result
    else:
        return "أمر غير معروف. استخدم /scan أو /mainnet"

if __name__ == "__main__":
    # محاكاة تلقي الأوامر من التيليغرام
    telegram_command_handler("/scan")
    telegram_command_handler("/mainnet")
