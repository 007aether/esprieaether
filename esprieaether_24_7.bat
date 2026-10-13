@echo off
REM ============================================================
REM  EsprieAether 24/7 — full stack launcher
REM  Starts: router, orchestrator, web, cloud-desktop, bot, watchdog
REM  Double-click or add to shell:startup for auto-restart on boot
REM ============================================================

setlocal
cd /d "%~dp0"

set PY=.venv\Scripts\python.exe
set OLLAMA_MODELS=C:\Users\ESPRIEAETHER\.ollama\models

echo [*] EsprieAether 24/7 — starting all services...

REM ollama (skip if already running)
curl -s -m 3 http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [+] starting ollama...
    start "" /min "%USERPROFILE%\.local\bin\ollama.exe" serve
    timeout /t 5 /nobreak >nul
)

echo [+] starting router (11435)...
start "" /min "%PY%" src\ai_router.py

timeout /t 3 /nobreak >nul
echo [+] starting orchestrator (11436)...
start "" /min "%PY%" src\orchestrator.py

timeout /t 2 /nobreak >nul
echo [+] starting web interface (5000)...
start "" /min "%PY%" src\web_interface.py

timeout /t 2 /nobreak >nul
echo [+] starting cloud desktop (5001)...
start "" /min "%PY%" src\cloud_desktop_agent.py

timeout /t 2 /nobreak >nul
echo [+] starting telegram bot...
start "" /min "%PY%" src\bot.py

timeout /t 3 /nobreak >nul
echo [+] starting JARVIS OSINT (8000)...
start "" /min "%LOCALAPPDATA%\Temp\JARVIS_repoackend\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir "%LOCALAPPDATA%\Temp\JARVIS_repoackend"

timeout /t 3 /nobreak >nul
echo [+] starting Sunna API bridge (5100)...
start "" /min "%PY%" src\sunna_api.py

timeout /t 3 /nobreak >nul
echo [+] starting bot heartbeat (cronpulse-style alerts)...
start "" /min "%PY%" srcot_heartbeat.py

timeout /t 2 /nobreak >nul
echo [+] starting kanban board (5103)...
start "" /min "%PY%" srceritas_kanban.py

timeout /t 2 /nobreak >nul
echo [+] starting HomeDock dashboard (5104)...
start "" /min "%PY%" src\homedock_dashboard.py

timeout /t 2 /nobreak >nul
echo [+] starting integrations adapter (5102)...
start "" /min "%PY%" src\integrations_adapter.py

timeout /t 3 /nobreak >nul
echo [+] starting watchdog (self-healing)...
start "" /min "%PY%" src\watchdog.py

echo.
echo [OK] All services started. Watchdog keeps them alive 24/7.
echo      Control center: http://localhost:5000/control
echo.
pause
