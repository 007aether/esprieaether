# AetherStartup 2.0 — launch all EsprieAether services at login (24/7)
# Runs: ollama + router + web + homedock + sunna + integrations + kanban + bot + jarvis + watchdog
# Supported: PowerShell 5.1+ (Windows). Run as administrator to allow hidden windows.

$ErrorActionPreference = "SilentlyContinue"
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
$env:OLLAMA_MODELS = "C:\Users\ESPRIEAETHER\.ollama\models"

$repo = "C:\Users\ESPRIEAETHER\Desktop\esprieaether"
$py  = "$repo\.venv\Scripts\python.exe"
$jarvis = "C:\Users\ESPRIEAETHER\AppData\Local\Temp\JARVIS_repo\backend\.venv\Scripts\python.exe"

# ollama (if installed and not already running)
$ollama = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
}
Start-Sleep -Seconds 3

# Helper: launch a service silently
function Start-Service {
    param([string]$Name, [string]$Command)
    if (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$Command*" }) {
        Write-Host "[skip] $Name already running"
        return
    }
    Write-Host "[start] $Name"
    Start-Process -FilePath "powershell" -ArgumentList "-NoProfile","-WindowStyle","Hidden","-Command","Set-Location '$repo'; & '$py' $Command" -WindowStyle Hidden
    Start-Sleep -Milliseconds 300
}

# services list
$svcs = @(
    @{ n="router";       c="src/ai_router.py" },
    @{ n="web";          c="src/web_interface.py" },
    @{ n="homedock";     c="src/homedock_dashboard.py" },
    @{ n="sunna";        c="src/sunna_api.py" },
    @{ n="integrations"; c="src/integrations_adapter.py" },
    @{ n="kanban";       c="src/veritas_kanban.py" },
    @{ n="bot";          c="src/bot.py" },
    @{ n="watchdog";     c="src/watchdog.py" },
    @{ n="autonomous";   c="src/autonomous_loop.py" },
    @{ n="vpn-daemon";   c="src/vpn_agent.py --daemon" }
)
foreach ($s in $svcs) { Start-Service -Name $s.n -Command $s.c }

# JARVIS (separate venv)
if (Test-Path $jarvis) {
    if (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*src/ai_router.py*" -or $_.CommandLine -like "*main:app*" }) {
        Write-Host "[skip] JARVIS already running"
    } else {
        Write-Host "[start] JARVIS"
        Start-Process -FilePath "powershell" -ArgumentList "-NoProfile","-WindowStyle","Hidden","-Command","Set-Location '$repo'; & '$jarvis' -m uvicorn main:app --host 0.0.0.0 --port 8000" -WindowStyle Hidden
    }
}

# log
$log = "$env:USERPROFILE\AppData\Local\Temp\aether_startup.log"
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') — AetherStartup launched $(($svcs.Count+1)) services + jarvis" | Out-File $log -Append
Write-Host "[done] AetherStartup (all services + JARVIS)"
