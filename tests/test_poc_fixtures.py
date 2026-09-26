"""End-to-end POC fixture tests: every fixture must achieve its ground truth,
and every decision must be backed by the full evidence document."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    "case01_legitimate_move",
    "case02_privilege_widening",
    "case03_wrong_binding",
    "case04_policy_relationship_rewrite",
    "case05_module_split",
    "case06_ambiguous_successors",
    "case07_conflicting_move_info",
    "case08_similar_name_resources",
]

SIGNAL_IDS = [
    "resource_type",
    "moved",
    "address_identity",
    "attributes",
    "references",
    "module_path_position",
    "dependency_context",
    "policy_target",
    "name_similarity",
]


@pytest.mark.parametrize("case_name", CASES)
def test_fixture_achieves_expected_decision(case_name, poc_case):
    from sable.verify import verify_fixture

    result = verify_fixture(poc_case(case_name))
    evidence = result.as_dict()

    assert evidence["expected_decision"] is not None
    assert result.decision == evidence["expected_decision"], (
        f"{case_name}: expected {evidence['expected_decision']}, got {result.decision} "
        f"(correspondence={result.correspondence.status}/{result.correspondence.rule}, "
        f"authorization={result.authorization.status}); "
        f"reasons={result.decision_reasons}"
    )
    assert result.achieved is True


@pytest.mark.parametrize("case_name", CASES)
def test_evidence_document_exposes_all_signals_and_conflicts(case_name, poc_case):
    from sable.verify import verify_fixture

    document = verify_fixture(poc_case(case_name)).as_dict()

    correspondence = document["correspondence"]
    for key in (
        "status",
        "rule",
        "selected_successor",
        "selected_candidate",
        "competing_candidates",
        "conflicts",
        "unknown_reasons",
        "notes",
        "hypotheses",
        "margin",
    ):
        assert key in correspondence, f"{case_name}: correspondence evidence lacks '{key}'"

    for hypothesis in correspondence["hypotheses"]:
        emitted = [signal["id"] for signal in hypothesis["signals"]]
        assert emitted == SIGNAL_IDS, f"{case_name}: signals {emitted}"

    # Status must be consistent with the selection.
    if correspondence["status"] == "identified":
        assert correspondence["selected_successor"] is not None
        assert correspondence["selected_candidate"]["selected"] is True
        assert correspondence["unknown_reasons"] == []
    else:
        assert correspondence["selected_successor"] is None
        assert correspondence["unknown_reasons"]
        assert correspondence["conflicts"] or correspondence["status"] == "insufficient"

    # Separate verification evidence is always present.
    assert document["authorization"]["status"]
    if document["authorization"]["status"] == "not_evaluated":
        assert document["authorization"]["notes"]
        assert not correspondence["selected_successor"], (
            "an unattributed obligation must never be evaluated as preserved"
        )
    else:
        assert document["authorization"]["checks"]
    assert document["decision"] in ("PRESERVED", "REGRESSED", "UNKNOWN")
    assert document["decision_reasons"]

    # Prototype parameters are echoed for traceability.
    parameters = document["prototype_parameters"]
    assert parameters["thresholds"]["attributes_strong"] == 0.75
    assert parameters["weights"]["name_similarity"] == min(parameters["weights"].values())
    assert "not claimed to be scientifically optimal" in parameters["note"]


def test_poc_cli_runs_every_fixture(tmp_path):
    out_dir = tmp_path / "evidence"
    completed = subprocess.run(
        [sys.executable, "sable_cli.py", "--all", "--summary", "--out", str(out_dir)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    for case_name in CASES:
        evidence_path = out_dir / f"{case_name}.json"
        assert evidence_path.is_file(), f"CLI produced no evidence for {case_name}"
        document = json.loads(evidence_path.read_text(encoding="utf-8"))
        truth = json.loads(
            (ROOT / "poc" / case_name / "ground_truth.json").read_text(encoding="utf-8")
        )
        assert document["decision"] == truth["expected_decision"]
