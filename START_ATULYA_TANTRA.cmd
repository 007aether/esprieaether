@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "ROOT=%~dp0"
set "VENDOR=%ROOT%GITHUB_IMPORT\Atulya-Tantra"
set "PY=%ROOT%esprieaether\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

if not exist "%VENDOR%\atulya\server.py" (
  echo [ESPRIEATHER] Atulya vendor is missing.
  exit /b 1
)

set "ATULYA_HOST=127.0.0.1"
set "ATULYA_PORT=8501"
set "ATULYA_DATA_DIR=%ROOT%esprieaether\state\atulya"
set "PYTHONPATH=%VENDOR%"
set "ATULYA_MODEL_PROVIDER=openai-compatible"
set "ATULYA_MODEL_NAME=dolphin3"
set "ATULYA_MODEL_BASE_URL=http://127.0.0.1:31416/v1"
set "ATULYA_MODEL_TIMEOUT=120"
set "ATULYA_FORCE_DARIJA=1"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"

"%PY%" -c "import fastapi, uvicorn, dotenv" >nul 2>&1
if errorlevel 1 (
  echo [ESPRIEATHER] Atulya dependencies are not installed in the local venv.
  echo [ESPRIEATHER] Install locally with: pip install -r GITHUB_IMPORT\Atulya-Tantra\requirements.lock.txt
  exit /b 1
)

"%PY%" -c "import mcp" >nul 2>&1
if errorlevel 1 echo [ESPRIEATHER] Optional MCP dependency missing: pip install mcp==2.3.0
"%PY%" -c "import faster_whisper" >nul 2>&1
if errorlevel 1 echo [ESPRIEATHER] Optional voice dependencies missing: see requirements.lock.txt

echo [ESPRIEATHER] Atulya-Tantra loopback on http://127.0.0.1:8501 (local brain 127.0.0.1:31416)
"%PY%" -m atulya.cli serve
exit /b !errorlevel!
