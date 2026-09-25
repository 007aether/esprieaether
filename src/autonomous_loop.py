import time
import psutil
from datetime import datetime
from wallet.manager import get_existing_wallet
from lab_generator import generate_custom_tool

def autonomous_heartbeat():
    print(f"==================================================")
    print(f"🤖 [AETHER AUTONOMOUS PULSE] - {datetime.now()}")
    print(f"==================================================")
    
    # 1. فحص الحالة العتادية
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    print(f"[+] حالة العتاد الفعلي: CPU = {cpu}% | RAM = {ram}%")
    
    # 2. التحقق من المحفظة الحقيقية
    w = get_existing_wallet()
    print(f"[+] المحفظة النشطة: {w.get('address', 'Unknown')}")
    
    # 3. توليد أداة صيانة خفيفة في الـ Lab
    tool_msg = generate_custom_tool("auto_optimizer")
    print(f"[+] {tool_msg}")
    print(f"==================================================\n")

if __name__ == "__main__":
    print("🚀 بدء تشغيل حلقة الأتمتة المستمرة لـ EsprieAether...")
    while True:
        try:
            autonomous_heartbeat()
            # التوقف لمدة ساعة بين كل دورة وأخرى (أو يمكنك تعديلها)
            time.sleep(3600)
        except KeyboardInterrupt:
            print("\n🛑 توقفت الحلقة المستمرة بناءً على طلب المستخدم.")
            break

# إضافة وكيل صيد الأيردروبات التلقائي للحلقة المستمرة
from testnet_farmer import simulate_testnet_tx

def trigger_scheduled_farming():
    print("[+] ⏰ تشغيل الدورة المجدولة لصيد الأيردروبات...")
    simulate_testnet_tx()

