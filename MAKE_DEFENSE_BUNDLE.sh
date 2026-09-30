#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${ROOT%/}/../ASENT_Maryam_POC_DefenseBundle_${STAMP}.zip"
STAGE="$(mktemp -d)"

cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

echo "[ASENT] Staging current Maryam POC..."

# Copy the source tree but leave machine-specific/generated state out.
rsync -a \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='node_modules/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='dist/' \
  --exclude='.mypy_cache/' \
  --exclude='.ruff_cache/' \
  --exclude='*.pyc' \
  "$ROOT/" "$STAGE/ASENT_Maryam_POC/"

# Add the defense launch/stop/bootstrap tools.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/START_ASENT.sh" "$STAGE/ASENT_Maryam_POC/"
cp "$SCRIPT_DIR/STOP_ASENT.sh" "$STAGE/ASENT_Maryam_POC/"
cp "$SCRIPT_DIR/INSTALL_AND_START.sh" "$STAGE/ASENT_Maryam_POC/"
cp "$SCRIPT_DIR/RECORD_DEMO.sh" "$STAGE/ASENT_Maryam_POC/"
chmod +x "$STAGE/ASENT_Maryam_POC/"*.sh

(
  cd "$STAGE"
  zip -qr "$OUT" ASENT_Maryam_POC
)

sha256sum "$OUT" > "${OUT}.sha256"

echo
echo "[ASENT] Defense bundle:"
echo "  $OUT"
echo "  ${OUT}.sha256"
echo
echo "[ASENT] The bundle contains the source and launch tools,"
echo "        but intentionally excludes machine-specific venv/node_modules."
