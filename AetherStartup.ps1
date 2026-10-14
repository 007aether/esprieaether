# AetherStartup — launch all EsprieAether services at login (24/7)
# Runs: ollama check + router + web + homedock + sunna + integrations + kanban + bot + jarvis + watchdog

$ErrorActionPreference = "SilentlyContinue"
$env:PATH = "$HOME\.local\bin;$env:PATH"
$env:OLLAMA_MODELS = "C:\Users\ESPRIEAETHER\.ollama\models"

$repo = "C:\Users\ESPRIEAETHER\Desktop\esprieaether"
$py = "$repo\.venv\Scripts\python.exe"
$jarvis = "$env:LOCALAPPDATA\Temp\JARVIS_repo\backend\.venv\Scripts\python.exe"

# ollama (if installed, not running)
$ollama = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollama) { Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden }

Start-Sleep -Seconds 3

# services (each in hidden window, survive until logoff)
$svcs = @(
  @{ n="router";       c="$py src/ai_router.py" },
  @{ n="web";          c="$py src/web_interface.py" },
  @{ n="homedock";     c="$py src/homedock_dashboard.py" },
  @{ n="sunna";        c="$py src/sunna_api.py" },
  @{ n="integrations"; c="$py src/integrations_adapter.py" },
  @{ n="kanban";       c="$py src/veritas_kanban.py" },
  @{ n="bot";          c="$py src/bot.py" },
  @{ n="watchdog";     c="$py src/watchdog.py" },
  @{ n="autonomous";   c="$py src/autonomous_loop.py" }
)
foreach ($s in $svcs) {
  Start-Process -FilePath "powershell" -ArgumentList "-NoProfile","-WindowStyle","Hidden","-Command","Set-Location '$repo'; & $($s.c)" -WindowStyle Hidden
}

# JARVIS (separate venv)
if (Test-Path $jarvis) {
  Start-Process -FilePath "powershell" -ArgumentList "-NoProfile","-WindowStyle","Hidden","-Command","Set-Location '$env:LOCALAPPDATA\Temp\JARVIS_repo\backend'; & '$jarvis' -m uvicorn main:app --host 0.0.0.0 --port 8000" -WindowStyle Hidden
}

# log
$log = "$env:LOCALAPPDATA\Temp\aether_startup.log"
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') — AetherStartup launched $($svcs.Count) services + jarvis" | Out-File $log -Append
