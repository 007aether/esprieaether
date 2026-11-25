# Wrapper local pour REA (rea-agents 6.10.1) — Node portable, aucun global, aucun secret.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ReaArgs)

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$node = Join-Path $root '.tools\node-v26.13.1\node.exe'
$cli  = Join-Path $root '.tools\rea-agents\node_modules\rea-agents\scripts\rea.mjs'
$jdk  = Join-Path $root '.tools\jdk-25'
$ghidra = Join-Path $root '.tools\ghidra_12.2'

if (Test-Path (Join-Path $jdk 'bin\java.exe')) {
    $env:JAVA_HOME = $jdk
    $env:PATH = (Join-Path $jdk 'bin') + ';' + $env:PATH
}
if (Test-Path (Join-Path $ghidra 'ghidraRun.bat')) { $env:GHIDRA_INSTALL_DIR = $ghidra }

if (-not (Test-Path $node)) { Write-Error "Node portable introuvable: $node"; exit 1 }
if (-not (Test-Path $cli))  { Write-Error "REA introuvable: $cli"; exit 1 }

& $node $cli @ReaArgs
exit $LASTEXITCODE
