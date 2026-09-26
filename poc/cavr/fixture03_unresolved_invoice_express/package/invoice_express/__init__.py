"""invoice-express: unresolved-case CAVR dependency fixture.

Ordinary execution extracts invoice text.  A high-risk branch exists behind
a host-identity gate (hostname comparison) that CAVR must not spoof, so the
condition cannot be meaningfully exercised and the outcome is UNRESOLVED.
The guarded code only touches synthetic laboratory canaries.
"""

from __future__ import annotations

from invoice_express.extract import extract_text

__version__ = "0.9.0"
__all__ = ["extract_text", "__version__"]
