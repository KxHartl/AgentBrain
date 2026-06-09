# Setup global AgentBrain Python environment.
# Prefers uv for speed, falls back to pip.

$ErrorActionPreference = "Stop"
$DIR = Split-Path -Parent $PSScriptRoot
$VENV_PATH = Join-Path $DIR ".venv"
$pythonPath = Join-Path $VENV_PATH "Scripts\python.exe"

Write-Host "=== Setup Global AgentBrain Environment ===" -ForegroundColor Cyan

$uvAvailable = [bool](Get-Command uv -ErrorAction SilentlyContinue)

if ($uvAvailable) {
    Write-Host "Using uv (fast mode)."
    if (-not (Test-Path $VENV_PATH)) {
        uv venv $VENV_PATH
    }
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

# --- GPU acceleration (optional, best-effort) --------------------------------
# The base install pulls a CPU build of torch. If a supported accelerator is
# present, swap in a matching GPU build so Docling parsing + embeddings run on
# the GPU (both libraries auto-detect the device). Tiered preference:
#   NVIDIA -> CUDA. Anything else on Windows -> CPU (PyTorch has no transparent
#   backend for non-NVIDIA Windows GPUs). CPU is always the safe final state.
# Same torch/torchvision VERSIONS as the base install -- only the build changes.
function Install-AcceleratedTorch {
    param([string]$Python, [bool]$UseUv)

    $hasNvidia = $false
    if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
        try { & nvidia-smi -L *> $null; if ($LASTEXITCODE -eq 0) { $hasNvidia = $true } } catch { }
    }
    if (-not $hasNvidia) {
        Write-Host "  No NVIDIA GPU detected - keeping CPU torch." -ForegroundColor Yellow
        Write-Host "  (On Windows, PyTorch accelerates transparently only on NVIDIA/CUDA.)"
        return
    }

    $tv = (& $Python -c "import torch;print(torch.__version__.split('+')[0])").Trim()
    $vv = (& $Python -c "import torchvision;print(torchvision.__version__.split('+')[0])").Trim()
    Write-Host "  NVIDIA GPU detected - installing CUDA build of torch $tv / torchvision $vv ..." -ForegroundColor Cyan

    function Invoke-TorchInstall([string]$IndexUrl) {
        try {
            if ($UseUv) {
                uv pip install --python $Python --reinstall "torch==$tv" "torchvision==$vv" --index-url $IndexUrl
            } else {
                & $Python -m pip install --force-reinstall "torch==$tv" "torchvision==$vv" --index-url $IndexUrl
            }
        } catch { }
    }

    foreach ($cu in @("cu128", "cu126", "cu124")) {
        Write-Host "    trying $cu ..."
        Invoke-TorchInstall "https://download.pytorch.org/whl/$cu"
        $cuda = ""
        try { $cuda = (& $Python -c "import torch;print(torch.cuda.is_available())").Trim() } catch { }
        if ($cuda -eq "True") {
            Write-Host "  CUDA enabled - torch sees the GPU." -ForegroundColor Green
            return
        }
    }

    # Every CUDA attempt failed -> guarantee a working CPU build (safe fallback).
    Write-Host "  No matching CUDA wheel - restoring CPU torch." -ForegroundColor Yellow
    Invoke-TorchInstall "https://download.pytorch.org/whl/cpu"
}

Write-Host "Checking for GPU acceleration..."
Install-AcceleratedTorch -Python $pythonPath -UseUv $uvAvailable

Write-Host "Global AgentBrain environment is ready!" -ForegroundColor Green
