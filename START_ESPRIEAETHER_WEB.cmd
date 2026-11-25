@echo off
cd /d "%~dp0esprieaether"
set "PY=%~dp0esprieaether\.venv\Scripts\python.exe"
set "OLLAMA_HOST=http://127.0.0.1:11434"
if not exist "%PY%" (
  echo [ERREUR] Python introuvable : %PY%
  pause
  exit /b 1
)
echo EsprieAether - JARVIS Web (sans Telegram) - http://127.0.0.1:5000/
echo Appuyez sur Ctrl+C pour arreter le serveur.
"%PY%" start_web_server.py
if errorlevel 1 (
  echo [ERREUR] Le serveur s'est arrete anormalement.
  pause
)
