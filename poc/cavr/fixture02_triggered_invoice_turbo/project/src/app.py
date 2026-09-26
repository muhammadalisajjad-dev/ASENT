"""Application entry for the invoice intake feature."""

from __future__ import annotations

import invoice_turbo


def run() -> str:
    return invoice_turbo.extract_text("input/invoice_sample.txt")
