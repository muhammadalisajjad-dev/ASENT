#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v git >/dev/null || { echo 'Git is required'; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required (3.12 tested)"'
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.lock.txt
if command -v npm >/dev/null; then
  npm --prefix frontend ci
  npm --prefix frontend run build
elif [ ! -f frontend/dist/index.html ]; then
  echo 'Node.js 20+ and npm are required to build the dashboard'; exit 1
else
  echo 'Using the included prebuilt dashboard; Node.js is needed only to edit it.'
fi
.venv/bin/python -m backend.cli --help
printf '\nReady. Run: bash scripts/start.sh\n'
