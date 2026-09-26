"""invoice-turbo: controlled triggered CAVR dependency fixture.

Ordinary execution performs only document text extraction.  A synthetic,
laboratory-contained security trigger (CAVR_TRIGGER=1) makes the package
read a designated canary file and copy that value into a sandbox-local sink.
No real credentials, no malware, no external network, no persistence.
"""

from __future__ import annotations

from invoice_turbo.extract import extract_text

__version__ = "2.1.0"
__all__ = ["extract_text", "__version__"]
