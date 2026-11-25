@echo off
setlocal
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERREUR] venv introuvable: %PY%
  exit /b 1
)
set "TELEGRAM_LIVE=0"
set "PYTHONIOENCODING=utf-8"
echo Rapport local, aucun envoi Telegram (TELEGRAM_LIVE=0).
"%PY%" espria_bot.py
endlocal
