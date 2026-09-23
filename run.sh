#!/bin/bash
cd ~/AETHER_V8
source .venv/bin/activate

while true; do
    echo "[*] Launching EsprieAether Jarvis Web Dashboard & Bot..."
    # تشغيل سيرفر الويب للواجهة في الخلفية
    python3 src/web_interface.py &
    WEB_PID=$!
    
    # تشغيل بوت تيليغرام
    python3 src/bot.py >> bot.log 2>&1
    
    # إذا توقف أحدهما، أعد التشغيل
    kill $WEB_PID 2>/dev/null
    echo "[-] System stopped. Restarting in 3 seconds..."
    sleep 3
done
