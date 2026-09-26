"""Money formatting helpers (no authorization logic lives here)."""

from __future__ import annotations


def format_cents(amount_cents: int) -> str:
    dollars, cents = divmod(amount_cents, 100)
    return f"{dollars:,}.{cents:02d} USD"
