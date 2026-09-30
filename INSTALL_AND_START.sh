#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/node22/bin:${PATH}"

echo "===== ASENT MARYAM ONE-TIME SETUP ====="

# Python
if ! command -v python3 >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    echo "[SETUP] Installing Python 3..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip curl
  else
    echo "[SETUP] ERROR: python3 is missing and sudo is unavailable." >&2
    exit 1
  fi
fi

# Node/npm: prefer an already prepared per-user Node 22 bundle.
if ! command -v node >/dev/null 2>&1 || ! node --version | grep -q '^v22\.'; then
  if [[ -x "${HOME}/.local/node22/bin/node" ]]; then
    export PATH="${HOME}/.local/node22/bin:${PATH}"
  else
    echo "[SETUP] Node 22 is missing."
    echo "[SETUP] Put a Linux x64 Node 22 tarball beside this script as node22-linux-x64.tar.xz"
    echo "[SETUP] and re-run, or install Node 22 once through your normal package method."
    exit 1
  fi
fi

echo "[SETUP] Node: $(node --version)"
echo "[SETUP] npm:  $(npm --version)"
echo "[SETUP] Python: $(python3 --version)"

# Python environment
if [[ ! -x ".venv/bin/python" ]]; then
  python3 -m venv .venv
fi

if [[ -f "requirements.lock.txt" ]]; then
  .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.lock.txt
elif [[ -f "requirements.txt" ]]; then
  .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
fi

# Frontend dependencies
if [[ -f "frontend/package-lock.json" ]]; then
  (cd frontend && npm ci --no-audit --no-fund)
fi

echo
echo "[SETUP] Complete."
echo "[SETUP] Start: ./START_ASENT.sh"
