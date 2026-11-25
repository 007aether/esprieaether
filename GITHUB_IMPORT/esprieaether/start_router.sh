#!/bin/bash
cd /c/Users/ESPRIEAETHER/Desktop/esprieaether
echo "Starting AI Router on port 11435..."
cd src
nohup python3 ai_router.py > /tmp/router11435_nohup.log 2>&1 &
echo "Router started with PID $!"
sleep 8
echo "=== Checking port 11435 ==="
curl -s --max-time 3 http://localhost:11435/ 2>&1 | head -3
echo "=== Log ==="
tail -20 /tmp/router_direct.log 2>/dev/null
