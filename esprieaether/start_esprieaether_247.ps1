# Point d'entree unique utilise par le raccourci Startup (EsprieAether247.bat / .lnk / SUNNAVOK-KeepAlive.cmd).
# Local uniquement, loopback only, aucun secret, aucun telechargement.
$ErrorActionPreference = 'Continue'

$supervisor = Join-Path $PSScriptRoot 'scripts\keep_alive.ps1'
if (-not (Test-Path $supervisor)) {
    Write-Error "Superviseur introuvable : $supervisor"
    exit 1
}

# Une seule entree Startup, et un seul lancement : le mutex est pris AVANT
# tout lancement de processus. Le superviseur prend ensuite son propre mutex,
# donc même un lancement manuel simultané ne peut pas créer de doublon.
$createdNew = $false
$gate = [System.Threading.Mutex]::new($false, 'SUNNAVOK_STARTUP_GATE', [ref]$createdNew)
if (-not $createdNew) {
    Write-Output 'EsprieAether 24/7: lancement deja en cours.'
    exit 0
}
try {
    Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-WindowStyle', 'Hidden',
        '-File', ('"' + $supervisor + '"')
    ) -WindowStyle Hidden | Out-Null
    Write-Output "EsprieAether 24/7 demarre via $supervisor"
} finally {
    $gate.ReleaseMutex()
    $gate.Dispose()
}
