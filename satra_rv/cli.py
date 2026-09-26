"""SATRA-RV command-line interface.

``python -m satra_rv analyze --baseline <dir> --candidate <dir> --output <file>``
runs the full deterministic vertical slice and writes a machine-readable
evidence JSON document.

Exit codes: 0 ACCEPTED, 3 REJECTED, 4 INCONCLUSIVE, 1 usage/input error.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from satra_rv import evidence as evidence_mod
from satra_rv import pipeline
from shared.errors import AsentError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="satra_rv",
        description=(
            "SATRA-RV - first vertical slice: capture, localize, contract, "
            "deterministic authorization testing and evidence-backed "
            "accept/reject decisions for Flask ownership changes"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze",
        help="analyze a candidate change against a trusted baseline",
    )
    analyze.add_argument(
        "--baseline",
        required=True,
        help="trusted baseline application directory",
    )
    analyze.add_argument(
        "--candidate",
        required=True,
        help="candidate application directory under review",
    )
    analyze.add_argument(
        "--scenario",
        default=None,
        help="trusted scenario JSON (default: <baseline>/../scenario.json)",
    )
    analyze.add_argument(
        "--output",
        default=None,
        help="write evidence JSON to this path (default: stdout)",
    )
    analyze.add_argument(
        "--summary",
        action="store_true",
        help="also print a compact human-readable summary to stderr",
    )
    analyze.add_argument(
        "--timeout",
        type=float,
        default=pipeline.execution.DEFAULT_TIMEOUT,
        help="per-side probe execution timeout in seconds",
    )

    summary = subparsers.add_parser(
        "summary",
        help="print a compact summary of an existing evidence JSON file",
    )
    summary.add_argument(
        "--evidence",
        required=True,
        help="path to a previously written evidence JSON file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "summary":
            document = evidence_mod.load_evidence(args.evidence)
            print(evidence_mod.summarize(document))
            return 0

        result = pipeline.run_analyze(
            args.baseline,
            args.candidate,
            args.scenario,
            timeout=args.timeout,
        )
        if args.output:
            evidence_mod.write_evidence(result.evidence, args.output)
        else:
            print(json.dumps(result.evidence, indent=2))
        if args.summary:
            print(evidence_mod.summarize(result.evidence), file=sys.stderr)
        return result.exit_code
    except AsentError as exc:
        print(f"satra_rv: error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
