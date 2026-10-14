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

# services: name -> script (+ optional args)
$svcs = @(
  @{ n="router";        s="src/ai_router.py" },
  @{ n="web";           s="src/web_interface.py" },
  @{ n="cloud-desktop"; s="src/cloud_desktop_agent.py" },
  @{ n="homedock";      s="src/homedock_dashboard.py" },
  @{ n="sunna";         s="src/sunna_api.py" },
  @{ n="integrations";  s="src/integrations_adapter.py" },
  @{ n="kanban";        s="src/veritas_kanban.py" },
  @{ n="bot";           s="src/bot.py" },
  @{ n="watchdog";      s="src/watchdog.py" },
  @{ n="autonomous";    s="src/autonomous_loop.py" },
  @{ n="vpn-daemon";    s="src/vpn_agent.py"; a="--daemon" },
  @{ n="governor-edr";  s="main.py"; a=""; d="$env:LOCALAPPDATA\Temp\new_repos\governor-edr" }
)

# JARVIS Next.js frontend (node, port 3000) — separate launch
$frontendDir = "$env:LOCALAPPDATA\Temp\JARVIS_repo\frontend"
if (Test-Path "$frontendDir\package.json") {
  Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
    Where-Object { $_.CommandLine -like "*next dev*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Process -FilePath "cmd.exe" -ArgumentList "/c","npx next dev --port 3000" `
    -WorkingDirectory $frontendDir -WindowStyle Hidden `
    -RedirectStandardOutput "$logs\jarvis-frontend.log" -RedirectStandardError "$logs\jarvis-frontend.err"
}

foreach ($s in $svcs) {
  # kill existing instance of this script (idempotent restart)
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*$($s.s)*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  # start detached: python directly, hidden, log to file
  $args = @($s.s)
  if ($s.a) { $args += $s.a }
  $wd = if ($s.d) { $s.d } else { $repo }
  Start-Process -FilePath $py -ArgumentList $args -WorkingDirectory $wd `
    -WindowStyle Hidden -RedirectStandardOutput "$logs\$($s.n).log" `
    -RedirectStandardError "$logs\$($s.n).err"
}

# JARVIS (separate venv, port 8000)
if (Test-Path $jpy) {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*uvicorn main:app*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Process -FilePath $jpy -ArgumentList "-m","uvicorn","main:app","--host","0.0.0.0","--port","8000" `
    -WorkingDirectory "$env:LOCALAPPDATA\Temp\JARVIS_repo\backend" -WindowStyle Hidden `
    -RedirectStandardOutput "$logs\jarvis.log" -RedirectStandardError "$logs\jarvis.err"
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
