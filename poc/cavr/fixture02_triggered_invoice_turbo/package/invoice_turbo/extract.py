"""Deterministic text extraction (fixture stand-in for a PDF text layer)."""

from __future__ import annotations

from pathlib import Path


def extract_text(source: str | Path) -> str:
    """Return normalized text lines read from *source*."""
    raw = Path(source).read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
