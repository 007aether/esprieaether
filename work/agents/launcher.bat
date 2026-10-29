@echo off
title Agents System Launcher
cd /d C:\Users\ESPRIEAETHER\Desktop\esprieaether

echo.
echo  ========================================
echo  EsprieAether — Agents System Launcher
echo  ========================================
echo.
echo  [1] Market Intelligence Agent (سوق الحديد)
echo  [2] Business Development Agent (الشراكات)
echo.
set /p choice=Select an agent to start (1-2): 

if "%choice%"=="1" goto :market
if "%choice%"=="2" goto :business
echo Invalid choice.
pause
exit /b

:market
echo.
echo Starting Market Intelligence Agent...
cd work\agents\market_intel
python agent.py
pause
exit /b

:business
echo.
echo Starting Business Development Agent...
cd work\agents\business_dev
python agent.py
pause
exit /b
