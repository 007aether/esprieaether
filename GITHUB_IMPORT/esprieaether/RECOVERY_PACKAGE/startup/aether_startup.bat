@echo off
REM ============================================
REM  AETHER - Self-Healing System (Startup)
REM  ============================================
REM  تشغيل تلقائي عند البدء
REM  ============================================

echo AETHER System Starting...
echo ============================================

REM تحديد مسار Python
set PYTHON_PATH=C:\Users\ESPRIEAETHER\AppData\Local\Programs\Python\Python315\python.exe
if not exist "%PYTHON_PATH%" set PYTHON_PATH=python

cd /d C:\Users\ESPRIEAETHER\Desktop\esprieaether

REM إنشاء مجلدات السجلات
if not exist data\logs mkdir data\logs

REM تشغيل الوكلاء الخلفية (بلا تقاطع)
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
echo Background agents started successfully!

echo Starting main GUI...
echo ============================================

REM تشغيل اللوحة الأم
"%PYTHON_PATH%" src\agents\simple_gui.py

REM إذا انتهت النافذة، ارجع للخلفية مرة أخرى
echo GUI closed. Restarting background agents...
start /B "%PYTHON_PATH%" src\agents\network_monitor.py >> data\logs\network_monitor.log 2>&1
start /B "%PYTHON_PATH%" src\agents\security_agent.py >> data\logs\security_agent.log 2>&1
start /B "%PYTHON_PATH%" src\agents\memory_agent.py >> data\logs\memory_agent.log 2>&1
start /B "%PYTHON_PATH%" src\agents\daily_report.py >> data\logs\daily_report.log 2>&1
start /B "%PYTHON_PATH%" src\agents\predictive_analyzer.py >> data\logs\predictive_analyzer.log 2>&1
start /B "%PYTHON_PATH%" src\agents\trading_bot.py >> data\logs\trading_bot.log 2>&1
start /B "%PYTHON_PATH%" src\agents\error_fix_agent.py >> data\logs\error_fix_agent.log 2>&1
start /B "%PYTHON_PATH%" src\agents\arabic_support.py >> data\logs\arabic_support.log 2>&1
start /B "%PYTHON_PATH%" src\agents\knowledge_base.py >> data\logs\knowledge_base.log 2>&1

echo System restarted automatically.
echo ============================================
timeout /t 60
