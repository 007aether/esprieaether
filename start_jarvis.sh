#!/bin/bash
cd /c/Users/ESPRIEAETHER/Desktop/esprieaether
echo "Starting Jarvis OSINT Backend on port 8000..."
cd src
nohup python3 jarvis_api.py > /tmp/jarvis_8000.log 2>&1 &
echo "Jarvis started with PID $!"
sleep 5
echo "=== Checking ==="
curl -s --max-time 3 http://localhost:8000/ 2>&1 | head -5
echo "=== Log ==="
tail -10 /tmp/jarvis_8000.log 2>/dev/null
