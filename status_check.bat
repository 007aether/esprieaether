@echo off
REM ============================================================
REM  ESPRIEATHER SYSTEM STATUS CHECK (Windows)
REM  Check all services status
REM  Usage: Double-click or run in PowerShell
REM ============================================================

echo.
echo ============================================
echo   ESPRIEATHER SYSTEM STATUS CHECK
echo   Date: %date% %time%
echo ============================================
echo.

echo ─── 🧠 OLLM (Full Brain) ───
tasklist /fi "imagename eq ollama.exe" 2>nul | find "ollama" >nul
if %errorlevel% equ 0 (
    echo [OK] RUNNING (Ollama process found)
) else (
    echo [ERROR] NOT RUNNING
)
echo.

echo ─── 🤖 AI ROUTER ───
tasklist /fi "imagename eq python.exe" 2>nul | find "ai_router" >nul
if %errorlevel% equ 0 (
    echo [OK] RUNNING
) else (
    echo [INFO] Starting AI Router...
    .venv\Scripts\activate
    python src\ai_router.py > data\logs\ai_router.log 2>&1
    echo [OK] Started
)
echo.

echo ─── 💻 WEB INTERFACE ───
tasklist /fi "imagename eq python.exe" 2>nul | find "web_interface" >nul
if %errorlevel% equ 0 (
    echo [OK] RUNNING
) else (
    echo [INFO] Starting Web Interface...
    .venv\Scripts\activate
    python src\web_interface.py > data\logs\web_interface.log 2>&1
    echo [OK] Started
)
echo.

echo ─── 🔄 AUTONOMOUS LOOP ───
tasklist /fi "imagename eq python.exe" 2>nul | find "autonomous_loop" >nul
if %errorlevel% equ 0 (
    echo [OK] RUNNING
) else (
    echo [INFO] Starting Autonomous Loop...
    .venv\Scripts\activate
    python src\autonomous_loop.py > data\logs\autonomous_loop.log 2>&1
    echo [OK] Started
)
echo.

echo ─── 📱 TELEGRAM BOT 1 (Esprieaether_bot) ───
tasklist /fi "imagename eq python.exe" 2>nul | find "bot.py" >nul
if %errorlevel% equ 0 (
    echo [OK] RUNNING (Bot 1)
) else (
    echo [INFO] Starting Bot 1...
    .venv\Scripts\activate
    python src\bot.py > data\logs\bot.log 2>&1
    echo [OK] Started
)
echo.

echo ─── 📱 TELEGRAM BOT 2 (ESPRIEXAETHER_bot) ───
tasklist /fi "imagename eq python.exe" 2>nul | find "bot.py" >nul
if %errorlevel% equ 0 (
    echo [OK] RUNNING (Bot 2)
) else (
    echo [INFO] Starting Bot 2...
    .venv\Scripts\activate
    set BOT_ENV=.env.bot2
    python src\bot.py > data\logs\bot2.log 2>&1
    echo [OK] Started
)
echo.

echo.
echo ============================================
echo   STATUS CHECK COMPLETE
echo ============================================
echo.
echo 🌐 Web Interface:     http://localhost:5000
echo 🧠 AI Router:         http://localhost:11435
echo 🤖 Ollama API:        http://localhost:11434
echo 📱 Telegram Bot 1:    @Esprieaether_bot
echo 📱 Telegram Bot 2:    @ESPRIEXAETHER_bot
echo.
echo Log files:
echo    data\logs\ai_router.log
echo    data\logs\web_interface.log
echo    data\logs\autonomous_loop.log
echo    data\logs\bot.log
echo    data\logs\bot2.log
echo.
echo To check logs: type "data\logs\<filename>.log"
echo.
pause
