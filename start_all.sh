#!/bin/bash
cd /c/Users/ESPRIEAETHER/Desktop/esprieaether
echo "Starting all services..."
echo "1. Starting AI Router (11435)..."
cd src
python3 ai_router.py > /tmp/router11435.log 2>&1 &
ROUTER_PID=$!
echo "Router PID: $ROUTER_PID"
sleep 5
echo "2. Checking status..."
for port in 5000 5001 8000 5100 5102 5103 5104 11435 11436 11437; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://localhost:$port/ 2>&1)
  if [ "$code" = "000" ] || [ -z "$code" ]; then echo "❌ $port"; else echo "✅ $port"; fi
done
echo "=== Router log ==="
tail -20 /tmp/router_direct.log 2>/dev/null
