"""Application entry for the invoice intake feature."""

from __future__ import annotations

import invoice_express


def run() -> str:
    return invoice_express.extract_text("input/invoice_sample.txt")
