#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
Usage:
  ./RECORD_DEMO.sh [--mode full|cavr|satra|sable|integrated]
  ./RECORD_DEMO.sh --smoke [secs]  Launch ASENT in Firefox and record a short MP4
EOF
}

MODE=full
SMOKE_SECONDS=12
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then usage; exit 0; fi
if [[ "${1:-}" == "--mode" ]]; then
  MODE="${2:-}"
  [[ $# -eq 2 ]] || { echo "[RECORD] ERROR: --mode takes exactly one mode." >&2; usage >&2; exit 2; }
  [[ "$MODE" =~ ^(full|cavr|satra|sable|integrated)$ ]] || { echo "[RECORD] ERROR: unsupported replay mode: ${MODE:-missing}" >&2; usage >&2; exit 2; }
elif [[ "${1:-}" == "--smoke" ]]; then
  MODE=smoke
  SMOKE_SECONDS="${2:-12}"
  [[ "$SMOKE_SECONDS" =~ ^[1-9][0-9]*$ ]] || { echo "[RECORD] ERROR: smoke duration must be a positive integer." >&2; exit 2; }
elif (($#)); then
  echo "[RECORD] ERROR: unknown argument: $1" >&2
  usage >&2
  exit 2
fi

BASE_URL="http://127.0.0.1:8000"
OUT_DIR="$ROOT/recordings"
STAMP="$(date +%Y%m%d_%H%M%S)"
if [[ "$MODE" == smoke ]]; then
  mkdir -p "$OUT_DIR"
  OUT="$OUT_DIR/ASENT_Maryam_Smoke_${STAMP}.mp4"
  HELPER_MODE=full
else
  ASSET_DIR="$ROOT/frontend/public/defense-replays"
  mkdir -p "$ASSET_DIR"
  OUT="$ASSET_DIR/.${MODE}_${STAMP}.partial.mp4"
  case "$MODE" in full) HELPER_MODE=full;; cavr) HELPER_MODE=cavr;; satra) HELPER_MODE=satra;; sable) HELPER_MODE=sable;; integrated) HELPER_MODE=integrated;; esac
fi
PIDFILE="/tmp/asent-maryam.pid"
LOG="/tmp/asent-maryam.log"
BACKEND_STARTED=0
ASSET_PUBLISHED=0
CAPTURE_PID=""
BROWSER_HELPER_PID=""

cleanup() {
  local status=$?
  trap - EXIT INT TERM
  if [[ -n "$BROWSER_HELPER_PID" ]] && kill -0 "$BROWSER_HELPER_PID" 2>/dev/null; then
    kill -TERM "$BROWSER_HELPER_PID" 2>/dev/null || true
    wait "$BROWSER_HELPER_PID" 2>/dev/null || true
  fi
  if [[ -n "$CAPTURE_PID" ]] && kill -0 "$CAPTURE_PID" 2>/dev/null; then
    kill -INT "$CAPTURE_PID" 2>/dev/null || true
    wait "$CAPTURE_PID" 2>/dev/null || true
  fi
  if (( BACKEND_STARTED )) && [[ -f "$PIDFILE" ]]; then
    local pid
    pid="$(cat "$PIDFILE" 2>/dev/null || true)"
    if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      for _ in {1..10}; do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PIDFILE"
  fi
  if (( status != 0 && !ASSET_PUBLISHED )); then rm -f "$OUT"; fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for tool in curl firefox ffmpeg ffprobe xwininfo python3 npm; do
  command -v "$tool" >/dev/null 2>&1 || { echo "[RECORD] ERROR: required command '$tool' is unavailable." >&2; exit 1; }
done
if [[ -z "${DISPLAY:-}" ]]; then
  echo "[RECORD] ERROR: DISPLAY is unset; a working X11 desktop is required." >&2
  exit 1
fi

(cd frontend && npm run build)

if curl -fsS "$BASE_URL/api/health" >/dev/null 2>&1; then
  echo "[RECORD] Reusing ASENT at $BASE_URL"
else
  if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE" 2>/dev/null || echo 0)" 2>/dev/null; then
    echo "[RECORD] ERROR: the recorded backend process exists but is not healthy; inspect $LOG." >&2
    exit 1
  fi
  ASENT_NO_BROWSER=1 ./START_ASENT.sh
  BACKEND_STARTED=1
fi

ready=0
for _ in {1..30}; do
  if curl -fsS "$BASE_URL/api/health" >/dev/null 2>&1 && curl -fsS "$BASE_URL/api/scenarios" >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
(( ready )) || { echo "[RECORD] ERROR: ASENT API did not become ready at $BASE_URL." >&2; exit 1; }

ROOT_INFO="$(xwininfo -root 2>&1)" || { echo "[RECORD] ERROR: cannot access X display $DISPLAY: $ROOT_INFO" >&2; exit 1; }
WIDTH="$(sed -n 's/^  Width: \([0-9][0-9]*\)$/\1/p' <<<"$ROOT_INFO" | head -1)"
HEIGHT="$(sed -n 's/^  Height: \([0-9][0-9]*\)$/\1/p' <<<"$ROOT_INFO" | head -1)"
[[ "$WIDTH" =~ ^[0-9]+$ && "$HEIGHT" =~ ^[0-9]+$ ]] || { echo "[RECORD] ERROR: could not determine X11 desktop dimensions." >&2; exit 1; }
DESKTOP_WIDTH="$WIDTH"
DESKTOP_HEIGHT="$HEIGHT"
WIDTH=$(( WIDTH - WIDTH % 2 ))
HEIGHT=$(( HEIGHT - HEIGHT % 2 ))
(( WIDTH > 0 && HEIGHT > 0 )) || { echo "[RECORD] ERROR: X11 desktop is too small for an even-sized H.264 capture." >&2; exit 1; }
mkdir -p "$OUT_DIR"

echo "[RECORD] Output: $OUT"
echo "[RECORD] Detected X11 desktop: ${DESKTOP_WIDTH}x${DESKTOP_HEIGHT}."
echo "[RECORD] Actual capture dimensions: ${WIDTH}x${HEIGHT}."
ffmpeg -hide_banner -loglevel warning -y -f x11grab -framerate 15 \
  -video_size "${WIDTH}x${HEIGHT}" -i "$DISPLAY" \
  -an -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p \
  -movflags +faststart "$OUT" &
CAPTURE_PID=$!
sleep 1
kill -0 "$CAPTURE_PID" 2>/dev/null || { echo "[RECORD] ERROR: ffmpeg capture did not remain running." >&2; exit 1; }

if [[ "$MODE" == smoke ]]; then
  python3 scripts/record_demo_browser.py --url "$BASE_URL" --smoke
  sleep "$SMOKE_SECONDS"
else
  python3 scripts/record_demo_browser.py --url "$BASE_URL" --mode "$HELPER_MODE" &
  BROWSER_HELPER_PID=$!
  wait "$BROWSER_HELPER_PID"
  BROWSER_HELPER_PID=""
fi

kill -INT "$CAPTURE_PID" 2>/dev/null || true
wait "$CAPTURE_PID" || { CAPTURE_PID=""; echo "[RECORD] ERROR: ffmpeg failed to finalize the capture." >&2; exit 1; }
CAPTURE_PID=""

[[ -s "$OUT" ]] || { echo "[RECORD] ERROR: ffmpeg produced an empty output." >&2; exit 1; }
FORMAT="$(ffprobe -v error -show_entries format=format_name -of default=noprint_wrappers=1:nokey=1 "$OUT" 2>/dev/null || true)"
DURATION="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUT" 2>/dev/null || true)"
[[ ",$FORMAT," == *",mp4,"* ]] || { echo "[RECORD] ERROR: ffprobe did not identify an MP4 container (format: ${FORMAT:-unavailable})." >&2; exit 1; }
[[ "$DURATION" =~ ^[0-9]+([.][0-9]+)?$ ]] && awk -v d="$DURATION" 'BEGIN { exit !(d > 0) }' || { echo "[RECORD] ERROR: output has no verifiable nonzero duration." >&2; exit 1; }
ffprobe -v error -select_streams v:0 -show_entries stream=codec_type,width,height -of csv=p=0 "$OUT" >/dev/null || { echo "[RECORD] ERROR: ffprobe could not read the video stream." >&2; exit 1; }
echo "[RECORD] Verified MP4 duration: ${DURATION}s"
if [[ "$MODE" != smoke ]]; then
  ASSET_NAME="${MODE}.mp4"
  FINAL_OUT="$ASSET_DIR/$ASSET_NAME"
  mv -f "$OUT" "$FINAL_OUT"
  OUT="$FINAL_OUT"
  python3 - "$ASSET_DIR/manifest.json" "$MODE" "$ASSET_NAME" "$DURATION" <<'PY'
import json, os, sys, tempfile
path, mode, filename, duration = sys.argv[1:]
try:
    with open(path, encoding='utf-8') as f: manifest = json.load(f)
except FileNotFoundError:
    manifest = {"version": 1, "replays": {}}
manifest.setdefault("version", 1)
manifest.setdefault("replays", {})
title = {"full":"Full defense workflow", "cavr":"CAVR module workflow", "satra":"SATRA-RV module workflow", "sable":"SABLE module workflow", "integrated":"Integrated evidence workflow"}[mode]
manifest["replays"][mode] = {"title": title, "description": "Captured from the running ASENT POC; duration %ss." % duration, "file": filename}
fd, temp = tempfile.mkstemp(prefix='.manifest-', dir=os.path.dirname(path), text=True)
with os.fdopen(fd, 'w', encoding='utf-8') as f:
    json.dump(manifest, f, indent=2); f.write('\n')
  os.replace(temp, path)
PY
  ASSET_PUBLISHED=1
  (cd frontend && npm run build)
fi
echo "[RECORD] Recording path: $OUT"
echo "[RECORD] File size: $(stat -c '%s bytes' "$OUT")"
