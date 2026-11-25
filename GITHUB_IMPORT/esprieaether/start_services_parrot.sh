#!/usr/bin/env bash
# AetherStartup for Parrot Linux — launches all EsprieAether services
set -e

REPO="$HOME/esprieaether"
PY="$REPO/.venv/bin/python"

echo "=== AetherStartup Parrot ==="
echo "Repo: $REPO"

# Activate venv if exists
if [ -f "$PY" ]; then
    echo "[ok] venv found"
else
    echo "[!] venv not found, run: python3 -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

# Services to start
SERVICES=(
    "src/ai_router.py"
    "src/web_interface.py"
    "src/homedock_dashboard.py"
    "src/sunna_api.py"
    "src/integrations_adapter.py"
    "src/veritas_kanban.py"
    "src/bot.py"
    "src/watchdog.py"
    "src/autonomous_loop.py"
    "src/vpn_agent.py --daemon"
)

echo "[*] Starting services..."
for svc in "${SERVICES[@]}"; do
    name=$(basename "$svc" .py)
    if pgrep -f "$svc" > /dev/null 2>&1; then
        echo "[skip] $name already running"
    else
        echo "[start] $name"
        nohup "$PY" $svc > "$REPO/data/logs/${name}.log" 2>&1 &
        sleep 0.5
    fi
done

# Ollama check
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "[start] ollama"
    nohup ollama serve > "$REPO/data/logs/ollama.log" 2>&1 &
    sleep 3
else
    echo "[skip] ollama already running"
fi

echo "[done] All services launched"
echo "Logs: $REPO/data/logs/"
