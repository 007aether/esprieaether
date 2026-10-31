#!/bin/bash
# ============================================================
# ESPRIEATHER SYSTEM STATUS CHECK SCRIPT
# Check all services status
# Usage: bash status_check.sh
# ============================================================

REPO="/home/esprieaether/esprieaether"

echo "========================================"
echo "  ESPRIEATHER SYSTEM STATUS CHECK"
echo "  Date: $(date)"
echo "========================================"
echo ""

# Check Ollama (Full Brain)
echo "─── 🧠 OLLM (Full Brain) ───"
if ps aux | grep "ollama serve" | grep -v grep > /dev/null; then
    OLLAMA_PID=$(ps aux | grep "ollama serve" | grep -v grep | awk '{print $2}')
    echo "   ✅ RUNNING"
    echo "   PID: $OLLAMA_PID"
    echo "   Port: 11434"
    echo "   Model: $(ollama list 2>/dev/null | grep -E 'qwen2.5-coder|llama' | awk '{print $1}')"
else
    echo "   ❌ NOT RUNNING"
fi
echo ""

# Check AI Router
echo "─── 🤖 AI ROUTER ───"
if ps aux | grep "src/ai_router.py" | grep -v grep > /dev/null; then
    AI_ROUTER_PID=$(ps aux | grep "src/ai_router.py" | grep -v grep | awk '{print $2}')
    echo "   ✅ RUNNING"
    echo "   PID: $AI_ROUTER_PID"
    echo "   Port: 11435"
    echo "   Log: data/logs/ai_router.log"
else
    echo "   ❌ NOT RUNNING"
fi
echo ""

# Check Web Interface
echo "─── 💻 WEB INTERFACE ───"
if ps aux | grep "src/web_interface.py" | grep -v grep > /dev/null; then
    WEB_PID=$(ps aux | grep "src/web_interface.py" | grep -v grep | awk '{print $2}')
    echo "   ✅ RUNNING"
    echo "   PID: $WEB_PID"
    echo "   Port: 5000"
    echo "   Log: data/logs/web_interface.log"
else
    echo "   ❌ NOT RUNNING"
fi
echo ""

# Check Autonomous Loop
echo "─── 🔄 AUTONOMOUS LOOP ───"
if ps aux | grep "src/autonomous_loop.py" | grep -v grep > /dev/null; then
    AUTO_PID=$(ps aux | grep "src/autonomous_loop.py" | grep -v grep | awk '{print $2}')
    echo "   ✅ RUNNING"
    echo "   PID: $AUTO_PID"
    echo "   Log: data/logs/autonomous_loop.log"
else
    echo "   ❌ NOT RUNNING"
fi
echo ""

# Check Telegram Bot 1
echo "─── 📱 TELEGRAM BOT 1 (Esprieaether_bot) ───"
if ps aux | grep "src/bot.py" | grep -v grep | head -1 > /dev/null; then
    BOT1_PID=$(ps aux | grep "src/bot.py" | grep -v grep | head -1 | awk '{print $2}')
    echo "   ✅ RUNNING"
    echo "   PID: $BOT1_PID"
    echo "   Token: 8620629158:***"
    echo "   Log: data/logs/bot.log"
else
    echo "   ❌ NOT RUNNING"
fi
echo ""

# Check Telegram Bot 2
echo "─── 📱 TELEGRAM BOT 2 (ESPRIEXAETHER_bot) ───"
if ps aux | grep "src/bot.py" | grep -v grep | tail -1 > /dev/null; then
    BOT2_PID=$(ps aux | grep "src/bot.py" | grep -v grep | tail -1 | awk '{print $2}')
    echo "   ✅ RUNNING"
    echo "   PID: $BOT2_PID"
    echo "   Token: 8853973061:***"
    echo "   Log: data/logs/bot2.log"
else
    echo "   ❌ NOT RUNNING"
fi
echo ""

# Check listening ports
echo "─── 🌐 LISTENING PORTS ───"
echo "   11434 (Ollama): $(ss -tlnp 2>/dev/null | grep -c '11434' | awk '{print $1}')"
echo "   11435 (AI Router): $(ss -tlnp 2>/dev/null | grep -c '11435' | awk '{print $1}')"
echo "   5000 (Web Interface): $(ss -tlnp 2>/dev/null | grep -c '5000' | awk '{print $1}')"
echo ""

# Check log files
echo "─── 📁 LOG FILES ───"
LOG_COUNT=$(ls data/logs/*.log 2>/dev/null | wc -l)
echo "   Total log files: $LOG_COUNT"
echo ""

# Summary
echo "========================================"
echo "  SUMMARY"
echo "========================================"
echo "   Ollama:     $(ps aux | grep 'ollama serve' | grep -v grep | wc -l) running"
echo "   AI Router:  $(ps aux | grep 'src/ai_router.py' | grep -v grep | wc -l) running"
echo "   Web UI:     $(ps aux | grep 'src/web_interface.py' | grep -v grep | wc -l) running"
echo "   Autonomous: $(ps aux | grep 'src/autonomous_loop.py' | grep -v grep | wc -l) running"
echo "   Bot 1:      $(ps aux | grep 'src/bot.py' | grep -v grep | head -1 | wc -l) running"
echo "   Bot 2:      $(ps aux | grep 'src/bot.py' | grep -v grep | tail -1 | wc -l) running"
echo ""
echo "========================================"
echo "  ✅ ALL SERVICES ARE RUNNING!"
echo "========================================"
