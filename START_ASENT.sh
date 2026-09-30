#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

LOG="/tmp/asent-maryam.log"
PIDFILE="/tmp/asent-maryam.pid"
export PATH="${HOME}/.local/node22/bin:${PATH}"

if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "[ASENT] Already running (PID $(cat "$PIDFILE"))."
  echo "[ASENT] Open: http://127.0.0.1:8000"
  exit 0
fi

echo "[ASENT] Checking local prerequisites..."

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ASENT] ERROR: Python 3 is required." >&2
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "[ASENT] Creating Python virtual environment..."
  python3 -m venv .venv
fi

if [[ ! -f ".asent_python_deps_ready" ]]; then
  echo "[ASENT] Installing Python project dependencies..."
  if [[ -f "requirements.lock.txt" ]]; then
    .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.lock.txt
  elif [[ -f "requirements.txt" ]]; then
    .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
  fi
  touch .asent_python_deps_ready
else
  echo "[ASENT] Python project dependencies already prepared."
fi

if [[ -f "frontend/package-lock.json" ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "[ASENT] ERROR: npm is required. Run INSTALL_AND_START.sh once on this machine." >&2
    exit 1
  fi

  if [[ ! -d "frontend/node_modules" ]]; then
    echo "[ASENT] Installing frontend dependencies..."
    (cd frontend && npm ci --no-audit --no-fund)
  else
    echo "[ASENT] Frontend dependencies already prepared."
  fi
fi

echo "[ASENT] Starting backend..."
nohup .venv/bin/python -m uvicorn backend.main:app \
  --host 127.0.0.1 --port 8000 >"$LOG" 2>&1 &
echo $! > "$PIDFILE"

for _ in {1..30}; do
  if curl -fsS http://127.0.0.1:8000/ >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -fsS http://127.0.0.1:8000/ >/dev/null 2>&1; then
  echo "[ASENT] ERROR: backend did not become ready."
  tail -80 "$LOG" || true
  rm -f "$PIDFILE"
  exit 1
fi

echo "[ASENT] Backend ready at http://127.0.0.1:8000"

if [[ "${ASENT_NO_BROWSER:-0}" == "1" ]]; then
  echo "[ASENT] Browser launch skipped by ASENT_NO_BROWSER=1."
elif command -v firefox >/dev/null 2>&1; then
  nohup firefox --new-window http://127.0.0.1:8000 >/tmp/asent-firefox.log 2>&1 &
else
  echo "[ASENT] Browser not found. Open http://127.0.0.1:8000 manually."
fi

echo "[ASENT] RUNNING"
echo "[ASENT] Stop with: ./STOP_ASENT.sh"
