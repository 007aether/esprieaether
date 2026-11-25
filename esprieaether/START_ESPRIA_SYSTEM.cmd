@echo off
setlocal
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERREUR] venv introuvable: %PY%
  exit /b 1
)
echo Demarrage EspriaAether sur http://127.0.0.1:5001 ...
"%PY%" -m uvicorn espria_system:app --host 127.0.0.1 --port 5001
endlocal
