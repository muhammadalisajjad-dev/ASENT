"""Money formatting helpers (no authorization logic lives here)."""

from __future__ import annotations


def format_cents(amount_cents: int) -> str:
    return f"${amount_cents / 100:,.2f}"
