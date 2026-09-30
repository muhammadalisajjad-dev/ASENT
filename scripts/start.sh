#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then echo 'Run bash scripts/setup.sh first'; exit 1; fi
exec .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port "${ASENT_PORT:-8000}"
