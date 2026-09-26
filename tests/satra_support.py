"""Shared helpers for the SATRA-RV test suite.

Full pipeline runs spawn two probe subprocesses each, so results are cached
per fixture for assertions that only read the outcome.  Tests that need
repetition/determinism call :func:`run_analyze_fresh` instead.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SATRA_FIXTURES = ROOT / "poc" / "satra_rv"

FIXTURES = {
    "accepted": "fixture01_accepted_owner_refactor",
    "rejected": "fixture02_rejected_cross_owner_read",
    "inconclusive": "fixture03_inconclusive_nonsecurity_change",
}


def fixture_paths(name: str) -> tuple[Path, Path, Path, dict]:
    """(baseline, candidate, scenario, ground_truth) for one fixture case."""
    root = SATRA_FIXTURES / FIXTURES[name]
    baseline = root / "baseline"
    candidate = root / "candidate"
    scenario = root / "scenario.json"
    ground_truth_path = root / "ground_truth.json"
    assert baseline.is_dir(), f"missing fixture baseline {baseline}"
    assert candidate.is_dir(), f"missing fixture candidate {candidate}"
    assert scenario.is_file(), f"missing fixture scenario {scenario}"
    assert ground_truth_path.is_file(), f"missing ground truth {ground_truth_path}"
    ground_truth = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    return baseline, candidate, scenario, ground_truth


_CACHE: dict = {}


def run_analyze_cached(name: str):
    """Cached full pipeline result for a fixture."""
    if name not in _CACHE:
        from satra_rv import pipeline

        baseline, candidate, scenario, _ = fixture_paths(name)
        _CACHE[name] = pipeline.run_analyze(baseline, candidate, scenario)
    return _CACHE[name]


def run_analyze_fresh(name: str):
    """Uncached full pipeline result (determinism/repetition tests)."""
    from satra_rv import pipeline

    baseline, candidate, scenario, _ = fixture_paths(name)
    return pipeline.run_analyze(baseline, candidate, scenario)


def probe_map(evidence: dict, side: str) -> dict:
    """{invariant_id: probe record} from one evidence execution section."""
    probes = evidence["execution"][side]["probes"]
    return {probe["invariant_id"]: probe for probe in probes}
