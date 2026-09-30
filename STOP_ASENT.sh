#!/usr/bin/env bash
set -euo pipefail

PIDFILE="/tmp/asent-maryam.pid"
LOG="/tmp/asent-maryam.log"

if [[ -f "$PIDFILE" ]]; then
  PID="$(cat "$PIDFILE" || true)"
  if [[ -n "${PID:-}" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "[ASENT] Stopping backend PID $PID..."
    kill "$PID" 2>/dev/null || true
    for _ in {1..10}; do
      kill -0 "$PID" 2>/dev/null || break
      sleep 0.5
    done
    kill -9 "$PID" 2>/dev/null || true
  fi
  rm -f "$PIDFILE"
else
  echo "[ASENT] No recorded backend PID."
fi

# Clean up only this POC's known port owner if still present.
if command -v fuser >/dev/null 2>&1; then
  fuser -k 8000/tcp 2>/dev/null || true
fi

echo "[ASENT] Stopped."
echo "[ASENT] Log: $LOG"
