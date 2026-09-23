import time
import subprocess
from pathlib import Path

print("[+] EsprieAether Autonomous Loop Started (24/7)...")

while True:
    try:
        # تشغيل وكيل صيد الأيردروبات والـ Lab كل ساعة أوتوماتيكياً
        print("[*] Executing background intelligence & farming cycle...")
        subprocess.run(["python3", "-c", "from bounty_farmer import hunt_bounties_and_airdrops; print(hunt_bounties_and_airdrops())"], check=False)
        
        # الانتظار لمدة ساعة قبل الدورة الموالية (3600 ثانية)
        time.sleep(3600)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"[-] Loop error: {e}")
        time.sleep(60)
