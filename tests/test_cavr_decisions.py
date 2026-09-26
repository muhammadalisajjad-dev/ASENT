"""CAVR tests: P9 decision, evidence serialization, deterministic repetition."""

from __future__ import annotations

import json

from cavr import decision, evidence

from cavr_support import ground_truth, run_check_cached, run_check_fresh


def _events_by_run(document, label):
    return [e for e in document["events"] if e["run"] == label]


def test_benign_fixture_is_verified():
    result = run_check_cached("benign")
    document = result.evidence

    assert result.decision == decision.VERIFIED
    assert document["decision"] == "VERIFIED"
    assert document["requirement"]["decision"] == "PERMITTED"
    assert document["analysis_performed"] is True
    assert document["phase_reached"] == "P9"
    assert document["violations"] == []
    assert document["observed_capabilities"] == ["FILE_READ", "FILE_WRITE"]
    assert set(document["observed_capabilities"]).isdisjoint(
        document["capability_contract"]["prohibited"]
    )
    assert len(document["execution_runs"]) == 2
    assert document["coverage"]["counterfactual_executed"] is True
    assert "stay inside the declared contract" in document["decision_reason"]


def test_triggered_fixture_is_rejected_only_via_counterfactual():
    """Ordinary execution looks benign; counterfactual activation exposes it."""
    result = run_check_cached("triggered")
    document = result.evidence

    assert result.decision == decision.REJECTED
    assert document["decision"] == "REJECTED"

    normal = _events_by_run(document, "normal")
    counterfactual = _events_by_run(document, "counterfactual")

    # Ordinary run: no synthetic trigger, no secret access observed.
    assert not any(e.get("target_class") == "canary_secret" for e in normal)
    # Counterfactual run: canary read observed -> prohibited capability.
    secret_reads = [
        e for e in counterfactual if e.get("target_class") == "canary_secret"
    ]
    assert len(secret_reads) == 1
    assert secret_reads[0]["kind"] == "FILE_READ"

    assert "SECRET_ACCESS" in document["observed_capabilities"]
    assert "SECRET_ACCESS" in document["prohibited_capabilities"]
    capability_violations = [
        v
        for v in document["violations"]
        if v["type"] == "prohibited_capability_observed"
    ]
    assert capability_violations
    assert capability_violations[0]["capability"] == "SECRET_ACCESS"
    assert capability_violations[0]["observed_in"] == ["counterfactual"]

    sink_violations = [
        v
        for v in document["violations"]
        if v["type"] == "canary_written_to_designated_sink"
    ]
    assert sink_violations and sink_violations[0]["evidence"]["passed"] is True

    # The activation that made this visible is recorded in coverage.
    assert document["triggers"]["triggers"][0]["predicate"] == "CAVR_TRIGGER == 1"
    assert (
        document["coverage"]["activations_exercised_in_counterfactual"]
        == ["CAVR_TRIGGER"]
    )


def test_unresolved_fixture_is_unresolved():
    result = run_check_cached("unresolved")
    document = result.evidence

    assert result.decision == decision.UNRESOLVED
    assert document["decision"] == "UNRESOLVED"
    assert document["violations"] == []
    assert document["coverage"]["unactivatable_triggers"] == 1
    assert any(
        "could not be exercised" in note
        for note in document["residual_uncertainty"]
    )
    assert "host-identity gate" in document["decision_reason"]
    assert document["coverage"]["activatable_triggers"] == 0


def test_ground_truth_matches_actual_decisions():
    for name in ("benign", "triggered", "unresolved"):
        truth = ground_truth(name)
        result = run_check_cached(name)
        assert result.decision == truth["expected_decision"], name
        if "expected_violation_capability" in truth:
            capabilities = {
                v["capability"] for v in result.evidence["violations"]
            }
            assert truth["expected_violation_capability"] in capabilities


def test_evidence_document_is_json_serializable_and_complete():
    document = run_check_cached("triggered").evidence
    round_tripped = json.loads(json.dumps(document))

    assert round_tripped == document
    assert document["schema_version"] == evidence.SCHEMA_VERSION
    assert document["module"] == "CAVR"
    assert document["run_id"]
    assert document["generated_at"]
    assert document["package"]["artifact_hash"]
    assert document["package"]["name"] == "invoice-turbo"
    assert document["requirement"]["decision"] == "PERMITTED"
    assert "Extract text from invoice PDFs" in document["project"]["intent"]
    assert document["capability_contract"]["required"]
    assert document["capability_contract"]["prohibited"]
    assert document["triggers"]["triggers"]
    assert [env["label"] for env in document["environments"]] == [
        "normal",
        "counterfactual",
    ]
    assert document["execution_runs"]
    assert document["events"]
    assert document["observed_capabilities"]
    assert document["prohibited_capabilities"]
    assert document["violations"]
    assert document["decision"] in decision.DECISIONS
    assert document["decision_reason"]
    assert document["residual_uncertainty"]
    assert document["isolation"]["mechanism"]
    assert document["isolation"]["trusted_project_executed"] is False
    assert document["runtime"]["python"]
    assert document["prototype_parameters"]["llm_used"] is False
    assert document["bounded_claim"]


def test_blocked_evidence_is_serializable_and_flagged():
    from cavr import pipeline

    from cavr_support import fixture_paths

    package_dir, project_dir = fixture_paths("benign")
    foreign_policy = fixture_paths("triggered")[1] / "policy.json"
    document = pipeline.run_check(package_dir, project_dir, foreign_policy).evidence
    round_tripped = json.loads(json.dumps(document))
    assert round_tripped == document
    assert document["decision"] == "BLOCKED"
    assert document["phase_reached"] == "P2"


def test_repeated_runs_produce_identical_stable_digest():
    # Two genuinely independent pipeline executions of the same fixture
    # (one from the cross-test cache, one fresh) must agree on the
    # non-volatile analysis content.
    first = run_check_cached("benign")
    second = run_check_fresh("benign")

    assert first.evidence["run_id"] != second.evidence["run_id"]
    assert first.stable_digest == second.stable_digest
    assert (
        first.evidence["package"]["artifact_hash"]
        == second.evidence["package"]["artifact_hash"]
    )
    assert first.decision == second.decision == "VERIFIED"

    triggered_cached = run_check_cached("triggered")
    triggered_fresh = run_check_fresh("triggered")
    assert triggered_cached.stable_digest == triggered_fresh.stable_digest
    assert triggered_fresh.decision == "REJECTED"


def test_stable_digest_excludes_volatile_fields():
    document = dict(run_check_cached("benign").evidence)
    baseline = evidence.stable_digest(document)

    altered = dict(document)
    altered["run_id"] = "different-run-id"
    altered["generated_at"] = "1999-01-01T00:00:00+00:00"
    assert evidence.stable_digest(altered) == baseline

    altered = dict(document)
    altered["decision"] = "REJECTED"
    assert evidence.stable_digest(altered) != baseline


def test_summary_mentions_key_facts():
    document = run_check_cached("triggered").evidence
    text = evidence.summarize(document)
    assert "invoice-turbo 2.1.0" in text
    assert "decision:    REJECTED" in text
    assert "SECRET_ACCESS" in text
    assert "digest:      sha256:" in text


def test_write_evidence_roundtrip(tmp_path):
    document = run_check_cached("benign").evidence
    target = evidence.write_evidence(document, tmp_path / "nested" / "evidence.json")
    loaded = evidence.load_evidence(target)
    assert loaded == document
    assert target.read_text(encoding="utf-8").strip().endswith("}")


def test_decisions_are_from_the_declared_vocabulary():
    assert decision.DECISIONS == (
        "VERIFIED",
        "RESTRICTED",
        "REJECTED",
        "UNRESOLVED",
        "BLOCKED",
    )
    assert "RESTRICTED" in decision.DECISIONS  # reserved, never fabricated
