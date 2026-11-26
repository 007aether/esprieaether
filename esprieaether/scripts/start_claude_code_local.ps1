param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ClaudeArgs
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$keyFile = Join-Path $root 'state\freellmapi.key'
$configDir = Join-Path $root 'state\claude_code_config'
$cli = Join-Path $env:LOCALAPPDATA 'Claude-3p\claude-code\2.1.330\9424831ad51c\claude.exe'

if (-not (Test-Path $cli)) {
    throw 'Claude Code CLI introuvable (LOCALAPPDATA\Claude-3p\claude-code).'
}
if (-not (Test-Path $keyFile)) {
    throw 'Clé FreeLLMAPI locale absente : aucune valeur n est écrite dans ce script.'
}

# La clé est lue à l exécution et reste uniquement dans l environnement du processus.
$key = (Get-Content $keyFile -Raw).Trim()
if (-not $key) {
    throw 'Clé FreeLLMAPI locale vide.'
}

$env:ANTHROPIC_BASE_URL = 'http://127.0.0.1:3860/freellm'
$env:ANTHROPIC_AUTH_TOKEN = $key
$env:CLAUDE_CONFIG_DIR = $configDir
$env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = '1'
$env:CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY = '0'
$env:DISABLE_TELEMETRY = '1'
$env:DO_NOT_TRACK = '1'

if (-not $ClaudeArgs -or $ClaudeArgs.Count -eq 0) {
    $ClaudeArgs = @('-p', '--model', 'claude-sonnet-4-5', '--max-turns', '1', '--no-session-persistence')
}

& $cli @ClaudeArgs
