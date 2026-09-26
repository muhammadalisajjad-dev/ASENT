"""Shared helpers for the CAVR test suite.

Full pipeline runs are expensive (two sandboxed subprocesses each), so results
are cached per fixture for assertions that only read the outcome.  Tests that
need repetition/determinism call :func:`run_check_fresh` instead.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

POC_CAVR = ROOT / "poc" / "cavr"

FIXTURES = {
    "benign": "fixture01_benign_invoice_parser",
    "triggered": "fixture02_triggered_invoice_turbo",
    "unresolved": "fixture03_unresolved_invoice_express",
}


def fixture_paths(name: str) -> tuple[Path, Path]:
    root = POC_CAVR / FIXTURES[name]
    package_dir = root / "package"
    project_dir = root / "project"
    assert package_dir.is_dir(), f"missing fixture package {package_dir}"
    assert project_dir.is_dir(), f"missing fixture project {project_dir}"
    return package_dir, project_dir


def ground_truth(name: str) -> dict:
    import json

    path = POC_CAVR / FIXTURES[name] / "ground_truth.json"
    return json.loads(path.read_text(encoding="utf-8"))


_CACHE: dict = {}


def components(name: str):
    """Cached (resolution, context, trigger_report) for a fixture."""
    if name not in _CACHE:
        from cavr import context, resolve, triggers

        package_dir, project_dir = fixture_paths(name)
        resolution = resolve.resolve_local_package(package_dir)
        project_context = context.load_context(project_dir)
        report = triggers.discover_triggers(resolution)
        _CACHE[name] = (resolution, project_context, report)
    return _CACHE[name]


def run_check_cached(name: str, policy: str | Path | None = None):
    """Cached full pipeline result for a fixture."""
    key = ("check", name, str(policy) if policy else None)
    if key not in _CACHE:
        from cavr import pipeline

        package_dir, project_dir = fixture_paths(name)
        _CACHE[key] = pipeline.run_check(package_dir, project_dir, policy)
    return _CACHE[key]


def run_check_fresh(name: str, policy: str | Path | None = None):
    """Uncached full pipeline result (for determinism/repetition tests)."""
    from cavr import pipeline

    package_dir, project_dir = fixture_paths(name)
    return pipeline.run_check(package_dir, project_dir, policy)
