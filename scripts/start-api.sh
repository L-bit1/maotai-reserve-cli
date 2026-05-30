#!/bin/bash
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
if [ -d "$ROOT/.venv" ]; then
  source "$ROOT/.venv/bin/activate"
fi
pip install -q -r backend/requirements.txt -r requirements.txt 2>/dev/null
cd "$ROOT"
export PYTHONPATH="$ROOT"
python backend/run.py
