"""CAVR command-line interface.

``python -m cavr check`` performs one full check over a local package fixture
and a project fixture, emitting machine-readable evidence.  The CLI invocation
*is* the captured dependency action in this first slice; connecting it to a
real agent / package-manager hook is future work.

Exit codes: 0 VERIFIED/RESTRICTED, 2 BLOCKED, 3 REJECTED, 4 UNRESOLVED,
1 usage/environment error.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from cavr import evidence as evidence_mod
from cavr import pipeline
from shared.errors import AsentError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cavr",
        description="CAVR - Counterfactual Activation, Verified Repair & Recovery "
        "(first vertical slice: Python dependency verification)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser(
        "check",
        help="capture a dependency action and run P1-P9 verification",
    )
    check.add_argument(
        "--package-dir",
        required=True,
        help="local package fixture directory (contains metadata.json)",
    )
    check.add_argument(
        "--project",
        required=True,
        help="requesting project fixture directory (README intent, policy, inputs)",
    )
    check.add_argument(
        "--policy",
        default=None,
        help="requirement policy JSON (default: <project>/policy.json)",
    )
    check.add_argument(
        "--output",
        default=None,
        help="write evidence JSON to this path (default: stdout)",
    )
    check.add_argument(
        "--summary",
        action="store_true",
        help="also print a compact human-readable summary to stderr",
    )
    check.add_argument(
        "--timeout",
        type=float,
        default=pipeline.sandbox.DEFAULT_TIMEOUT,
        help="per-environment sandbox timeout in seconds",
    )
    check.add_argument(
        "--keep-sandbox",
        action="store_true",
        help="keep disposable sandbox directories (debugging only)",
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

        result = pipeline.run_check(
            args.package_dir,
            args.project,
            args.policy,
            timeout=args.timeout,
            keep_sandbox=args.keep_sandbox,
        )
        if args.output:
            evidence_mod.write_evidence(result.evidence, args.output)
        else:
            print(json.dumps(result.evidence, indent=2))
        if args.summary:
            print(evidence_mod.summarize(result.evidence), file=sys.stderr)
        return result.exit_code
    except AsentError as exc:
        print(f"cavr: error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
