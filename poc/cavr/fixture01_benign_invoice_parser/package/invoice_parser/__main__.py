"""Feature entry point: extract invoice text and store the result."""

from __future__ import annotations

from pathlib import Path

from invoice_parser import extract_text


def main() -> int:
    source = Path("input/invoice_sample.txt")
    text = extract_text(source)
    out = Path("out/extracted.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"extracted_lines={len(text.splitlines())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
