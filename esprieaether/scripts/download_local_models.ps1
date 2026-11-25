# Téléchargement résilient des 3 cerveaux GGUF locaux (Hugging Face).
# Relance automatique avec reprise (-C -) jusqu'à taille + SHA256 vérifiés.
# Aucun secret, aucun .env modifié, loopback uniquement pour le routeur.

param([int]$Index = -1)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$dir = [IO.Path]::GetFullPath((Join-Path $root '..\models\uncensored-3b'))
$suffix = if ($Index -ge 0) { "_$Index" } else { '' }
$log = Join-Path $root "state\local_brain_download$suffix.log"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $log) | Out-Null

function Write-Log([string]$message) {
    $line = "{0} | {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
    Write-Host $line
}

$models = @(
    @{
        name = 'Dolphin3.0-Llama3.2-3B-Q4_K_M.gguf'
        url  = 'https://huggingface.co/bartowski/Dolphin3.0-Llama3.2-3B-GGUF/resolve/main/Dolphin3.0-Llama3.2-3B-Q4_K_M.gguf'
        size = 2019382400
        sha  = '5d6d02eeefa1ab5dbf23f97afdf5c2c95ad3d946dc3b6e9ab72e6c1637d54177'
    },
    @{
        name = 'Hermes-3-Llama-3.2-3B-Q4_K_M.gguf'
        url  = 'https://huggingface.co/bartowski/Hermes-3-Llama-3.2-3B-GGUF/resolve/main/Hermes-3-Llama-3.2-3B-Q4_K_M.gguf'
        size = 2019374176
        sha  = '2e220a14ba4328fee38cf36c2c068261560f999fadb5725ce5c6d977cb5126b5'
    },
    @{
        name = 'Llama-3.2-3B-Instruct-uncensored-Q4_K_M.gguf'
        url  = 'https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-uncensored-GGUF/resolve/main/Llama-3.2-3B-Instruct-uncensored-Q4_K_M.gguf'
        size = 2241003904
        sha  = '80f532552e3d56e366226f428395de8285a671f2da1d5fd68563741181b77a95'
    }
)

if ($Index -ge 0) {
    if ($Index -ge 3) { throw "Index hors limite : $Index" }
    $models = @($models[$Index])
}

function Get-Size([string]$path) {
    $item = Get-Item -LiteralPath $path -ErrorAction SilentlyContinue
    if ($item) { return $item.Length }
    return 0
}

Write-Log "START dir=$dir index=$Index"

foreach ($model in $models) {
    $path = Join-Path $dir $model.name
    while ($true) {
        $stalled = 0
        while ($true) {
            $before = Get-Size $path
            if ($before -ge $model.size) { break }

            Write-Log ("GET {0} from {1} bytes" -f $model.name, $before)
            # Pas de --retry : curl recommencerait depuis le même offset et
            # perdrait les octets déjà reçus. La boucle PowerShell reprend
            # depuis la taille réelle du fichier après chaque tentative.
            & curl.exe -sSL -C - --max-time 180 --speed-time 30 --speed-limit 1024 -o $path $model.url
            $after = Get-Size $path
            Write-Log ("STEP {0} -> {1} bytes (curl={2})" -f $before, $after, $LASTEXITCODE)

            if ($after -le $before) {
                $stalled++
                if ($stalled -ge 5) {
                    Write-Log ("STALL {0} - pause 30s" -f $model.name)
                    $stalled = 0
                }
                Start-Sleep -Seconds 15
            } else {
                $stalled = 0
            }
        }

        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $model.sha) {
            Write-Log ("BAD_SHA {0} expected={1} actual={2} - restarting file" -f $model.name, $model.sha, $actual)
            Remove-Item -LiteralPath $path -Force
            continue
        }
        Write-Log ("COMPLETE {0} size={1} sha_verified" -f $model.name, $model.size)
        break
    }
}

Write-Log ("ALL_DONE {0}/{0} modèle(s) vérifié(s)" -f $models.Count)
