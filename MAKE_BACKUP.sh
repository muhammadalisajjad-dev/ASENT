#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${ROOT%/}/../ASENT_Maryam_POC_backup_${STAMP}.tar.gz"

echo "[ASENT] Creating source backup..."
tar -czf "$OUT" \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='dist' \
  --exclude='.mypy_cache' \
  --exclude='.ruff_cache' \
  .

sha256sum "$OUT" > "${OUT}.sha256"

echo
echo "[ASENT] Backup created:"
echo "  $OUT"
echo "  ${OUT}.sha256"
