@echo off
REM ============================================================
REM  EsprieAether Robots 24/7 — Windows service installer
REM  يدير Task Scheduler entry لي يشد الروبوتات على restart
REM ============================================================

set PYTHON=python
set DAEMON=%~dp0robot_daemon.py
set TASK=EsprieAetherRobots

if "%1"=="" goto help
if /i "%1"=="install" goto install
if /i "%1"=="uninstall" goto uninstall
if /i "%1"=="start" goto start
if /i "%1"=="stop" goto stop
if /i "%1"=="status" goto status
goto help

:install
echo [*] Installing scheduled task "%TASK%"...
schtasks /create /tn "%TASK%" /tr "\"%PYTHON%\" \"%DAEMON%\"" /sc onstart /rl highest /f
if errorlevel 1 (
    echo [!] Failed. Try running as Administrator.
    exit /b 1
)
echo [+] Installed. Robots will start on every boot.
echo [+] Start now:  %~nx0 start
goto :eof

:uninstall
echo [*] Removing task "%TASK%"...
schtasks /delete /tn "%TASK%" /f
goto :eof

:start
echo [*] Starting robots now...
start "EsprieAetherRobots" /min %PYTHON% "%DAEMON%"
echo [+] Started (minimized window). Log: robot_daemon.log
goto :eof

:stop
echo [*] Stopping robots...
taskkill /FI "WINDOWTITLE eq EsprieAetherRobots*" /F 2>nul
taskkill /IM python.exe /FI "MEMUSAGE gt 0" /F 2>nul
echo [+] Stopped
goto :eof

:status
echo [*] Task status:
schtasks /query /tn "%TASK%" /fo LIST 2>nul
echo.
echo [*] Running python processes:
tasklist /FI "IMAGENAME eq python.exe" 2>nul
goto :eof

:help
echo.
echo  EsprieAether Robots 24/7
echo  ========================
echo   %~nx0 install     Register on-boot task (needs Admin)
echo   %~nx0 uninstall   Remove task
echo   %~nx0 start       Start robots now (background)
echo   %~nx0 stop        Stop robots
echo   %~nx0 status      Show task + process status
echo.
goto :eof
