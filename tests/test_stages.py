"""Stage-level regression tests (E-G): attribution and authorization must be
separate, and the final decision must reflect both."""

from __future__ import annotations

import json


def test_e_legitimate_moved_refactor_is_preserved_after_authorization(poc_case):
    from sable.verify import verify_fixture

    result = verify_fixture(poc_case("case01_legitimate_move"))

    # Stage 1: correspondence attributes the successor from moved + structure.
    assert result.correspondence.status == "identified"
    assert result.correspondence.rule == "explicit_moved"
    assert result.correspondence.selected == "aws_s3_bucket.app_customer_records"

    # Stage 2: the obligation is independently verified on that successor.
    assert result.authorization.status == "satisfied"
    assert result.authorization.resource == result.correspondence.selected

    assert result.decision == "PRESERVED"
    assert result.expected_decision == "PRESERVED"
    assert result.achieved is True


def test_f_correct_successor_with_widened_iam_is_regressed(poc_case):
    from sable.verify import verify_fixture

    result = verify_fixture(poc_case("case02_privilege_widening"))

    # The successor itself is correctly identified from configuration evidence.
    assert result.correspondence.status == "identified"
    assert result.correspondence.selected == "aws_s3_bucket.customer_data_store"

    # ...but the authorization stage rejects the widened boundary.
    assert result.authorization.status == "violated"
    failed = {check.id for check in result.authorization.checks if check.status == "fail"}
    assert "action_widening" in failed
    assert "scope_widening" in failed

    assert result.decision == "REGRESSED"
    assert result.achieved is True


def test_g_wrong_asset_policy_yields_regressed_not_preserved(poc_case):
    from sable.verify import verify_fixture

    result = verify_fixture(poc_case("case03_wrong_binding"))

    # Attribution: the structurally supported successor is selected...
    assert result.correspondence.status == "identified"
    assert result.correspondence.selected == "aws_s3_bucket.customer_data_v2"

    # ...and the candidate carrying the valid-looking policy is NOT selected:
    # policy relationship evidence alone never decides attribution.
    by_address = {
        hypothesis.address: hypothesis for hypothesis in result.correspondence.hypotheses
    }
    policy_carrier = by_address["aws_s3_bucket.analytics_dump"]
    assert policy_carrier.signal("policy_target").score == 1.0
    assert result.correspondence.selected != "aws_s3_bucket.analytics_dump"

    # Authorization: the obligation is not preserved on the selected successor.
    assert result.authorization.status == "violated"
    failed = {check.id for check in result.authorization.checks if check.status == "fail"}
    assert "successor_binding" in failed
    bound_elsewhere = [
        binding["asset"] for binding in result.authorization.other_asset_bindings
    ]
    assert any("analytics_dump" in asset for asset in bound_elsewhere)

    assert result.decision == "REGRESSED"
    assert result.achieved is True


def test_policy_relationship_signal_is_relationship_evidence_only(poc_case):
    from sable.verify import verify_fixture

    result = verify_fixture(poc_case("case03_wrong_binding"))
    for hypothesis in result.correspondence.hypotheses:
        detail = hypothesis.signal("policy_target").detail
        # Covered or not: the signal only ever reports policy *wiring*, never
        # obligation conformance.
        assert "relationship evidence only" in detail or "no S3 allow statement" in detail
        assert "exactly the obligation action set" not in detail
    covered = next(
        hypothesis
        for hypothesis in result.correspondence.hypotheses
        if hypothesis.address == "aws_s3_bucket.analytics_dump"
    )
    assert covered.signal("policy_target").score == 1.0
    assert "authorization stage" in covered.signal("policy_target").detail


def test_unidentified_correspondence_never_runs_as_preserved(poc_case):
    from sable.verify import verify_fixture

    for name in (
        "case06_ambiguous_successors",
        "case07_conflicting_move_info",
        "case08_similar_name_resources",
    ):
        result = verify_fixture(poc_case(name))
        assert not result.correspondence.identified
        assert result.authorization.status == "not_evaluated"
        assert result.decision == "UNKNOWN"


def test_ground_truth_documents_are_consistent(poc_case):
    for name in (
        "case01_legitimate_move",
        "case02_privilege_widening",
        "case03_wrong_binding",
        "case06_ambiguous_successors",
        "case07_conflicting_move_info",
        "case08_similar_name_resources",
    ):
        truth = json.loads((poc_case(name) / "ground_truth.json").read_text(encoding="utf-8"))
        assert truth["expected_decision"] in ("PRESERVED", "REGRESSED", "UNKNOWN")
