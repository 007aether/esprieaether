# AetherRun — launch all EsprieAether services DETACHED (survive session/logoff)
# Each service = own hidden python process, output -> log file. Idempotent.
# Replaces AetherStartup.ps1 (which used nested powershell wrappers).

$ErrorActionPreference = "SilentlyContinue"
$env:PATH = "C:\Users\ESPRIEAETHER\.local\bin;$env:PATH"
$env:OLLAMA_MODELS = "C:\Users\ESPRIEAETHER\.ollama\models"

$repo = "C:\Users\ESPRIEAETHER\Desktop\esprieaether"
$py = "$repo\.venv\Scripts\python.exe"
$jpy = "$env:LOCALAPPDATA\Temp\JARVIS_repo\backend\.venv\Scripts\python.exe"
$logs = "C:\Users\ESPRIEAETHER\ESPRIEAETHER\data\logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

# ollama (native exe — keep running)
if (-not (Get-Process ollama -ErrorAction SilentlyContinue)) {
  Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
}
Start-Sleep -Seconds 3

# services: name -> script (colon-separated)
$svcs = @(
  "router:src/ai_router.py",
  "web:src/web_interface.py",
  "cloud-desktop:src/cloud_desktop_agent.py",
  "homedock:src/homedock_dashboard.py",
  "sunna:src/sunna_api.py",
  "integrations:src/integrations_adapter.py",
  "kanban:src/veritas_kanban.py",
  "bot:src/bot.py",
  "watchdog:src/watchdog.py",
  "autonomous:src/autonomous_loop.py",
  "vpn-daemon:src/vpn_agent.py --daemon"
)

foreach ($svc in $svcs) {
  $n = $svc.Split(":")[0]
  $s = $svc.Substring($n.Length + 1)
  # kill existing instance (idempotent restart)
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*$s*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  # launch detached via cmd start /b (survives PowerShell exit)
  cmd /c "start /b cmd /c `"$py $s > $logs\$n.log 2>&1`""
}

Start-Sleep -Seconds 20

# governor-edr (different working dir)
$govDir = "$env:LOCALAPPDATA\Temp\new_repos\governor-edr"
if (Test-Path "$govDir\main.py") {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*governor*main*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  cmd /c "start /b cmd /c `"cd /d $govDir && $py main.py > $logs\governor.log 2>&1`""
}

# JARVIS Next.js frontend (node, port 3000)
$frontendDir = "$env:LOCALAPPDATA\Temp\JARVIS_repo\frontend"
if (Test-Path "$frontendDir\package.json") {
  Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
    Where-Object { $_.CommandLine -like "*next dev*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  cmd /c "start /b cmd /c `"cd /d $frontendDir && npx next dev --port 3000 > $logs\jarvis-fe.log 2>&1`""
}

# JARVIS backend (uvicorn, port 8000)
if (Test-Path $jpy) {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*uvicorn main:app*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  cmd /c "start /b cmd /c `"cd /d $env:LOCALAPPDATA\Temp\JARVIS_repo\backend && $jpy -m uvicorn main:app --host 0.0.0.0 --port 8000 > $logs\jarvis.log 2>&1`""
}

Start-Sleep -Seconds 20

# verify + report
$report = @()
$ports = [ordered]@{ "router"=11435; "web"=5000; "cloud-desktop"=5001; "sunna"=5100; "integrations"=5102; "kanban"=5103; "homedock"=5104; "jarvis"=8000 }
foreach ($n in $ports.Keys) {
  $code = "DOWN"
  foreach ($ep in @("/health", "/api/health", "/")) {
    try {
      $r = Invoke-WebRequest -Uri "http://127.0.0.1:$($ports[$n])$ep" -TimeoutSec 5 -UseBasicParsing
      $code = "$($r.StatusCode)"; break
    } catch {}
  }
  $report += "$n : $code"
}
$report += "ollama : $(if (Get-Process ollama -ErrorAction SilentlyContinue) {'UP'} else {'DOWN'})"
$report | Out-File "$logs\startup_report.txt"
$report
