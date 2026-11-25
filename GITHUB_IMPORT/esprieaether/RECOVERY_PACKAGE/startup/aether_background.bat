@echo off
REM ============================================
REM  AETHER - Self-Healing System (Background)
REM  ============================================
REM  تشغيل خلفية دائمة - لا يقفل
REM  ============================================

setlocal

echo AETHER Background System Starting...
echo ============================================

cd /d C:\Users\ESPRIEAETHER\Desktop\esprieaether

REM تحديد مسارات Python
set PYTHON_PATH=C:\Users\ESPRIEAETHER\AppData\Local\Programs\Python\Python315\python.exe

echo Detecting Python...
if not exist "%PYTHON_PATH%" set PYTHON_PATH=python

echo Using Python: %PYTHON_PATH%

REM إنشاء سجل الأحداث
if not exist "data\logs" mkdir data\logs

REM تشغيل جميع الوكلاء كعمليات خلفية
echo Starting background agents...

REM وكيل الشبكة
echo Starting Network Monitor...
start /B "%PYTHON_PATH%" src\agents\network_monitor.py >> data\logs\network_monitor.log 2>&1

REM وكيل الأمان
echo Starting Security Agent...
start /B "%PYTHON_PATH%" src\agents\security_agent.py >> data\logs\security_agent.log 2>&1

REM وكيل الذاكرة
echo Starting Memory Agent...
start /B "%PYTHON_PATH%" src\agents\memory_agent.py >> data\logs\memory_agent.log 2>&1

REM وكيل التقارير
echo Starting Daily Report...
start /B "%PYTHON_PATH%" src\agents\daily_report.py >> data\logs\daily_report.log 2>&1

REM وكيل التحليل التنبؤي
echo Starting Predictive Analyzer...
start /B "%PYTHON_PATH%" src\agents\predictive_analyzer.py >> data\logs\predictive_analyzer.log 2>&1

REM وكيل التداول
echo Starting Trading Bot...
start /B "%PYTHON_PATH%" src\agents\trading_bot.py >> data\logs\trading_bot.log 2>&1

REM وكيل إصلاح الأخطاء
echo Starting Error Fix Agent...
start /B "%PYTHON_PATH%" src\agents\error_fix_agent.py >> data\logs\error_fix_agent.log 2>&1

REM وكيل دعم اللغة العربية
echo Starting Arabic Support...
start /B "%PYTHON_PATH%" src\agents\arabic_support.py >> data\logs\arabic_support.log 2>&1

REM وكييل الوثائق (Knowledge Base)
echo Starting Knowledge Base...
start /B "%PYTHON_PATH%" src\agents\knowledge_base.py >> data\logs\knowledge_base.log 2>&1

echo Agents started successfully!
echo ============================================

echo AETHER System is now running in background...
echo To stop all agents, close this window or run:
echo   taskkill /F /IM python.exe

REM الحفاظ على فتح النافذة لرؤية الأخطاء
timeout /t 3600 >nul
cmd /k
