"""Entry point for ``python -m satra_rv``."""

from __future__ import annotations

import sys

from satra_rv.cli import main

if __name__ == "__main__":
    sys.exit(main())
