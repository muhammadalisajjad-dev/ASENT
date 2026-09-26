"""CAVR pipeline orchestration: P1 capture through P9 decision.

The gate short-circuits at P2 when the action is not permitted; every later
phase only runs on PERMITTED actions, and the evidence document states
explicitly which phase was reached and whether analysis was performed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cavr import (
    capability,
    capture,
    context,
    decision,
    evidence,
    observe,
    policy,
    resolve,
    sandbox,
    triggers,
)
from shared.errors import InputError

PROTOTYPE_PARAMETERS = {
    "ecosystem": "pypi (local fixtures only; no PyPI network resolution)",
    "trigger_analyzer": "cavr_ast_trigger_discovery_v1",
    "observation_backend": "cpython_audit_hooks (prototype, no native/syscall visibility)",
    "version_specifier_evaluator": "minimal subset of PEP 440",
    "sandbox_timeout_seconds": sandbox.DEFAULT_TIMEOUT,
    "llm_used": False,
}


@dataclass
class CheckResult:
    """Outcome of one full CAVR check."""

    evidence: dict
    decision: str
    exit_code: int

    @property
    def stable_digest(self) -> str:
        return evidence.stable_digest(self.evidence)


_EXIT_CODES = {
    decision.VERIFIED: 0,
    decision.RESTRICTED: 0,
    decision.BLOCKED: 2,
    decision.REJECTED: 3,
    decision.UNRESOLVED: 4,
}


def _blocked_result(
    action: capture.DependencyAction,
    requirement: policy.RequirementDecision,
) -> dict:
    """Evidence document for a P2 short-circuit (no package analysis)."""
    return evidence.build_evidence(
        action=action.as_dict(),
        requirement=requirement.as_dict(),
        package={
            "name": action.package,
            "version_spec": action.version_spec,
            "artifact_hash": None,
            "resolution": "not attempted (requirement gate blocked the action)",
        },
        project={"project_dir": action.project},
        capability_contract={"derived": False},
        triggers={"triggers": [], "analysis_performed": False},
        environments=[],
        runs=[],
        events=[],
        artifact_checks=[],
        observed=[],
        prohibited=[],
        decision=decision.BLOCKED,
        decision_reason=(
            "requirement gate blocked the dependency action before any "
            f"package analysis: {requirement.reason}"
        ),
        violations=[],
        residual_uncertainty=[
            "no package analysis was performed; this is a requirement-gate "
            "outcome, not a security verdict"
        ],
        coverage={"environments": []},
        isolation=sandbox.isolation_report(),
        prototype_parameters=PROTOTYPE_PARAMETERS,
        phase_reached="P2",
        analysis_performed=False,
    )


def run_check(
    package_dir: str | Path,
    project_dir: str | Path,
    policy_path: str | Path | None = None,
    *,
    timeout: float = sandbox.DEFAULT_TIMEOUT,
    keep_sandbox: bool = False,
) -> CheckResult:
    """Execute the CAVR vertical slice for one captured dependency action."""
    project_root = Path(project_dir)
    policy_file = Path(policy_path) if policy_path else project_root / "policy.json"

    # P2 input: the project policy.  Reading it is not package analysis.
    policy_data = policy.load_policy(policy_file)

    # P1 - normalized dependency action record.  Identity comes from the
    # requested local fixture (the captured action names the package).
    name, version_spec, _module, _identity = resolve.read_package_identity(package_dir)
    action = capture.capture_action(
        package=name,
        version_spec=version_spec,
        project=str(project_root),
        ecosystem="pypi",
        action_type="install",
        source="cli",
    )

    # P2 - requirement gate.  PERMITTED != TRUSTED.  A blocked action stops
    # here: no hashing, no trigger discovery, no execution.
    requirement = policy.evaluate_requirement(action, policy_data)
    if not requirement.permitted:
        return CheckResult(
            evidence=_blocked_result(action, requirement),
            decision=decision.BLOCKED,
            exit_code=_EXIT_CODES[decision.BLOCKED],
        )

    # P3 - minimum project context; P4 - capability contract.
    project_context = context.load_context(project_root)
    contract = capability.derive_contract(project_context)
    if contract.conflicts:
        raise InputError(
            f"capability contract has conflicting roles: {contract.conflicts}"
        )

    # P5 - exact local package fixture resolution (artifact hash, inventory,
    # declared dependency metadata).
    resolution = resolve.resolve_local_package(package_dir)

    # P6 - trigger discovery over the exact resolved artifact.
    trigger_report = triggers.discover_triggers(resolution)

    # P7 - disposable counterfactual sandbox (normal + counterfactual).
    normal_plan, counterfactual_plan = sandbox.plan_environments(trigger_report)
    runs = [
        sandbox.execute_run(
            resolution, project_context, normal_plan, timeout=timeout,
            keep_sandbox=keep_sandbox,
        ),
        sandbox.execute_run(
            resolution, project_context, counterfactual_plan, timeout=timeout,
            keep_sandbox=keep_sandbox,
        ),
    ]

    # P8 - observation aggregation.
    events = [event for run in runs for event in run.events]
    artifact_checks = [
        dict(check) for run in runs for check in run.artifact_checks
    ]
    observed = observe.observed_capabilities(events)

    # P9 - decision against the capability contract.
    verdict = decision.decide(contract, trigger_report, runs)

    document = evidence.build_evidence(
        action=action.as_dict(),
        requirement=requirement.as_dict(),
        package=resolution.as_dict(),
        project=project_context.as_dict(),
        capability_contract=contract.as_dict(),
        triggers=trigger_report.as_dict(),
        environments=[plan.as_dict() for plan in (normal_plan, counterfactual_plan)],
        runs=[run.as_dict() for run in runs],
        events=events,
        artifact_checks=artifact_checks,
        observed=observed,
        prohibited=list(contract.prohibited),
        decision=verdict.decision,
        decision_reason=verdict.reason,
        violations=list(verdict.violations),
        residual_uncertainty=list(verdict.residual_uncertainty),
        coverage=verdict.coverage,
        isolation=sandbox.isolation_report(),
        prototype_parameters=PROTOTYPE_PARAMETERS,
        phase_reached="P9",
        analysis_performed=True,
    )
    return CheckResult(
        evidence=document,
        decision=verdict.decision,
        exit_code=_EXIT_CODES[verdict.decision],
    )
