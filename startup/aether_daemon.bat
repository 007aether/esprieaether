@echo off
REM ============================================
REM  AETHER - Background System (Daemon)
REM  ============================================
REM  تشغيل دوري دائم بدون واجهة رسومية
REM  ============================================

setlocal

echo AETHER Background System (Daemon) Starting...
echo ============================================

cd /d C:\Users\ESPRIEAETHER\Desktop\esprieaether

set PYTHON_PATH=C:\Users\ESPRIEAETHER\AppData\Local\Programs\Python\Python315\python.exe
if not exist "%PYTHON_PATH%" set PYTHON_PATH=python

if not exist data\logs mkdir data\logs

echo Starting background agents...
start /B "%PYTHON_PATH%" src\agents\network_monitor.py >> data\logs\network_monitor.log 2>&1
start /B "%PYTHON_PATH%" src\agents\security_agent.py >> data\logs\security_agent.log 2>&1
start /B "%PYTHON_PATH%" src\agents\memory_agent.py >> data\logs\memory_agent.log 2>&1
start /B "%PYTHON_PATH%" src\agents\daily_report.py >> data\logs\daily_report.log 2>&1
start /B "%PYTHON_PATH%" src\agents\predictive_analyzer.py >> data\logs\predictive_analyzer.log 2>&1
start /B "%PYTHON_PATH%" src\agents\trading_bot.py >> data\logs\trading_bot.log 2>&1
start /B "%PYTHON_PATH%" src\agents\error_fix_agent.py >> data\logs\error_fix_agent.log 2>&1
start /B "%PYTHON_PATH%" src\agents\arabic_support.py >> data\logs\arabic_support.log 2>&1
start /B "%PYTHON_PATH%" src\agents\knowledge_base.py >> data\logs\knowledge_base.log 2>&1
echo Background agents started!

echo Waiting... (Ctrl+C to stop)
echo ============================================

REM الحفاظ على التشغيل الدائم
ping -n 3600 127.0.0.1 >nul 2>&1
echo "Duration: 60 minutes elapsed"
