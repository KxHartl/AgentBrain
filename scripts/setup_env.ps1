# Setup global AgentBrain Python environment.
# Prefers uv for speed, falls back to pip.

$ErrorActionPreference = "Stop"
$DIR = Split-Path -Parent $PSScriptRoot
$VENV_PATH = Join-Path $DIR ".venv"

Write-Host "=== Setup Global AgentBrain Environment ===" -ForegroundColor Cyan

$uvAvailable = Get-Command uv -ErrorAction SilentlyContinue

if ($uvAvailable) {
    Write-Host "Using uv (fast mode)."
    if (-not (Test-Path $VENV_PATH)) {
        uv venv $VENV_PATH
    }
    $pythonPath = Join-Path $VENV_PATH "Scripts\python.exe"
    uv pip install --python $pythonPath --upgrade pip
    uv pip install --python $pythonPath -q `
        python-dotenv `
        docling `
        lancedb `
        pypdf `
        sentence-transformers `
        google-generativeai
} else {
    Write-Host "uv not found, using pip. Consider installing uv for faster setup."
    if (-not (Test-Path $VENV_PATH)) {
        python -m venv $VENV_PATH
    }
    $pipCmd = Join-Path $VENV_PATH "Scripts\pip.exe"
    & $pipCmd install --upgrade pip
    & $pipCmd install -q `
        python-dotenv `
        docling `
        lancedb `
        pypdf `
        sentence-transformers `
        google-generativeai
}

Write-Host "Global AgentBrain environment is ready!" -ForegroundColor Green
