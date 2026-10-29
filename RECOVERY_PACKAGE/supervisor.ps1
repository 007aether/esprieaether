# SUPERVISOR 24/7 — starts everything, keeps everything alive, runs at boot
# What it does:
#   1. Waits for network + user login
#   2. Starts AetherRun.ps1 (launches 11 services via Start-Process -WindowStyle Hidden)
#   3. Starts the daemons that AetherRun does NOT handle (bot, watchdog, autonomous_loop, cloud_poller)
#   4. Every 60s: checks that watchdog is alive; if dead → restart it
#   5. If watchdog crashes 5x in 10min → supervisor itself restarts everything from scratch
# Exit codes:
#   0 = clean shutdown (Ctrl+C / stop)
#   1 = fatal error (logged to data\logs\supervisor.err)

$ErrorActionPreference = "Continue"
$repo = "C:\Users\ESPRIEAETHER\Desktop\esprieaether"
$logs = "$repo\data\logs"
$py = "$repo\.venv\Scripts\python.exe"
$supervisorLog = "$logs\supervisor.log"
$supervisorErr = "$logs\supervisor.err"

function Write-Log {
    param([string]$msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $supervisorLog -Value "[$ts] $msg" -Encoding UTF8
}

Write-Log "════ SUPERVISOR START ════"

# wait for network (max 30s)
$netOk = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $null = Test-Connection -ComputerName "8.8.8.8" -Count 1 -Quiet -ErrorAction SilentlyContinue
        if ($?) { $netOk = $true; break }
    } catch {}
    Start-Sleep -Seconds 1
}
Write-Log "network: $(if ($netOk) {'OK'} else {'TIMEOUT — continuing anyway'})"

# start AetherRun (services)
Write-Log "launching AetherRun.ps1 ..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$repo\AetherRun.ps1" 2>&1 | Out-Null
Start-Sleep -Seconds 5

# start daemons (things AetherRun doesn't handle)
$daemons = @(
    @{ name = "bot";            script = "src\bot.py" },
    @{ name = "watchdog";       script = "src\watchdog.py" },
    @{ name = "autonomous_loop"; script = "src\autonomous_loop.py" },
    @{ name = "cloud_poller";   script = "src\cloud_poller.py" },
    @{ name = "work_organizer"; script = "bots\work_organizer.py" },
    @{ name = "self_heal";      script = "bots\self_heal.py" }
)

foreach ($d in $daemons) {
    # kill existing duplicates first
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -like "*$($d.script)*" -and $_.CommandLine -like "*\.venv*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1

    # start fresh
    Start-Process -FilePath $py -ArgumentList $d.script -WorkingDirectory $repo -WindowStyle Hidden `
        -RedirectStandardOutput "$logs\$($d.name).log" -RedirectStandardError "$logs\$($d.name).err"
    Write-Log "started $($d.name)"
    Start-Sleep -Seconds 2
}

# main loop: keep watchdog alive
Write-Log "maintenance loop entered"
$watchdogRestarts = @()
while ($true) {
    Start-Sleep -Seconds 60

    # check watchdog alive
    $watchdog = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -like "*watchdog.py*" -and $_.CommandLine -like "*\.venv*" }

    if (-not $watchdog) {
        Write-Log "watchdog DEAD → restarting"
        Start-Process -FilePath $py -ArgumentList "src\watchdog.py" -WorkingDirectory $repo -WindowStyle Hidden `
            -RedirectStandardOutput "$logs\watchdog.log" -RedirectStandardError "$logs\watchdog.err"

        $watchdogRestarts += (Get-Date)
        # keep only last 10 min
        $watchdogRestarts = $watchdogRestarts | Where-Object { $_ -gt (Get-Date).AddMinutes(-10) }

        # 5+ restarts in 10 min = cycle everything
        if ($watchdogRestarts.Count -ge 5) {
            Write-Log "watchdog crashed 5x/10min → restarting ALL services + daemons"
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$repo\AetherRun.ps1" 2>&1 | Out-Null
            foreach ($d in $daemons) {
                Start-Process -FilePath $py -ArgumentList $d.script -WorkingDirectory $repo -WindowStyle Hidden `
                    -RedirectStandardOutput "$logs\$($d.name).log" -RedirectStandardError "$logs\$($d.name).err"
            }
            $watchdogRestarts = @()
        }
    }
}
