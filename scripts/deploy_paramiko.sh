#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
test -d .venv || python3 -m venv .venv
.venv/bin/pip install -q paramiko
exec .venv/bin/python scripts/deploy_paramiko.py
