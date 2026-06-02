#!/bin/bash
# Setup global AgentBrain Python environment

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BRAIN_ROOT="$(dirname "$DIR")"
VENV_PATH="$BRAIN_ROOT/.venv"

echo "=== Setup Global AgentBrain Environment ==="

if [[ ! -d "$VENV_PATH" ]]; then
    echo "Creating virtual environment at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
else
    echo "Virtual environment already exists at $VENV_PATH."
fi

source "$VENV_PATH/bin/activate"

echo "Installing global RAG dependencies..."
pip install --upgrade pip
pip install -q langchain langchain-community chromadb pypdf google-generativeai sentence-transformers

echo "Global AgentBrain environment is ready!"
