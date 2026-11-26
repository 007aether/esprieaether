# ESPRIEATHER — ordonnanceur local quotidien des quatre agents.
# Une passe au plus toutes les 24 h (date-gate dans daily_orchestrator.py).
# GitHub en lecture seule. Aucun commit, push, restart, SMS, appel ni action device.
param([switch]$Once)

$ErrorActionPreference = 'Continue'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$py = Join-Path $root 'esprieaether\.venv\Scripts\python.exe'
$script = Join-Path $root 'esprieaether\src\daily_orchestrator.py'
$log = Join-Path $root 'esprieaether\state\daily_agents.log'
$intervalSeconds = 3600

function Log([string]$message) {
    $line = '{0} | {1}' -f (Get-Date).ToString('s'), $message
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}

$created = $false
$mutex = New-Object System.Threading.Mutex($true, 'SUNNAVOK_DAILY_AGENTS', [ref]$created)
if (-not $created) {
    Log 'SKIP: une autre instance est déjà active'
    exit 0
}

Log 'DEMARRAGE ordonnanceur quotidien local'
try {
    while ($true) {
        Log 'PASSE: verification des quatre agents'
        $output = & $py $script 2>&1 | Out-String
        $code = $LASTEXITCODE
        if ($output.Trim()) { Log $output.Trim() }
        Log ('TERMINEE: exit=' + $code)
        if ($Once) { break }
        Start-Sleep -Seconds $intervalSeconds
    }
} finally {
    Log 'ARRET ordonnanceur quotidien'
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
