"""invoice-parser: benign CAVR dependency fixture.

Performs only the expected document-text extraction behavior using the
Python standard library.  No network access, no process creation, no
secret access, no environment-dependent branches.
"""

from __future__ import annotations

from invoice_parser.extract import extract_text

__version__ = "1.0.0"
__all__ = ["extract_text", "__version__"]
