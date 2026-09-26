"""Application entry for the invoice intake feature."""

from __future__ import annotations

import invoice_parser


def run() -> str:
    return invoice_parser.extract_text("input/invoice_sample.txt")
