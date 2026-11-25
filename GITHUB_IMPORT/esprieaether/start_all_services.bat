@echo off
REM ============================================================
REM  Startup script for ESPRIEAETHER autonomous system (2026)
REM  All services run as background processes
REM ============================================================
setlocal
cd /d C:\Users\ESPRIEAETHER\Desktop\esprieaether
set VENV=.venv\Scripts\python.exe

echo ===============================================
echo  Starting ESPRIEAETHER Autonomous System
echo ===============================================
echo.

REM 1. AI Router (port 11435)
echo [1/12] AI Router (port 11435)...
start /B "%VENV%" src\ai_router.py > data\logs\ai_router.log 2>&1
echo AI Router started.

REM 2. Orchestrator (port 11436)
echo [2/12] Orchestrator (port 11436)...
start /B "%VENV%" src\orchestrator.py > data\logs\orchestrator.log 2>&1
echo Orchestrator started.

REM 3. Agent Mesh (port 11437)
echo [3/12] Agent Mesh (port 11437)...
start /B "%VENV%" src\agent_mesh.py > data\logs\agent_mesh.log 2>&1
echo Agent Mesh started.

REM 4. Cloud Desktop (port 5001)
echo [4/12] Cloud Desktop (port 5001)...
start /B "%VENV%" src\cloud_desktop_agent.py > data\logs\cloud_desktop.log 2>&1
echo Cloud Desktop started.

REM 5. Sunna API Bridge (port 5100)
echo [5/12] Sunna API Bridge (port 5100)...
start /B "%VENV%" src\sunna_api.py > data\logs\sunna_api.log 2>&1
echo Sunna API started.

REM 6. JARVIS Web Interface (port 5000)
echo [6/12] JARVIS Web Interface (port 5000)...
start /B "%VENV%" src\web_interface.py > data\logs\jarvis_web.log 2>&1
echo JARVIS Web started.

REM 7. G0DM0D3 UI (port 3860)
echo [7/12] G0DM0D3 UI (port 3860)...
cd /d C:\Users\ESPRIEAETHER\Desktop\esprieaether\G0DM0D3
start /B npx serve@latest out -l 3860 > C:\Users\ESPRIEAETHER\Desktop\esprieaether\data\logs\g0dm0d3.log 2>&1
cd /d C:\Users\ESPRIEAETHER\Desktop\esprieaether
echo G0DM0D3 started.

echo.
echo ===============================================
echo === Services started successfully! ===
echo ===============================================
echo Logs in: data\logs\
echo.
pause
