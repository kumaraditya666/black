param(
    [int]$Port = 8200,
    [string]$Database = '',
    [switch]$NoAi
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $Database) { $Database = Join-Path $root 'data\cloud.db' }
$dbDirectory = Split-Path -Parent $Database
if ($dbDirectory -and -not (Test-Path -LiteralPath $dbDirectory)) {
    New-Item -ItemType Directory -Path $dbDirectory -Force | Out-Null
}

$env:BLACKBOX_CLOUD_DB = $Database
if (-not $NoAi) {
    if (-not $env:BLACKBOX_AI_PROVIDER) { $env:BLACKBOX_AI_PROVIDER = 'ollama' }
    if (-not $env:BLACKBOX_AI_MODEL) { $env:BLACKBOX_AI_MODEL = 'qwen3.5:4b' }
    if (-not $env:BLACKBOX_OLLAMA_CONTEXT_LENGTH) { $env:BLACKBOX_OLLAMA_CONTEXT_LENGTH = '2048' }
    if (-not $env:BLACKBOX_OLLAMA_TIMEOUT_SECONDS) { $env:BLACKBOX_OLLAMA_TIMEOUT_SECONDS = '120' }
}

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error 'Create .venv and install requirements first; see README.'
    exit 1
}

Write-Host "BLACKBOX Cloud: http://127.0.0.1:$Port"
Write-Host "Database: $Database"
Write-Host 'Local prototype only. Do not expose this port publicly.'

Push-Location $root
try {
    & $python -m uvicorn blackbox.cloud:app --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
