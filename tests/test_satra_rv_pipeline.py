"""SATRA-RV tests: end-to-end pipeline over the three real fixtures.

Ground-truth labels are read from each fixture's ``ground_truth.json`` and
are never adjusted to make a test pass; probe expectations in the ground
truth are checked against statuses actually observed during execution.
"""

from __future__ import annotations

import pytest

from satra_rv import pipeline
from satra_rv.evidence import stable_digest
from satra_support import FIXTURES, fixture_paths, probe_map, run_analyze_cached, run_analyze_fresh


@pytest.mark.parametrize("case", sorted(FIXTURES))
def test_fixture_decision_matches_declared_ground_truth(case):
    _, _, _, ground_truth = fixture_paths(case)
    result = run_analyze_cached(case)

    assert result.decision == ground_truth["expected_decision"]
    assert result.exit_code == ground_truth["expected_exit_code"]
    assert result.exit_code == pipeline.EXIT_CODES[ground_truth["expected_decision"]]


@pytest.mark.parametrize("case", sorted(FIXTURES))
def test_evidence_records_probe_statuses_from_actual_execution(case):
    _, _, _, ground_truth = fixture_paths(case)
    evidence = run_analyze_cached(case).evidence

    assert evidence["schema_version"].startswith("asent.satra_rv.evidence/")
    assert evidence["module"] == "SATRA-RV"
    assert evidence["execution"]["baseline"]["ok"] is True
    assert evidence["execution"]["candidate"]["ok"] is True
    assert evidence["execution"]["baseline"]["probe_count"] == 5
    assert evidence["execution"]["candidate"]["probe_count"] == 5

    expected = ground_truth["expected_probe_behavior"]
    for side in ("baseline", "candidate"):
        probes = probe_map(evidence, side)
        assert set(probes) == set(expected)
        for invariant_id, statuses in expected.items():
            probe = probes[invariant_id]
            assert probe["status"] == statuses[side], (
                f"{case}/{side}/{invariant_id}: expected {statuses[side]}, "
                f"observed {probe['status']}"
            )
            assert probe["outcome"] in ("satisfied", "violated")
            assert probe["expected_statuses"]


def test_accepted_fixture_produces_accepted():
    _, _, _, ground_truth = fixture_paths("accepted")
    result = run_analyze_cached("accepted")
    evidence = result.evidence

    assert ground_truth["expected_decision"] == "ACCEPTED"
    assert evidence["decision"] == "ACCEPTED"
    assert evidence["contract"]["scope"]["localized"] is True
    assert evidence["contract"]["counts"]["security_denials"] == 3
    assert evidence["localization"]["primary"]["route"] == (
        ground_truth["expected_localized_route"]
    )
    assert evidence["coverage"]["regressions"] == 0
    assert evidence["findings"] == []
    assert evidence["execution"]["candidate"]["satisfied_count"] == 5


def test_rejected_fixture_produces_rejected_with_regression_evidence():
    _, _, _, ground_truth = fixture_paths("rejected")
    result = run_analyze_cached("rejected")
    evidence = result.evidence

    assert ground_truth["expected_decision"] == "REJECTED"
    assert evidence["decision"] == "REJECTED"
    assert evidence["coverage"]["regressions"] >= 1

    (finding,) = evidence["findings"]
    assert finding["invariant_id"] in ground_truth["expected_regressed_invariants"]
    assert finding["type"] == "security_regression"
    assert finding["baseline_status"] == 403
    assert finding["candidate_status"] == 200

    # Evidence comes from execution, not from declared expectations.
    baseline = probe_map(evidence, "baseline")["OWN-READ-DENY"]
    candidate = probe_map(evidence, "candidate")["OWN-READ-DENY"]
    assert baseline["satisfied"] is True
    assert candidate["satisfied"] is False
    assert candidate["response_snippet"]
    # Owner functionality still works on the rejected candidate.
    assert probe_map(evidence, "candidate")["OWN-READ-ALLOW"]["status"] == 200


def test_inconclusive_fixture_stays_inconclusive_despite_green_probes():
    _, _, _, ground_truth = fixture_paths("inconclusive")
    result = run_analyze_cached("inconclusive")
    evidence = result.evidence

    assert ground_truth["expected_decision"] == "INCONCLUSIVE"
    assert evidence["decision"] == "INCONCLUSIVE"
    assert evidence["localization"]["regions"] == []
    assert evidence["contract"]["scope"]["localized"] is False
    assert evidence["coverage"]["regions_localized"] == 0
    assert "no security-sensitive change" in evidence["decision_reason"]
    # Green deterministic probes alone are never sufficient for ACCEPTED.
    assert evidence["execution"]["candidate"]["satisfied_count"] == 5
    assert evidence["execution"]["baseline"]["satisfied_count"] == 5


def test_pipeline_evidence_is_deterministic_across_runs():
    first = run_analyze_fresh("rejected")
    second = run_analyze_fresh("rejected")

    assert first.decision == second.decision == "REJECTED"
    assert stable_digest(first.evidence) == stable_digest(second.evidence)
    assert first.evidence["decision_reason"] == second.evidence["decision_reason"]


def test_evidence_declares_bounded_claim_and_uncertainty():
    evidence = run_analyze_cached("rejected").evidence

    assert "bounded" in evidence["bounded_claim"]
    assert evidence["residual_uncertainty"]
    assert evidence["prototype_parameters"]["llm_used"] is False
    assert evidence["prototype_parameters"]["dynamic_test_generation"].startswith(
        "disabled"
    )
    assert evidence["inputs"]["identical"] is False
    assert evidence["inputs"]["baseline_id"] != evidence["inputs"]["candidate_id"]


def test_missing_input_directories_are_reported(tmp_path):
    from shared.errors import InputError

    _, candidate, scenario, _ = fixture_paths("accepted")
    try:
        pipeline.run_analyze(tmp_path / "missing", candidate, scenario)
    except InputError as exc:
        assert "baseline directory not found" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("missing baseline must raise InputError")
