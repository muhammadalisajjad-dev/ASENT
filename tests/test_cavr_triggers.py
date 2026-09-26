"""CAVR tests: P6 security trigger discovery."""

from __future__ import annotations

from cavr import triggers

from cavr_support import components


def test_benign_fixture_has_no_triggers():
    _resolution, _context, report = components("benign")
    assert report.triggers == ()
    assert report.as_dict()["analyzer"] == "cavr_ast_trigger_discovery_v1"
    assert report.as_dict()["exhaustiveness"] == "best-effort, not exhaustive"
    assert "invoice_parser/__main__.py" in report.scanned_files


def test_triggered_fixture_trigger_frontier():
    _resolution, _context, report = components("triggered")
    assert len(report.triggers) == 1

    trigger = report.triggers[0]
    assert trigger.predicate == "CAVR_TRIGGER == 1"
    assert trigger.predicate_kind == "env_var"
    assert trigger.activatable is True
    assert trigger.activation == {"env": {"CAVR_TRIGGER": "1"}}
    assert trigger.risk == "high"
    assert "canary-secret read path" in trigger.controls
    assert "canary-sink write" in trigger.controls
    assert trigger.source_file == "invoice_turbo/__main__.py"
    assert trigger.line > 0
    assert report.unexercisable == ()


def test_unresolved_fixture_trigger_is_high_risk_and_unactivatable():
    _resolution, _context, report = components("unresolved")
    assert len(report.triggers) == 1

    trigger = report.triggers[0]
    assert trigger.predicate_kind == "host_identity"
    assert "host-identity gate" in trigger.predicate
    assert trigger.activatable is False
    assert trigger.activation is None
    assert trigger.risk == "high"
    assert "canary-secret read path" in trigger.controls
    assert report.unexercisable == (trigger,)


def test_merged_activations_only_include_activatable_triggers():
    _resolution, _context, report = components("triggered")
    assert report.activations == {"env": {"CAVR_TRIGGER": "1"}}

    _r2, _c2, unresolved = components("unresolved")
    assert unresolved.activations == {}


def test_trigger_report_serialization_shape():
    _resolution, _context, report = components("triggered")
    document = report.as_dict()
    assert set(document) >= {
        "scanned_files",
        "analyzer",
        "exhaustiveness",
        "triggers",
    }
    entry = document["triggers"][0]
    assert set(entry) == {
        "source_file",
        "line",
        "predicate",
        "predicate_kind",
        "controls",
        "risk",
        "activatable",
        "activation",
        "notes",
    }
