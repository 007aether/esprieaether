@echo off
REM ============================================================
REM  ESPRIEATHER SYSTEM SETUP SCRIPT (Windows)
REM  Simple setup and start script
REM  Usage: Double-click or run in PowerShell
REM ============================================================

echo.
echo ============================================
echo  ESPRIEATHER SYSTEM SETUP
echo ============================================
echo.

REM Check if Python is installed
echo [1/8] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo [INFO] Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found: %PYTHON_VERSION%
echo.

REM Activate virtual environment (create if needed)
echo [2/8] Setting up virtual environment...
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)
echo [OK] Virtual environment ready
echo.

REM Activate venv
echo [3/8] Activating virtual environment...
call .venv\Scripts\activate
echo [OK] Virtual environment activated
echo.

REM Install requirements
echo [4/8] Installing required packages...
if exist "requirements.txt" (
    pip install -r requirements.txt
)
pip install python-telegram-bot flask psutil defusedxml
echo [OK] Packages installed
echo.

REM Copy .env file if not exists
echo [5/8] Setting up configuration files...
if not exist ".env" (
    copy .env.example .env >nul 2>&1
    echo [INFO] Created .env file from template
) else (
    echo [OK] .env file exists
)
if not exist ".env.bot1" (
    copy .env.bot1.example .env.bot1 >nul 2>&1
    echo [INFO] Created .env.bot1 file from template
)
if not exist ".env.bot2" (
    copy .env.bot2.example .env.bot2 >nul 2>&1
    echo [INFO] Created .env.bot2 file from template
)
echo [OK] Configuration files ready
echo.

REM Check if Ollama is installed
echo [6/8] Checking Ollama installation...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Ollama not found!
    echo [INFO] Please install from https://ollama.ai
    set OLLAMA_INSTALLED=false
) else (
    echo [OK] Ollama found
    set OLLAMA_INSTALLED=true
)
echo.

REM Start services
echo [7/8] Starting services...
echo.

REM Start AI Router
echo --- Starting AI Router ---
python src\ai_router.py > data\logs\ai_router.log 2>&1
echo [OK] AI Router started
echo.

REM Start Web Interface
echo --- Starting Web Interface ---
python src\web_interface.py > data\logs\web_interface.log 2>&1
echo [OK] Web Interface started
echo.

REM Start Autonomous Loop
echo --- Starting Autonomous Loop ---
python src\autonomous_loop.py > data\logs\autonomous_loop.log 2>&1
echo [OK] Autonomous Loop started
echo.

REM Start Telegram Bot 1
echo --- Starting Telegram Bot 1 (Esprieaether_bot) ---
python src\bot.py > data\logs\bot.log 2>&1
echo [OK] Bot 1 started
echo.

REM Start Telegram Bot 2
echo --- Starting Telegram Bot 2 (ESPRIEXAETHER_bot) ---
set BOT_ENV=.env.bot2
python src\bot.py > data\logs\bot2.log 2>&1
echo [OK] Bot 2 started
echo.

echo.
echo ============================================
echo  SERVICES STARTED
echo ============================================
echo.
echo 🌐 Web Interface:     http://localhost:5000
echo 🧠 AI Router:         http://localhost:11435
echo 🤖 Ollama API:        http://localhost:11434
echo 📱 Telegram Bot 1:    @Esprieaether_bot
echo 📱 Telegram Bot 2:    @ESPRIEXAETHER_bot
echo.
echo Log files:
echo    data\logs\ai_router.log
echo    data\logs\web_interface.log
echo    data\logs\autonomous_loop.log
echo    data\logs\bot.log
echo    data\logs\bot2.log
echo.
echo To stop services, press Ctrl+C or close this window.
echo.
timeout /t 5 >nul
echo Starting background services in new PowerShell windows...
echo.

REM Start services in separate PowerShell windows
powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd """"$(pwd -replace "&", "^&")""""; .venv\Scripts\activate; python src\ai_router.py'" -WindowStyle Minimized
timeout /t 2 >nul

powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd """"$(pwd -replace "&", "^&")""""; .venv\Scripts\activate; python src\web_interface.py'" -WindowStyle Minimized
timeout /t 2 >nul

powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd """"$(pwd -replace "&", "^&")""""; .venv\Scripts\activate; python src\autonomous_loop.py'" -WindowStyle Minimized
timeout /t 2 >nul

powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd """"$(pwd -replace "&", "^&")""""; .venv\Scripts\activate; python src\bot.py'" -WindowStyle Minimized
timeout /t 2 >nul

powershell -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd """"$(pwd -replace "&", "^&")""""; .venv\Scripts\activate; set BOT_ENV=.env.bot2; python src\bot.py'" -WindowStyle Minimized
timeout /t 2 >nul

echo All services are now running in background windows.
echo Check the individual windows for logs and status.
echo.
echo ============================================

PAUSE
