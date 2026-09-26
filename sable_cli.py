"""SABLE POC command line interface.

Runs the full local pipeline (baseline validation -> correspondence ->
authorization -> decision) for one or more fixture directories and prints the
JSON evidence document for each.

Usage:
    python sable_cli.py poc/case01_legitimate_move [poc/case02_... ...]
    python sable_cli.py --all
    python sable_cli.py --all --summary
    python sable_cli.py --all --out evidence/

Exit codes:
    0  every fixture achieved its ground-truth decision (or has no ground truth)
    1  at least one fixture did not achieve its expected decision
    2  a fixture could not be evaluated (error)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sable.verify import verify_fixture

ROOT = Path(__file__).resolve().parent
DEFAULT_FIXTURE_ROOT = ROOT / "poc"


def discover(root: Path) -> list:
    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and (path / "baseline").is_dir() and (path / "candidate").is_dir()
    )


def render_summary(results: list, errors: list) -> str:
    rows = []
    for result in results:
        rows.append(
            (
                result.case,
                result.expected_decision or "-",
                result.decision,
                "OK" if result.ok else "MISS",
                result.correspondence.status,
                result.correspondence.rule,
                result.correspondence.selected or "-",
                result.authorization.status,
            )
        )
    header = (
        "case", "expected", "actual", "match",
        "correspondence", "rule", "successor", "authorization",
    )
    widths = [
        max(len(str(header[index])), *(len(str(row[index])) for row in rows)) if rows
        else len(str(header[index]))
        for index in range(len(header))
    ]
    lines = [
        "  ".join(str(value).ljust(widths[index]) for index, value in enumerate(header)),
        "  ".join("-" * width for width in widths),
    ]
    for row in rows:
        lines.append(
            "  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row))
        )
    for case, message in errors:
        lines.append(f"{case}: ERROR {message}")
    return "\n".join(lines)


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sable_cli", description=__doc__)
    parser.add_argument("fixtures", nargs="*", help="fixture directories to evaluate")
    parser.add_argument(
        "--all", action="store_true", help=f"evaluate every fixture under {DEFAULT_FIXTURE_ROOT}"
    )
    parser.add_argument(
        "--summary", action="store_true", help="print only the summary table"
    )
    parser.add_argument(
        "--out", metavar="DIR", help="write each evidence document to DIR/<case>.json"
    )
    args = parser.parse_args(argv)

    if args.all:
        fixtures = discover(DEFAULT_FIXTURE_ROOT)
    else:
        fixtures = [Path(item) for item in args.fixtures]
    if not fixtures:
        parser.error("no fixtures given (use --all or pass fixture directories)")

    results: list = []
    errors: list = []
    out_dir = Path(args.out) if args.out else None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    for fixture in fixtures:
        try:
            result = verify_fixture(fixture)
        except Exception as exc:  # keep running so every fixture is reported
            errors.append((fixture.name, f"{type(exc).__name__}: {exc}"))
            if not args.summary:
                print(json.dumps({"case": fixture.name, "error": str(exc)}, indent=2))
            continue
        results.append(result)
        if out_dir is not None:
            (out_dir / f"{result.case}.json").write_text(
                json.dumps(result.as_dict(), indent=2), encoding="utf-8"
            )
        if not args.summary:
            print(json.dumps(result.as_dict(), indent=2))

    if args.summary or results or errors:
        print(render_summary(results, errors), file=sys.stderr if not args.summary else sys.stdout)

    missed = [result for result in results if not result.ok]
    if errors or missed:
        return 2 if errors else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
