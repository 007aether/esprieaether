# REA read-only PE/ELF/Mach-O hardening scan. No execution, no patching, no network.
param([Parameter(Mandatory = $true)][string]$Path)

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$node = Join-Path $root '.tools\node-v26.13.1\node.exe'
$cli  = Join-Path $root '.tools\rea-agents\node_modules\rea-agents\scripts\rea.mjs'
$jdk  = Join-Path $root '.tools\jdk-25'
$ghidra = Join-Path $root '.tools\ghidra_12.2'
$evidenceDir = Join-Path $root 'state\rea_evidence'

if (Test-Path (Join-Path $jdk 'bin\java.exe')) {
    $env:JAVA_HOME = $jdk
    $env:PATH = (Join-Path $jdk 'bin') + ';' + $env:PATH
}
if (Test-Path (Join-Path $ghidra 'ghidraRun.bat')) { $env:GHIDRA_INSTALL_DIR = $ghidra }

if (-not (Test-Path $node)) { Write-Error "Node portable introuvable: $node"; exit 1 }
if (-not (Test-Path $cli))  { Write-Error "REA introuvable: $cli"; exit 1 }
if (-not (Test-Path $Path -PathType Leaf)) { Write-Error "Cible introuvable: $Path"; exit 1 }

New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
$name = [IO.Path]::GetFileNameWithoutExtension($Path)
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$outFile = Join-Path $evidenceDir "${name}_${stamp}.json"

$raw = & $node $cli inspect-binary-hardening $Path --json 2>&1 | ForEach-Object { $_.ToString() }
if ($LASTEXITCODE -ne 0) {
    $raw | ForEach-Object { Write-Error $_ }
    exit $LASTEXITCODE
}

[IO.File]::WriteAllText($outFile, ($raw -join "`n"), (New-Object Text.UTF8Encoding($false)))
$j = ($raw -join "`n") | ConvertFrom-Json
$img = $j.normalized_result.images[0]
$hardening = ($img.rows | ForEach-Object { "$($_.property)=$($_.state)" }) -join ', '

[PSCustomObject]@{
    target       = $Path
    evidence_id  = $j.evidence_id
    sha256       = $j.subject.identity.sha256
    format       = $j.normalized_result.format
    architecture = $img.architecture
    hardening    = $hardening
    evidence_file = $outFile
} | ConvertTo-Json -Depth 4
