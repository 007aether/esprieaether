# SUNNAVOK 24/7 supervisor — local only, no secrets, no network install.
# Restarts only what is down. Singleton via named mutex.
# Ports deliberately NOT in $services (do not supervise, do not kill):
#   :5101  dsh_bridge.py — owned by its own process, /health reports dsh_running=false.
#   :31501/:31502/:31503  children spawned by local-brain :31416 (model workers),
#          they must die/restart with their parent, never be started separately.
# Startup entries (.bat, .lnk, .cmd) all go through start_esprieaether_247.ps1,
# which owns the SUNNAVOK_STARTUP_GATE mutex before spawning this supervisor.
param([switch]$Once)

$ErrorActionPreference = 'Continue'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$base = Join-Path $root 'esprieaether'
$vendor = Join-Path $root 'GITHUB_IMPORT\Atulya-Tantra'
$py   = Join-Path $base '.venv\Scripts\python.exe'
$node = Join-Path $root '.tools\node-v26.13.1\node.exe'
$logDir = Join-Path $base 'state'
$logFile = Join-Path $logDir 'keep_alive.log'
$interval = [int]($env:SUNNAVOK_KEEPALIVE_INTERVAL -as [int])
if ($interval -lt 10) { $interval = 60 }
# Un seul timeout client pour Jarvis et Atulya : aucun appel n'attend 180s ou 900s.
$localTimeout = [int]($env:ESPRIE_LOCAL_TIMEOUT -as [int])
if ($localTimeout -lt 30) { $localTimeout = 120 }
# Une seule voix par défaut : Atulya répond. L'ancien daemon vocal JARVIS reste
# disponible uniquement si le propriétaire le demande explicitement (=1).
$legacyVoice = $env:ESPRIE_LEGACY_VOICE -eq '1'

$createdNew = $false
$mutex = [System.Threading.Mutex]::new($false, 'SUNNAVOK_KEEPALIVE_7X24', [ref]$createdNew)
if (-not $createdNew) { Write-Output 'SUNNAVOK keep-alive is already running.'; exit 0 }

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
if ((Test-Path $logFile) -and ((Get-Item $logFile).Length -gt 1MB)) {
    Copy-Item $logFile ($logFile + '.1') -Force
    Clear-Content $logFile
}

function Log([string]$message) {
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message
    Add-Content -Path $logFile -Value $line -Encoding UTF8
    Write-Output $line
}

function Test-Port([int]$port) {
    $client = [Net.Sockets.TcpClient]::new()
    try {
        $iar = $client.BeginConnect('127.0.0.1', $port, $null, $null)
        if ($iar.AsyncWaitHandle.WaitOne(500)) { $client.EndConnect($iar); return $true }
        return $false
    } catch { return $false } finally { $client.Close() }
}

function Test-Http([int]$port, [string]$path) {
    try {
        $r = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}{1}" -f $port, $path) -UseBasicParsing -TimeoutSec 4
        return [int]$r.StatusCode -lt 500
    } catch { return $false }
}

function Stop-PortOwner([int]$port) {
    $line = netstat -ano | Select-String (":{0}\s+.*LISTENING" -f $port) | Select-Object -First 1
    if (-not $line) { return }
    $owner = ($line.Line -split '\s+')[-1]
    if ($owner -and $owner -ne '0') {
        Stop-Process -Id ([int]$owner) -Force -ErrorAction SilentlyContinue
        Log "STOP owner of :$port (PID $owner) before restart"
        Start-Sleep -Milliseconds 800
    }
}

function Start-Managed([hashtable]$svc) {
    $backup = @{}
    foreach ($key in $svc.Env.Keys) {
        $backup[$key] = [Environment]::GetEnvironmentVariable($key)
        [Environment]::SetEnvironmentVariable($key, [string]$svc.Env[$key])
    }
    try {
        $out = Join-Path $logDir ($svc.Name + '.out.log')
        $err = Join-Path $logDir ($svc.Name + '.err.log')
        Start-Process -FilePath $svc.Exe -ArgumentList @($svc.Args) -WorkingDirectory $svc.Cwd `
            -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err | Out-Null
    } finally {
        foreach ($key in $backup.Keys) {
            [Environment]::SetEnvironmentVariable($key, $backup[$key])
        }
    }
    Log ("START {0} (:{1})" -f $svc.Name, $svc.Port)
}

$services = @(
    @{ Name='flask-web';      Port=5000;  Exe=$py;   Args=@('start_web_server.py'); Cwd=$base },
    @{ Name='gateway';        Port=5001;  Exe=$py;   Args=@('-m','uvicorn','espria_system:app','--host','127.0.0.1','--port','5001'); Cwd=$base },
    @{ Name='cloud-desktop';  Port=5002;  Exe=$py;   Args=@('src\cloud_desktop_agent.py'); Cwd=$base },
    @{ Name='dashboard-node'; Port=5100;  Exe=$node; Args=@('api\server.mjs'); Cwd=$root },
    @{ Name='integrations';   Port=5102;  Exe=$py;   Args=@('src\integrations_adapter.py'); Cwd=$base },
    @{ Name='kanban';         Port=5103;  Exe=$py;   Args=@('src\veritas_kanban.py'); Cwd=$base },
    @{ Name='homedock';       Port=5104;  Exe=$py;   Args=@('src\homedock_dashboard.py'); Cwd=$base },
    # :11435 et :31415 restent malgré le doublon apparent : dépendances réelles
    # (agent_mesh/self_improve/colibri_launcher et espria_system FREELLMAPI_BASE).
    @{ Name='ai-router';      Port=11435; Exe=$py;   Args=@('src\ai_router.py'); Cwd=$base },
    @{ Name='orchestrator';   Port=11436; Exe=$py;   Args=@('src\orchestrator.py'); Cwd=$base },
    @{ Name='agent-mesh';     Port=11437; Exe=$py;   Args=@('src\agent_mesh.py'); Cwd=$base },
    @{ Name='freellmapi';     Port=31415; Exe='C:\Users\aether\Downloads\FreeLLMAPI-0.16.37-win\FreeLLMAPI.exe'; Args=@(); Cwd='C:\Users\aether\Downloads\FreeLLMAPI-0.16.37-win' },
    @{ Name='local-brain';    Port=31416; Exe=$py;   Args=@('-m','src.local_brain'); Cwd=$base },
    @{ Name='atulya';         Port=8501;  Exe=$py;   Args=@('-m','atulya.cli','serve'); Cwd=$root; Env=@{
        PYTHONPATH=$vendor;
        ATULYA_DATA_DIR=(Join-Path $base 'state\atulya');
        ATULYA_MODEL_PROVIDER='openai-compatible';
        ATULYA_MODEL_NAME='dolphin3';
        ATULYA_MODEL_BASE_URL='http://127.0.0.1:31416/v1';
        ATULYA_MODEL_TIMEOUT="$localTimeout";
        ESPRIE_LOCAL_TIMEOUT="$localTimeout";
        ATULYA_FORCE_DARIJA='1';
        ATULYA_LANDING_URL='http://127.0.0.1:3860/jarvis.html';
        HF_HUB_DISABLE_SYMLINKS_WARNING='1'
    } },
    @{ Name='sentinel';       Port=8766;  Exe=$py;   Args=@('scripts\local_sentinel.py'); Cwd=$base; Env=@{ ESPRIE_SENTINEL_PORT='8766' } },
    @{ Name='g0dm0d3-ui';     Port=3860;  Exe=$node; Args=@('scripts\serve_g0dm0d3.mjs'); Cwd=$base },
    @{ Name='g0dm0d3-api';    Port=7860;  Exe=$node; Args=@('node_modules\tsx\dist\cli.mjs','api\server.ts'); Cwd=(Join-Path $base 'G0DM0D3'); Env=@{ PORT='7860'; G0DM0D3_API_HOST='127.0.0.1' } }
)

$httpChecks = @{
    5000 = '/'
    5100 = '/'
    8501 = '/api/health'
    8766 = '/health'
    3860 = '/v1/health'
    7860 = '/v1/health'
}

function Invoke-Pass {
    $up = 0; $down = 0; $fixed = 0
    foreach ($svc in $services) {
        if (-not (Test-Port $svc.Port)) {
            $down++; Start-Managed $svc; $fixed++
            continue
        }
        if ($httpChecks.ContainsKey($svc.Port)) {
            if (-not (Test-Http $svc.Port $httpChecks[$svc.Port])) {
                $down++; Log ("UNHEALTHY {0} (:{1})" -f $svc.Name, $svc.Port)
                Stop-PortOwner $svc.Port
                Start-Managed $svc; $fixed++
                continue
            }
        }
        $up++
    }

    $daemon = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*robot_daemon.py*' }
    if (-not $daemon) {
        Start-Managed @{ Name='robot-daemon'; Port=0; Exe=$py; Args=@('robot_daemon.py','--interval','60'); Cwd=$base }
        $fixed++
    }

    if ($legacyVoice) {
        $voice = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like '*voice_daemon.py*' }
        if (-not $voice) {
            Start-Managed @{ Name='voice-daemon'; Port=0; Exe=$py; Args=@('voice_daemon.py'); Cwd=$base }
            $fixed++
        }
        $voiceState = $(if ($voice) { 'ok' } else { 'started' })
    } else {
        # Un daemon hérité encore vivant produirait un second answer audible : on l'arrête.
        $legacy = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like "*$base*voice_daemon.py*" }
        foreach ($proc in $legacy) { Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue }
        $voiceState = 'atulya-only'
    }

    Log ("PASS up={0} down={1} restarted={2} robots={3} voice={4}" -f $up, $down, $fixed, $(if ($daemon) { 'ok' } else { 'started' }), $voiceState)
}

Log 'SUPERVISOR start (24/7, loopback only, no secrets)'
Invoke-Pass
if ($Once) { Log 'SUPERVISOR once-mode done'; exit 0 }

while ($true) {
    Start-Sleep -Seconds $interval
    try { Invoke-Pass } catch { Log ("ERROR in pass: {0}" -f $_.Exception.Message) }
}
