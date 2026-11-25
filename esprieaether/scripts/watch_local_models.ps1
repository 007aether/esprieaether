# Attend les 3 téléchargements vérifiés (taille + SHA256), puis lance la
# vérification de bout en bout du routeur et de la passerelle. Lecture seule.
param([int]$TimeoutHours = 12)

$root = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $root 'state'
$log = Join-Path $stateDir 'local_brain_watch.log'
$py = Join-Path $root '.venv\Scripts\python.exe'
$verify = Join-Path $root 'scripts\verify_local_brains.py'
$deadline = (Get-Date).AddHours($TimeoutHours)

function Write-Log([string]$message) {
    $line = "{0} | {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
    Write-Host $line
}

Write-Log "WATCH_START deadline=$deadline"

while ((Get-Date) -lt $deadline) {
    $done = 0
    foreach ($i in 0..2) {
        $f = Join-Path $stateDir "local_brain_download_$i.log"
        if ((Test-Path -LiteralPath $f) -and (Select-String -LiteralPath $f -Pattern 'COMPLETE ' -Quiet)) {
            $done++
        }
    }
    if ($done -eq 3) {
        Write-Log 'ALL_3_COMPLETE - verification start'
        & $py $verify 2>&1 | ForEach-Object { Write-Log $_ }
        Write-Log 'VERIFY_DONE'
        exit 0
    }
    Start-Sleep -Seconds 60
}

Write-Log "TIMEOUT after $TimeoutHours h"
exit 1
