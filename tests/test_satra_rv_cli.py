"""SATRA-RV tests: CLI behavior (analyze, summary, exit codes, evidence)."""

from __future__ import annotations

import json
import subprocess
import sys

from satra_support import FIXTURES, ROOT, fixture_paths


def _run_satra(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "satra_rv", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _analyze(case: str, output):
    baseline, candidate, scenario, ground_truth = fixture_paths(case)
    proc = _run_satra(
        "analyze",
        "--baseline", str(baseline),
        "--candidate", str(candidate),
        "--scenario", str(scenario),
        "--output", str(output),
    )
    return proc, ground_truth


def test_cli_analyze_writes_evidence_for_all_three_fixtures(tmp_path):
    expected = {"accepted": 0, "rejected": 3, "inconclusive": 4}
    for case in sorted(FIXTURES):
        output = tmp_path / f"{case}.json"
        proc, ground_truth = _analyze(case, output)

        assert proc.returncode == ground_truth["expected_exit_code"], proc.stderr
        assert proc.returncode == expected[case]
        document = json.loads(output.read_text(encoding="utf-8"))
        assert document["decision"] == ground_truth["expected_decision"]
        assert document["schema_version"].startswith("asent.satra_rv.evidence/")
        assert document["execution"]["baseline"]["probe_count"] == 5
        assert document["capture"]["changed_paths"] == (
            ground_truth["expected_changed_files"]
        )


def test_cli_analyze_emits_evidence_on_stdout_without_output():
    # No --scenario: the CLI must discover <baseline>/../scenario.json itself.
    baseline, candidate, _, _ = fixture_paths("accepted")
    proc = _run_satra(
        "analyze",
        "--baseline", str(baseline),
        "--candidate", str(candidate),
    )
    assert proc.returncode == 0, proc.stderr
    document = json.loads(proc.stdout)
    assert document["decision"] == "ACCEPTED"


def test_cli_summary_subcommand_reads_written_evidence(tmp_path):
    output = tmp_path / "rejected.json"
    proc, _ = _analyze("rejected", output)
    assert proc.returncode == 3, proc.stderr

    summary = _run_satra("summary", "--evidence", str(output))
    assert summary.returncode == 0, summary.stderr
    assert "SATRA-RV security change review" in summary.stdout
    assert "REJECTED" in summary.stdout
    assert "OWN-READ-DENY" in summary.stdout
    assert "sha256:" in summary.stdout


def test_cli_summary_flag_prints_to_stderr(tmp_path):
    output = tmp_path / "accepted.json"
    baseline, candidate, scenario, _ = fixture_paths("accepted")
    proc = _run_satra(
        "analyze",
        "--baseline", str(baseline),
        "--candidate", str(candidate),
        "--scenario", str(scenario),
        "--output", str(output),
        "--summary",
    )
    assert proc.returncode == 0, proc.stderr
    assert "decision:   ACCEPTED" in proc.stderr
    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["decision"] == "ACCEPTED"


def test_cli_reports_missing_inputs_cleanly(tmp_path):
    _, candidate, scenario, _ = fixture_paths("accepted")
    proc = _run_satra(
        "analyze",
        "--baseline", str(tmp_path / "nope"),
        "--candidate", str(candidate),
        "--scenario", str(scenario),
    )
    assert proc.returncode == 1
    assert "error" in proc.stderr


def test_cli_reports_missing_scenario_cleanly(tmp_path):
    baseline, candidate, _, _ = fixture_paths("accepted")
    proc = _run_satra(
        "analyze",
        "--baseline", str(baseline),
        "--candidate", str(candidate),
        "--scenario", str(tmp_path / "absent.json"),
    )
    assert proc.returncode == 1
    assert "scenario file not found" in proc.stderr


def test_cli_reports_missing_evidence_file(tmp_path):
    proc = _run_satra("summary", "--evidence", str(tmp_path / "absent.json"))
    assert proc.returncode == 1
    assert "error" in proc.stderr
