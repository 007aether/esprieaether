@echo off
cd /d "%~dp0"
set "NODE=%~dp0.tools\node-v26.13.1\node.exe"
if not exist "%NODE%" (
  echo [ERREUR] Node introuvable : %NODE%
  pause
  exit /b 1
)
"%NODE%" --test tests\dashboard.test.mjs
pause
