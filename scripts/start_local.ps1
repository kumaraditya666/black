param(
    [string]$Repo = '',
    [string]$Database = '',
    [int]$Port = 8000,
    [switch]$NoAi
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $Repo) { $Repo = $root }
if (-not $Database) { $Database = Join-Path $root 'data\blackbox-local.db' }

$repoPath = (Resolve-Path -LiteralPath $Repo).Path
$dbDirectory = Split-Path -Parent $Database
if ($dbDirectory -and -not (Test-Path -LiteralPath $dbDirectory)) {
    New-Item -ItemType Directory -Path $dbDirectory -Force | Out-Null
}

$env:BLACKBOX_REPO = $repoPath
$env:BLACKBOX_DB = $Database
if (-not $NoAi) {
    $env:BLACKBOX_AI_PROVIDER = 'ollama'
    $env:BLACKBOX_AI_MODEL = 'qwen3.5:4b'
    $env:BLACKBOX_OLLAMA_CONTEXT_LENGTH = '2048'
    $env:BLACKBOX_OLLAMA_TIMEOUT_SECONDS = '120'
}

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error 'Create .venv and install requirements first; see README.'
    exit 1
}

Write-Host "BLACKBOX API: http://127.0.0.1:$Port"
Write-Host "Monitored repository: $repoPath"
Write-Host "Database: $Database"
if (-not $NoAi) { Write-Host 'AI provider: local Ollama / qwen3.5:4b' }

Push-Location $root
try {
    & $python -m uvicorn blackbox.app:app --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
