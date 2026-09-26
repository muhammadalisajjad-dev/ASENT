"""SATRA-RV tests: M1 capture, M2 localization, M3 contract, M4 dictionary."""

from __future__ import annotations

import shutil

from satra_rv import capture, dictionary, localization
from satra_rv.contract import build_contract
from satra_rv.localization import FAMILY_AUTHORIZATION
from satra_support import fixture_paths


# ---- M1 capture -----------------------------------------------------------


def test_capture_identifies_the_changed_flask_file():
    baseline, candidate, _, ground_truth = fixture_paths("rejected")
    diff = capture.capture_diff(baseline, candidate)

    assert diff.changed_paths == tuple(ground_truth["expected_changed_files"])
    (change,) = diff.changed_files
    assert change.change_type == "modified"
    assert change.text is True
    assert diff.baseline_id != diff.candidate_id
    # The actual authorization predicate change is present in the real diff.
    assert "invoice.status == \"draft\"" in change.unified_diff
    assert change.removed_line_numbers, "baseline ownership line must be removed"
    assert change.changed_line_numbers, "candidate ownership line must be added"


def test_capture_reports_no_changes_for_identical_trees(tmp_path):
    baseline, _, _, _ = fixture_paths("accepted")
    copy = tmp_path / "same"
    shutil.copytree(baseline, copy)

    diff = capture.capture_diff(baseline, copy)
    assert diff.changed_files == ()
    assert diff.baseline_id == diff.candidate_id


def test_capture_changed_lines_exclude_unchanged_context():
    baseline, candidate, _, _ = fixture_paths("rejected")
    diff = capture.capture_diff(baseline, candidate)
    (change,) = diff.changed_files
    removed = set(change.removed_line_numbers)
    # Unchanged context (module imports) must not be reported as changed.
    import_lines = {
        line_no
        for line_no, text in enumerate(
            (baseline / "app.py").read_text(encoding="utf-8").splitlines(), start=1
        )
        if text.startswith("from flask import")
    }
    assert import_lines
    assert not (removed & import_lines)


# ---- M2 localization ------------------------------------------------------


def test_localization_maps_the_change_to_the_ownership_route():
    baseline, candidate, _, ground_truth = fixture_paths("rejected")
    diff = capture.capture_diff(baseline, candidate)
    result = localization.localize(diff)

    assert result.regions, "the authorization change must be localized"
    primary = result.primary
    assert primary is not None
    assert primary.route == ground_truth["expected_localized_route"]
    assert primary.method == "GET"
    assert primary.security_family == FAMILY_AUTHORIZATION
    assert primary.confidence_label == "high"
    assert any("ownership comparison" in signal for signal in primary.signals)
    assert primary.changed_lines


def test_localization_prefers_a_route_bearing_region():
    baseline, candidate, _, ground_truth = fixture_paths("accepted")
    diff = capture.capture_diff(baseline, candidate)
    result = localization.localize(diff)

    assert result.regions
    primary = result.primary
    assert primary is not None
    assert primary.route == ground_truth["expected_localized_route"]
    functions = {region.function for region in result.regions}
    assert "_require_owner" in functions, "the factored guard must be localized"


def test_localization_finds_nothing_for_a_non_security_change():
    baseline, candidate, _, _ = fixture_paths("inconclusive")
    diff = capture.capture_diff(baseline, candidate)
    result = localization.localize(diff)

    assert diff.changed_paths == ("formatting.py",)
    assert result.regions == ()
    assert result.primary is None


# ---- M3 contract ----------------------------------------------------------


def test_contract_binds_trusted_invariants_before_execution():
    baseline, candidate, _, ground_truth = fixture_paths("rejected")
    diff = capture.capture_diff(baseline, candidate)
    result = localization.localize(diff)
    change_contract = build_contract(result.primary)

    assert change_contract.declared_before_execution is True
    assert change_contract.scope["route"] == ground_truth["expected_localized_route"]
    assert len(change_contract.obligations) == len(dictionary.INVARIANTS)
    assert len(change_contract.security_obligations) == 3
    assert len(change_contract.functionality_obligations) == 2
    assert set(change_contract.obligation_ids()) == {
        inv.id for inv in dictionary.INVARIANTS
    }
    assert change_contract.dictionary_version == dictionary.DICTIONARY_VERSION


def test_contract_id_is_deterministic_for_the_same_region():
    baseline, candidate, _, _ = fixture_paths("rejected")
    diff = capture.capture_diff(baseline, candidate)
    result = localization.localize(diff)

    first = build_contract(result.primary)
    second = build_contract(result.primary)
    assert first.contract_id == second.contract_id
    assert len(first.contract_id) == 64


def test_contract_without_a_region_is_empty_and_says_so():
    change_contract = build_contract(None)

    assert change_contract.scope["localized"] is False
    assert change_contract.obligations == ()
    assert change_contract.security_obligations == ()
    assert any("no security-sensitive region" in note for note in change_contract.binding_notes)


# ---- M4 dictionary --------------------------------------------------------


def test_dictionary_is_unique_typed_and_bounded():
    ids = [inv.id for inv in dictionary.INVARIANTS]
    assert len(ids) == len(set(ids))
    for inv in dictionary.INVARIANTS:
        assert inv.family == dictionary.FAMILY_AUTHORIZATION
        assert inv.kind in (dictionary.KIND_DENY, dictionary.KIND_ALLOW)
        assert inv.route.startswith("/")
        assert inv.obligation and inv.rationale
        assert inv.expected_statuses
        if inv.kind == dictionary.KIND_DENY:
            assert all(status in (401, 403) for status in inv.expected_statuses)
        else:
            assert all(200 <= status < 300 for status in inv.expected_statuses)
        assert inv.probe.path_template.startswith("/")


def test_dictionary_routes_match_the_localized_flask_route():
    baseline, candidate, _, ground_truth = fixture_paths("rejected")
    diff = capture.capture_diff(baseline, candidate)
    primary = localization.localize(diff).primary
    assert primary is not None
    bound = dictionary.invariants_for_route(primary.route)
    assert {inv.id for inv in bound} == {
        inv.id for inv in dictionary.INVARIANTS
    }
    assert primary.route == ground_truth["expected_localized_route"]
