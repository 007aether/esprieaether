@echo off
REM ============================================================
REM  AetherDocker — self-elevating dockerd launcher
REM  Double-click once (one UAC click) or keep in shell:startup.
REM  dockerd then runs hidden; PC keeps the services non-elevated.
REM ============================================================

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges for dockerd...
    powershell -NoProfile -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
    exit /b
)

cd /d "%LOCALAPPDATA%\Temp\docker\docker"
if not exist "%LOCALAPPDATA%\Temp\docker\data" mkdir "%LOCALAPPDATA%\Temp\docker\data"
start "" /min dockerd.exe -H npipe://./pipe/docker_engine --data-root "%LOCALAPPDATA%\Temp\docker\data"
echo dockerd started (hidden window). Verify with: docker version
timeout /t 4 /nobreak >nul
