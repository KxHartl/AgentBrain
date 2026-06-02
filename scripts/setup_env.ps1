# Setup global AgentBrain Python environment

$ErrorActionPreference = "Stop"
$DIR = Split-Path -Parent $PSScriptRoot
$VENV_PATH = Join-Path $DIR ".venv"

Write-Host "=== Setup Global AgentBrain Environment ===" -ForegroundColor Cyan

if (-not (Test-Path $VENV_PATH)) {
    Write-Host "Creating virtual environment at $VENV_PATH..."
    python -m venv $VENV_PATH
} else {
    Write-Host "Virtual environment already exists at $VENV_PATH."
}

$pipCmd = Join-Path $VENV_PATH "Scripts\pip.exe"

Write-Host "Installing global RAG dependencies..."
& $pipCmd install --upgrade pip
& $pipCmd install -q langchain langchain-community chromadb pypdf google-generativeai sentence-transformers

Write-Host "Global AgentBrain environment is ready!" -ForegroundColor Green
