#!/bin/bash
# EsprieAether — start all services detached (bash)
REPO=/c/Users/ESPRIEAETHER/Desktop/esprieaether
PY=/c/Users/ESPRIEAETHER/AppData/Local/hermes/installs/18613b2b4f703f95/environments/3aedbe718e9f420e85e71cffc762d2f8/venv/Scripts/python.exe
LOGDIR=/c/Users/ESPRIEAETHER/ESPRIEAETHER/data/logs
mkdir -p $LOGDIR

declare -A SVC=(
  [web]="src/web_interface.py"
  [router]="src/ai_router.py"
  [mesh]="src/agent_mesh.py"
  [cloud_desktop]="src/cloud_desktop_agent.py"
  [jarvis_dsh_relay]="src/jarvis_dsh_relay.py"
  [sunna]="src/sunna_api.py"
  [integrations]="src/integrations_adapter.py"
  [kanban]="src/veritas_kanban.py"
  [cloud_poller]="src/cloud_poller.py"
  [bot]="src/bot.py"
  [watchdog]="src/watchdog.py"
  [autonomous]="src/autonomous_loop.py"
  [vpn_daemon]="src/vpn_agent.py --daemon"
  [guardian]="src/guardian_agent.py"
)

for name in "${!SVC[@]}"; do
  log="$LOGDIR/$name.log"
  # kill any existing instance
  pkill -f "python.*src/${SVC[$name]}" 2>/dev/null
  sleep 1
  nohup $PY "${SVC[$name]}" > "$log" 2>&1 &
  echo "[$name] started pid=$! log=$log"
  sleep 2
done

echo "=== waiting 20s for services to bind ==="
sleep 20
echo "=== port check ==="
for port in 11434 11435 11437 5000 5001 5100 5102 5103 5104 5105; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://127.0.0.1:$port/ 2>&1)
  echo "port $port -> $code"
done
