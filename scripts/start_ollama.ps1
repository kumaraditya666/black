$env:BLACKBOX_AI_PROVIDER = 'ollama'
$env:BLACKBOX_AI_MODEL = 'qwen3.5:4b'
$env:BLACKBOX_OLLAMA_CONTEXT_LENGTH = '2048'
$env:BLACKBOX_OLLAMA_TIMEOUT_SECONDS = '120'
$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { Write-Error 'Create .venv and install requirements first; see README.'; exit 1 }
Push-Location (Join-Path $PSScriptRoot '..')
try { & $python -m uvicorn blackbox.app:app --host 127.0.0.1 --port 8000 }
finally { Pop-Location }
