#!/bin/bash
# Setup global AgentBrain Python environment.
# Prefers uv for speed, falls back to pip.

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BRAIN_ROOT="$(dirname "$DIR")"
VENV_PATH="$BRAIN_ROOT/.venv"

echo "=== Setup Global AgentBrain Environment ==="

# Create venv
if command -v uv &>/dev/null; then
    echo "Using uv (fast mode)."
    if [[ ! -d "$VENV_PATH" ]]; then
        uv venv "$VENV_PATH"
    fi
    uv pip install --python "$VENV_PATH/bin/python" --upgrade pip
    uv pip install --python "$VENV_PATH/bin/python" -q \
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
    source "$VENV_PATH/bin/activate"
    pip install --upgrade pip
    pip install -q \
        python-dotenv \
        docling \
        lancedb \
        pypdf \
        sentence-transformers \
        google-generativeai
fi

echo "Global AgentBrain environment is ready!"
