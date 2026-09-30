#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python -m backend.cli run --scenario "${1:-safe}" --wait "${@:2}"
