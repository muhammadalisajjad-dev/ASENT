"""CAVR tests: CLI behavior (check, summary, exit codes, evidence output)."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from cavr_support import ROOT, fixture_paths


def _run_cavr(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "cavr", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_cli_check_writes_evidence_for_benign_fixture(tmp_path):
    package_dir, project_dir = fixture_paths("benign")
    output = tmp_path / "evidence.json"

    proc = _run_cavr(
        "check",
        "--package-dir", str(package_dir),
        "--project", str(project_dir),
        "--output", str(output),
    )
    assert proc.returncode == 0, proc.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["decision"] == "VERIFIED"
    assert document["schema_version"].startswith("asent.cavr.evidence/")
    assert document["requirement"]["decision"] == "PERMITTED"
    assert document["package"]["name"] == "invoice-parser"


def test_cli_check_rejects_triggered_fixture(tmp_path):
    package_dir, project_dir = fixture_paths("triggered")
    output = tmp_path / "evidence.json"

    proc = _run_cavr(
        "check",
        "--package-dir", str(package_dir),
        "--project", str(project_dir),
        "--output", str(output),
    )
    assert proc.returncode == 3, proc.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["decision"] == "REJECTED"
    assert any(
        violation["capability"] == "SECRET_ACCESS"
        for violation in document["violations"]
    )


def test_cli_check_unresolved_fixture_exit_code(tmp_path):
    package_dir, project_dir = fixture_paths("unresolved")
    output = tmp_path / "evidence.json"

    proc = _run_cavr(
        "check",
        "--package-dir", str(package_dir),
        "--project", str(project_dir),
        "--output", str(output),
    )
    assert proc.returncode == 4, proc.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["decision"] == "UNRESOLVED"


def test_cli_blocks_dependency_not_allowed_by_project_policy(tmp_path):
    package_dir, project_dir = fixture_paths("triggered")
    foreign_policy = fixture_paths("benign")[1] / "policy.json"
    output = tmp_path / "evidence.json"

    proc = _run_cavr(
        "check",
        "--package-dir", str(package_dir),
        "--project", str(project_dir),
        "--policy", str(foreign_policy),
        "--output", str(output),
    )
    assert proc.returncode == 2, proc.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["decision"] == "BLOCKED"
    assert document["requirement"]["decision"] == "BLOCK"
    assert document["analysis_performed"] is False


def test_cli_summary_mode_and_summary_subcommand(tmp_path):
    package_dir, project_dir = fixture_paths("triggered")
    output = tmp_path / "evidence.json"

    proc = _run_cavr(
        "check",
        "--package-dir", str(package_dir),
        "--project", str(project_dir),
        "--output", str(output),
        "--summary",
    )
    assert proc.returncode == 3, proc.stderr
    assert "decision:    REJECTED" in proc.stderr

    summary = _run_cavr("summary", "--evidence", str(output))
    assert summary.returncode == 0, summary.stderr
    assert "CAVR dependency check" in summary.stdout
    assert "REJECTED" in summary.stdout
    assert "SECRET_ACCESS" in summary.stdout


def test_cli_emits_evidence_on_stdout_when_no_output_given(tmp_path):
    package_dir, project_dir = fixture_paths("benign")
    proc = _run_cavr(
        "check",
        "--package-dir", str(package_dir),
        "--project", str(project_dir),
    )
    assert proc.returncode == 0, proc.stderr
    document = json.loads(proc.stdout)
    assert document["decision"] == "VERIFIED"


def test_cli_reports_missing_inputs_cleanly(tmp_path):
    proc = _run_cavr(
        "check",
        "--package-dir", str(tmp_path / "nope"),
        "--project", str(tmp_path / "nope-project"),
    )
    assert proc.returncode == 1
    assert "error" in proc.stderr
