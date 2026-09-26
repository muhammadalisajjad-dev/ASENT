"""CAVR tests: P1 capture, P2 requirement gate, P3 context, P4 contract, P5 resolution."""

from __future__ import annotations

import shutil

import pytest

from cavr import capability, capture, context, policy, resolve
from shared.errors import InputError

from cavr_support import fixture_paths, ground_truth


# ---- P1 action capture --------------------------------------------------


def test_action_capture_records_normalized_dependency_action():
    action = capture.capture_action(
        package="invoice-parser",
        version_spec="==1.0.0",
        project="poc/project",
        source="cli",
    )
    record = action.as_dict()
    assert record["ecosystem"] == "pypi"
    assert record["package"] == "invoice-parser"
    assert record["version_spec"] == "==1.0.0"
    assert record["action_type"] == "install"
    assert record["project"] == "poc/project"
    assert record["source"] == "cli"
    assert record["run_id"] and len(record["run_id"]) >= 8
    assert record["timestamp"]


def test_action_capture_rejects_unsupported_values():
    with pytest.raises(InputError):
        capture.capture_action(package="", version_spec="1.0", project="x")
    with pytest.raises(InputError):
        capture.capture_action(
            package="p", version_spec="1.0", project="x", ecosystem="npm"
        )
    with pytest.raises(InputError):
        capture.capture_action(
            package="p", version_spec="1.0", project="x", source="made-up"
        )


# ---- P2 requirement gate ------------------------------------------------


def test_requirement_gate_permits_fixture1_dependency():
    action = capture.capture_action(
        package="invoice-parser", version_spec="1.0.0", project="proj"
    )
    gate = policy.evaluate_requirement(
        action, {"allowed_dependencies": {"invoice-parser": "==1.0.0"}}
    )
    assert gate.decision == policy.PERMITTED
    assert gate.permitted
    assert gate.matched_rule is not None
    assert "PERMITTED" in gate.as_dict()["decision"]
    assert "not trusted" in gate.as_dict()["note"]


def test_requirement_gate_blocks_unknown_package():
    action = capture.capture_action(
        package="invoice-turbo", version_spec="2.1.0", project="proj"
    )
    gate = policy.evaluate_requirement(
        action, {"allowed_dependencies": {"invoice-parser": "==1.0.0"}}
    )
    assert gate.decision == policy.BLOCK
    assert not gate.permitted
    assert "not listed" in gate.reason


def test_requirement_gate_blocks_wrong_version():
    action = capture.capture_action(
        package="invoice-parser", version_spec="1.0.1", project="proj"
    )
    gate = policy.evaluate_requirement(
        action, {"allowed_dependencies": {"invoice-parser": "==1.0.0"}}
    )
    assert gate.decision == policy.BLOCK
    assert "does not satisfy" in gate.reason


def test_requirement_gate_blocks_unknown_policy_file(tmp_path):
    with pytest.raises(InputError):
        policy.load_policy(tmp_path / "missing.json")


def test_blocked_action_stops_before_package_analysis():
    from cavr import pipeline

    package_dir, project_dir = fixture_paths("triggered")
    foreign_policy = fixture_paths("benign")[1] / "policy.json"
    result = pipeline.run_check(package_dir, project_dir, foreign_policy)
    document = result.evidence

    assert result.decision == "BLOCKED"
    assert document["requirement"]["decision"] == "BLOCK"
    assert document["analysis_performed"] is False
    assert document["phase_reached"] == "P2"
    # No hashing, no trigger discovery, no execution happened.
    assert document["package"]["artifact_hash"] is None
    assert document["triggers"]["triggers"] == []
    assert document["events"] == []
    assert document["execution_runs"] == []
    assert document["environments"] == []


# ---- P3 project context -------------------------------------------------


def test_project_context_extracts_intent_requirements_imports():
    _, project_dir = fixture_paths("benign")
    project_context = context.load_context(project_dir)
    assert "Extract text from invoice PDFs" in project_context.intent
    assert project_context.intent_source == "README.md"
    assert "invoice-parser==1.0.0" in project_context.requirements
    assert "invoice_parser" in project_context.imports
    assert project_context.runtime_input_dirs == ("input",)


def test_project_context_requires_intent_declaration(tmp_path):
    with pytest.raises(InputError):
        context.load_context(tmp_path)


# ---- P4 capability contract ---------------------------------------------


def test_capability_contract_reflects_declared_intent():
    _, project_dir = fixture_paths("benign")
    contract = capability.derive_contract(context.load_context(project_dir))

    assert contract.required == (capability.FILE_READ, capability.FILE_WRITE)
    for banned in (
        capability.NETWORK_CONNECT,
        capability.PROCESS_CREATE,
        capability.SECRET_ACCESS,
    ):
        assert banned in contract.prohibited
    assert contract.conflicts == ()
    assert contract.derivation == "deterministic_intent_rules_v1"
    evidence_texts = " ".join(rule.evidence for rule in contract.rules)
    assert "Extract text from invoice PDFs" in evidence_texts
    rule_ids = {rule.rule_id for rule in contract.rules}
    assert "intent_document_read" in rule_ids
    assert "intent_result_store" in rule_ids
    assert "baseline_least_privilege" in rule_ids


def test_capability_contract_without_justification_prohibits_everything():
    tmp = capability.derive_contract(
        context.ProjectContext(
            project_dir="x",
            intent="A helper utility.",
            intent_source="README.md",
            requirements=(),
            imports=(),
            runtime_input_dirs=(),
        )
    )
    assert tmp.required == ()
    assert set(tmp.prohibited) == set(capability.CAPABILITIES)


# ---- P5 package resolution ----------------------------------------------


def test_resolution_records_identity_hash_and_metadata():
    package_dir, _ = fixture_paths("benign")
    resolved = resolve.resolve_local_package(package_dir)
    assert resolved.name == "invoice-parser"
    assert resolved.version == "1.0.0"
    assert resolved.module == "invoice_parser"
    assert len(resolved.artifact_hash) == 64
    assert set(resolved.artifact_hash) <= set("0123456789abcdef")
    assert resolved.dependencies == ("pdfmini==0.4.2",)
    assert resolved.transitive_dependencies == ("_textbuf==1.0.0",)
    assert any(entry["path"] == "metadata.json" for entry in resolved.files)
    assert resolved.as_dict()["declared_only"] is True


def test_artifact_hash_is_deterministic():
    package_dir, _ = fixture_paths("benign")
    first = resolve.resolve_local_package(package_dir)
    second = resolve.resolve_local_package(package_dir)
    assert first.artifact_hash == second.artifact_hash
    assert first.files == second.files


def test_artifact_hash_changes_with_content(tmp_path):
    package_dir, _ = fixture_paths("benign")
    copy = tmp_path / "package"
    shutil.copytree(package_dir, copy)
    baseline = resolve.resolve_local_package(copy).artifact_hash

    # identical copy hashes the same
    assert resolve.resolve_local_package(copy).artifact_hash == baseline

    target = copy / "invoice_parser" / "extract.py"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8"
    )
    tampered = resolve.resolve_local_package(copy)
    assert tampered.artifact_hash != baseline


def test_resolution_requires_metadata(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(InputError):
        resolve.resolve_local_package(tmp_path / "empty")


def test_ground_truth_files_declare_expected_outcomes():
    for name in ("benign", "triggered", "unresolved"):
        truth = ground_truth(name)
        assert truth["expected_decision"] in (
            "VERIFIED",
            "REJECTED",
            "UNRESOLVED",
        )
        assert truth["requirement_expected"] == "PERMITTED"
