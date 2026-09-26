"""CAVR tests: P7 disposable counterfactual sandbox and P8 observation."""

from __future__ import annotations

from pathlib import Path

from cavr import capability, observe, sandbox

from cavr_support import components, fixture_paths


def _events_for(runs, label):
    return [event for run in runs if run.label == label for event in run.events]


def test_normal_execution_uses_expected_capability_only():
    resolution, project_context, report = components("triggered")
    normal, _counterfactual = sandbox.plan_environments(report)

    assert normal.env_overrides == {}
    assert normal.plant_canary is False

    run = sandbox.execute_run(resolution, project_context, normal)
    assert run.ok, run.error
    assert run.exit_code == 0
    assert run.timed_out is False
    assert run.artifact_checks == []

    kinds = {event["kind"] for event in run.events if event["kind"] in observe.EVENT_KINDS}
    assert "FILE_READ" in kinds
    assert "FILE_WRITE" in kinds
    assert "NETWORK_CONNECT" not in kinds
    assert "PROCESS_CREATE" not in kinds

    targets = {
        event["target"]
        for event in run.events
        if event["kind"] in observe.EVENT_KINDS
    }
    assert "input/invoice_sample.txt" in targets
    assert "out/extracted.txt" in targets
    assert not any("canary" in str(target) for target in targets)
    assert observe.observed_capabilities(run.events) == [
        capability.FILE_READ,
        capability.FILE_WRITE,
    ]


def test_counterfactual_activation_reads_canary_and_fills_sink():
    resolution, project_context, report = components("triggered")
    _normal, counterfactual = sandbox.plan_environments(report)

    assert counterfactual.env_overrides == {"CAVR_TRIGGER": "1"}
    assert counterfactual.plant_canary is True
    assert counterfactual.as_dict()["synthetic_condition_present"] is True

    run = sandbox.execute_run(resolution, project_context, counterfactual)
    assert run.ok, run.error

    canary_reads = [
        event
        for event in run.events
        if event["kind"] == observe.FILE_READ
        and event["target_class"] == "canary_secret"
    ]
    assert canary_reads, "counterfactual must observe the canary-secret read"
    assert canary_reads[0]["run"] == "counterfactual"
    assert "SECRET_ACCESS" in observe.observed_capabilities(run.events)

    sink_writes = [
        event
        for event in run.events
        if event["kind"] == observe.FILE_WRITE
        and event["target"] == "out/canary_sink.txt"
    ]
    assert sink_writes, "counterfactual must observe the sink write"

    checks = run.artifact_checks
    assert checks and checks[0]["check"] == "counterfactual_canary_reached_sink"
    assert checks[0]["passed"] is True


def test_ordinary_run_differs_from_counterfactual_run():
    """The central CAVR premise: normal run != security-triggered run."""
    resolution, project_context, report = components("triggered")
    normal, counterfactual = sandbox.plan_environments(report)

    normal_run = sandbox.execute_run(resolution, project_context, normal)
    counter_run = sandbox.execute_run(resolution, project_context, counterfactual)

    def secret_reads(run):
        return [
            event
            for event in run.events
            if event.get("target_class") == "canary_secret"
        ]

    assert normal_run.ok and counter_run.ok
    assert secret_reads(normal_run) == []
    assert len(secret_reads(counter_run)) == 1
    # Both runs perform the legitimate feature behavior identically.
    for run in (normal_run, counter_run):
        targets = {
            event["target"] for event in run.events if event["kind"] == "FILE_WRITE"
        }
        assert "out/extracted.txt" in targets


def test_parent_environment_trigger_does_not_leak_into_normal_run(monkeypatch):
    """The normal environment must not contain the synthetic trigger."""
    monkeypatch.setenv("CAVR_TRIGGER", "1")
    monkeypatch.setenv("CAVR_CANARY_PATH", "/tmp/should-not-leak")

    resolution, project_context, report = components("triggered")
    normal, counterfactual = sandbox.plan_environments(report)
    normal_run = sandbox.execute_run(resolution, project_context, normal)
    counter_run = sandbox.execute_run(resolution, project_context, counterfactual)

    normal_env_events = [
        event
        for event in normal_run.events
        if event.get("target_class") == "canary_secret"
    ]
    assert normal_env_events == []
    assert normal.env_overrides == {}
    assert counterfactual.env_overrides == {"CAVR_TRIGGER": "1"}


def test_trusted_project_never_modified_by_execution():
    _, project_dir = fixture_paths("triggered")

    def snapshot(root: Path):
        return {
            str(path.relative_to(root)): (path.stat().st_size, path.read_bytes())
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    before = snapshot(project_dir)
    resolution, project_context, report = components("triggered")
    normal, counterfactual = sandbox.plan_environments(report)
    sandbox.execute_run(resolution, project_context, normal)
    sandbox.execute_run(resolution, project_context, counterfactual)
    after = snapshot(project_dir)

    assert before == after
    assert not (project_dir / "out").exists()


def test_observation_normalization_labels_targets():
    """Normalized events classify sandbox paths relative to the workdir."""
    resolution, project_context, report = components("triggered")
    _normal, counterfactual = sandbox.plan_environments(report)
    run = sandbox.execute_run(resolution, project_context, counterfactual)

    for event in run.events:
        if event["target_class"] == "sandbox":
            assert "/" in event["target"] or event["target"].endswith(
                (".txt", ".py", ".pyc")
            )
            assert not Path(event["target"]).is_absolute()
    classes = {event["target_class"] for event in run.events}
    assert {"project_input", "package_source", "sandbox", "canary_secret"} <= classes


def test_observed_capabilities_order_is_deterministic():
    _, project_context, report = components("triggered")
    resolution = components("triggered")[0]
    _normal, counterfactual = sandbox.plan_environments(report)
    run = sandbox.execute_run(resolution, project_context, counterfactual)
    observed = observe.observed_capabilities(run.events)
    assert observed == [capability.FILE_READ, capability.FILE_WRITE, capability.SECRET_ACCESS]
    assert observe.observed_capabilities(list(reversed(run.events))) == observed


def test_isolation_report_is_honest():
    report = sandbox.isolation_report()
    assert report["trusted_project_executed"] is False
    assert report["package_copied_into_sandbox"] is True
    assert report["mechanism"] in ("disposable_tempdir_subprocess", "container", "podman")
    assert "process/directory/environment isolation only" in report["boundary"] or (
        report["mechanism"] != "disposable_tempdir_subprocess"
    )
    assert "no real malware" in report["fixtures"]
