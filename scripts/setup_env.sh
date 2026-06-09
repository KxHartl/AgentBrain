#!/bin/bash
# Setup global AgentBrain Python environment.
# Prefers uv for speed, falls back to pip.

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BRAIN_ROOT="$(dirname "$DIR")"
VENV_PATH="$BRAIN_ROOT/.venv"

echo "=== Setup Global AgentBrain Environment ==="

USE_UV=0
if command -v uv &>/dev/null; then USE_UV=1; fi

# Create venv + install base deps (pulls a CPU/default build of torch)
if [[ "$USE_UV" -eq 1 ]]; then
    echo "Using uv (fast mode)."
    if [[ ! -d "$VENV_PATH" ]]; then
        uv venv "$VENV_PATH"
    fi
    PYBIN="$VENV_PATH/bin/python"
    uv pip install --python "$PYBIN" --upgrade pip
    uv pip install --python "$PYBIN" -q \
        python-dotenv \
        docling \
        lancedb \
        pypdf \
        sentence-transformers \
        google-generativeai
else
    echo "uv not found, using pip. Consider installing uv for faster setup."
    if [[ ! -d "$VENV_PATH" ]]; then
        python3 -m venv "$VENV_PATH"
    fi
    PYBIN="$VENV_PATH/bin/python"
    "$PYBIN" -m pip install --upgrade pip
    "$PYBIN" -m pip install -q \
        python-dotenv \
        docling \
        lancedb \
        pypdf \
        sentence-transformers \
        google-generativeai
fi

# --- GPU acceleration (optional, best-effort) --------------------------------
# Swap the CPU torch for a matching GPU build when a supported accelerator is
# present, so Docling parsing + embeddings run on the GPU (both auto-detect it).
# Tiered preference: NVIDIA->CUDA, AMD on Linux->ROCm, Apple Silicon->MPS (the
# default wheel already has it). Anything else -> CPU (the safe final state).
# Only the torch/torchvision BUILD changes; the versions stay as base-installed.
install_accel_torch() {
    OS="$(uname -s)"
    TV="$("$PYBIN" -c 'import torch;print(torch.__version__.split("+")[0])' 2>/dev/null || true)"
    VV="$("$PYBIN" -c 'import torchvision;print(torchvision.__version__.split("+")[0])' 2>/dev/null || true)"

    reinstall() {  # $1 = index url
        if [[ "$USE_UV" -eq 1 ]]; then
            uv pip install --python "$PYBIN" --reinstall "torch==$TV" "torchvision==$VV" --index-url "$1"
        else
            "$PYBIN" -m pip install --force-reinstall "torch==$TV" "torchvision==$VV" --index-url "$1"
        fi
    }
    torch_sees_gpu() {  # CUDA build reports True for both CUDA and ROCm
        [[ "$("$PYBIN" -c 'import torch;print(torch.cuda.is_available())' 2>/dev/null)" == "True" ]]
    }

    if command -v nvidia-smi &>/dev/null && nvidia-smi -L &>/dev/null; then
        echo "  NVIDIA GPU detected - installing CUDA build of torch $TV ..."
        for cu in cu128 cu126 cu124; do
            echo "    trying $cu ..."
            reinstall "https://download.pytorch.org/whl/$cu" || true
            if torch_sees_gpu; then echo "  CUDA enabled - torch sees the GPU."; return; fi
        done
        echo "  No matching CUDA wheel - restoring CPU torch."
        reinstall "https://download.pytorch.org/whl/cpu" || true
    elif [[ "$OS" == "Linux" ]] && command -v rocminfo &>/dev/null; then
        echo "  AMD ROCm GPU detected - installing ROCm build of torch $TV ..."
        for rc in rocm6.3 rocm6.2 rocm6.1; do
            echo "    trying $rc ..."
            reinstall "https://download.pytorch.org/whl/$rc" || true
            if torch_sees_gpu; then echo "  ROCm enabled - torch sees the GPU."; return; fi
        done
        echo "  No matching ROCm wheel - restoring CPU torch."
        reinstall "https://download.pytorch.org/whl/cpu" || true
    elif [[ "$OS" == "Darwin" ]]; then
        if [[ "$("$PYBIN" -c 'import torch;print(bool(getattr(torch.backends,"mps",None) and torch.backends.mps.is_available()))' 2>/dev/null)" == "True" ]]; then
            echo "  Apple MPS acceleration available (default wheel) - nothing to install."
        else
            echo "  No MPS - using CPU torch."
        fi
    else
        echo "  No supported GPU - using CPU torch."
    fi
}

echo "Checking for GPU acceleration..."
install_accel_torch

echo "Global AgentBrain environment is ready!"
