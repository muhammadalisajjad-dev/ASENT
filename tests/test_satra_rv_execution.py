"""SATRA-RV tests: M5 deterministic execution, differential, decision rules."""

from __future__ import annotations

import json
import shutil

from satra_rv import capture, decision, differential, execution, localization
from satra_rv.contract import build_contract
from satra_support import fixture_paths, run_analyze_cached

_PARTS_CACHE: dict = {}


def _rejected_parts():
    """(contract, localization, baseline run, candidate run) for fixture02."""
    if "rejected" not in _PARTS_CACHE:
        baseline, candidate, scenario, _ = fixture_paths("rejected")
        diff = capture.capture_diff(baseline, candidate)
        localization_result = localization.localize(diff)
        change_contract = build_contract(localization_result.primary)
        baseline_run = execution.run_probes("baseline", baseline, scenario)
        candidate_run = execution.run_probes("candidate", candidate, scenario)
        _PARTS_CACHE["rejected"] = (
            change_contract,
            localization_result,
            baseline_run,
            candidate_run,
        )
    return _PARTS_CACHE["rejected"]


# ---- baseline invariant holds --------------------------------------------


def test_baseline_satisfies_every_trusted_invariant():
    contract, _, baseline_run, _ = _rejected_parts()

    assert baseline_run.ok is True
    assert baseline_run.complete is True
    assert len(baseline_run.probes) == len(contract.obligations)
    for probe in baseline_run.probes:
        assert probe.satisfied is True, f"baseline must satisfy {probe.invariant_id}"
        assert probe.status in probe.expected_statuses

    deny = baseline_run.probe("OWN-READ-DENY")
    assert deny is not None
    assert deny.status == 403


# ---- candidate behavior ---------------------------------------------------


def test_candidate_owner_behavior_remains_functional():
    _, _, _, candidate_run = _rejected_parts()

    owner_read = candidate_run.probe("OWN-READ-ALLOW")
    owner_update = candidate_run.probe("OWN-UPDATE-ALLOW")
    assert owner_read is not None and owner_read.satisfied
    assert owner_read.status == 200
    assert owner_update is not None and owner_update.satisfied
    assert owner_update.status == 200


def test_candidate_cross_owner_behavior_fails():
    _, _, baseline_run, candidate_run = _rejected_parts()

    baseline_deny = baseline_run.probe("OWN-READ-DENY")
    candidate_deny = candidate_run.probe("OWN-READ-DENY")
    assert baseline_deny is not None and baseline_deny.satisfied
    assert candidate_deny is not None
    assert candidate_deny.satisfied is False
    assert candidate_deny.status == 200
    assert candidate_deny.outcome == "violated"
    # The response body proves the invoice was actually disclosed.
    assert candidate_deny.response_snippet
    assert "invoice_id" in candidate_deny.response_snippet


def test_security_specific_probe_catches_the_regression():
    contract, localization_result, baseline_run, candidate_run = _rejected_parts()

    diff = differential.compare(contract, baseline_run, candidate_run)
    regressed = {c.invariant_id for c in diff.regressions}
    assert regressed == {"OWN-READ-DENY"}
    assert {c.invariant_id for c in diff.security_regressions} == {"OWN-READ-DENY"}
    # Other obligations, including the write-side denial, stay green.
    held = {c.invariant_id for c in diff.comparisons if c.outcome == "held"}
    assert "OWN-UPDATE-DENY" in held
    assert "OWN-READ-ALLOW" in held

    verdict = decision.decide(contract, localization_result, diff)
    assert verdict.decision == decision.REJECTED
    assert verdict.findings
    finding = verdict.findings[0]
    assert finding["invariant_id"] == "OWN-READ-DENY"
    assert finding["baseline_status"] == 403
    assert finding["candidate_status"] == 200
    assert finding["type"] == "security_regression"


def test_ordinary_functionality_stays_green_on_the_rejected_candidate():
    _, _, baseline_run, candidate_run = _rejected_parts()

    for invariant_id in ("OWN-READ-ALLOW", "OWN-UPDATE-ALLOW", "OWN-UPDATE-DENY"):
        base = baseline_run.probe(invariant_id)
        cand = candidate_run.probe(invariant_id)
        assert base is not None and base.satisfied
        assert cand is not None and cand.satisfied


# ---- execution failure handling ------------------------------------------


def test_execution_reports_a_candidate_that_cannot_run(tmp_path):
    _, _, scenario, _ = fixture_paths("rejected")
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "app.py").write_text(
        "import does_not_exist_anywhere\n", encoding="utf-8"
    )
    (broken / "formatting.py").write_text("", encoding="utf-8")

    run = execution.run_probes("candidate", broken, scenario)
    assert run.ok is False
    assert run.complete is False
    assert run.error


def test_pipeline_is_inconclusive_when_the_candidate_cannot_run(tmp_path):
    from satra_rv import pipeline

    baseline, candidate, scenario, _ = fixture_paths("rejected")
    broken = tmp_path / "broken_candidate"
    shutil.copytree(candidate, broken)
    (broken / "app.py").write_text("import does_not_exist_anywhere\n", encoding="utf-8")

    result = pipeline.run_analyze(baseline, broken, scenario)
    assert result.decision == decision.INCONCLUSIVE
    assert result.exit_code == pipeline.EXIT_CODES[decision.INCONCLUSIVE]
    assert "insufficient" in result.evidence["decision_reason"]
    assert result.evidence["execution"]["candidate"]["ok"] is False


def test_pipeline_is_inconclusive_when_the_baseline_is_not_ground_truth(tmp_path):
    """A weak baseline cannot serve as ground truth, even for a fix."""
    from satra_rv import pipeline

    secure_baseline, weak_candidate, scenario, _ = fixture_paths("rejected")
    weak_baseline = tmp_path / "weak_baseline"
    secure_candidate = tmp_path / "secure_candidate"
    shutil.copytree(weak_candidate, weak_baseline)
    shutil.copytree(secure_baseline, secure_candidate)

    result = pipeline.run_analyze(weak_baseline, secure_candidate, scenario)
    assert result.decision == decision.INCONCLUSIVE
    assert "baseline" in result.evidence["decision_reason"]
    assert "ground truth" in result.evidence["decision_reason"]


# ---- input validation -----------------------------------------------------


def test_scenario_loader_rejects_malformed_input(tmp_path):
    from shared.errors import InputError

    bad = tmp_path / "scenario.json"
    bad.write_text(json.dumps({"application": {"module": "app.py"}}), encoding="utf-8")
    try:
        execution.load_scenario(bad)
    except InputError as exc:
        assert "missing required key" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("malformed scenario must raise InputError")


def test_missing_scenario_is_reported_as_an_input_error(tmp_path):
    from shared.errors import InputError

    try:
        execution.load_scenario(tmp_path / "nope.json")
    except InputError as exc:
        assert "scenario file not found" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("missing scenario must raise InputError")


# ---- decision sufficiency -------------------------------------------------


def test_accepted_fixture_decides_accepted():
    result = run_analyze_cached("accepted")
    assert result.decision == decision.ACCEPTED
    assert result.exit_code == 0
