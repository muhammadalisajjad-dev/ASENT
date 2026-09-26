"""P9 - decision: compare observed behavior against the capability contract.

Outcomes:

* VERIFIED    - observed behavior stays inside the project-specific contract
                and all discovered triggers were exercised or benign.
* RESTRICTED  - reserved; this slice never emits it (no narrower capability
                policy is genuinely enforced yet).
* REJECTED    - a prohibited capability was observed (including under the
                deliberately activated counterfactual condition).
* UNRESOLVED  - a high-risk condition could not be meaningfully exercised, or
                the sandbox analysis could not complete.
* BLOCKED     - P2 terminal state: the requirement gate refused the action
                before any package analysis (not a security verdict).

"Executed once without bad behavior" is never sufficient: counterfactual
coverage is part of the decision inputs.
"""

from __future__ import annotations

from dataclasses import dataclass

from cavr.capability import CapabilityContract
from cavr.observe import SECRET_ACCESS, event_capability, observed_capabilities
from cavr.sandbox import RunResult
from cavr.triggers import TriggerReport

VERIFIED = "VERIFIED"
RESTRICTED = "RESTRICTED"
REJECTED = "REJECTED"
UNRESOLVED = "UNRESOLVED"
BLOCKED = "BLOCKED"

DECISIONS = (VERIFIED, RESTRICTED, REJECTED, UNRESOLVED, BLOCKED)

_BASE_UNCERTAINTY = (
    "static trigger discovery is best-effort and not exhaustive "
    "(cavr_ast_trigger_discovery_v1)",
    "observation uses CPython audit hooks: activity below the interpreter "
    "(native code, direct syscalls) is not visible",
    "version specifier evaluation is a minimal subset of PEP 440",
    "declared dependency metadata was recorded but not resolved or executed "
    "(no PyPI network resolution in this slice)",
    "isolation is process/disposable-directory based; no container runtime "
    "was available to confine the sandbox",
)


@dataclass(frozen=True)
class DecisionResult:
    """Evidence-backed bounded decision with explicit uncertainty."""

    decision: str
    reason: str
    violations: tuple[dict, ...]
    residual_uncertainty: tuple[str, ...]
    coverage: dict

    def as_dict(self) -> dict:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "violations": [dict(v) for v in self.violations],
            "residual_uncertainty": list(self.residual_uncertainty),
            "coverage": dict(self.coverage),
        }


def _coverage(report: TriggerReport, runs: list[RunResult]) -> dict:
    exercised = []
    counterfactual = next((r for r in runs if r.label == "counterfactual"), None)
    if counterfactual is not None:
        exercised = sorted(report.activations.get("env", {}))
    return {
        "environments": [run.label for run in runs],
        "activatable_triggers": sum(1 for t in report.triggers if t.activatable),
        "unactivatable_triggers": sum(1 for t in report.triggers if not t.activatable),
        "activations_exercised_in_counterfactual": exercised,
        "counterfactual_executed": counterfactual is not None
        and counterfactual.ok,
    }


def decide(
    contract: CapabilityContract,
    report: TriggerReport,
    runs: list[RunResult],
) -> DecisionResult:
    """Derive the CAVR decision from contract, triggers and observed runs."""
    all_events = [event for run in runs for event in run.events]
    capabilities = observed_capabilities(all_events)
    prohibited = set(contract.prohibited)
    coverage = _coverage(report, runs)
    uncertainty: list[str] = list(_BASE_UNCERTAINTY)

    failed_runs = [run for run in runs if not run.ok]
    if failed_runs:
        details = "; ".join(
            f"{run.label}: {run.error or f'exit code {run.exit_code}'}"
            for run in failed_runs
        )
        for run in failed_runs:
            uncertainty.append(f"sandbox run '{run.label}' did not complete cleanly")
        return DecisionResult(
            decision=UNRESOLVED,
            reason=f"security analysis could not complete: {details}",
            violations=(),
            residual_uncertainty=tuple(uncertainty),
            coverage=coverage,
        )

    violations: list[dict] = []
    for capability in sorted(prohibited):
        hits = [event for event in all_events if event_capability(event) == capability]
        if hits:
            runs_with = sorted({hit["run"] for hit in hits})
            violations.append(
                {
                    "type": "prohibited_capability_observed",
                    "capability": capability,
                    "observed_in": runs_with,
                    "evidence": dict(hits[0]),
                    "occurrences": len(hits),
                }
            )

    for run in runs:
        for check in run.artifact_checks:
            if check.get("passed"):
                violations.append(
                    {
                        "type": "canary_written_to_designated_sink",
                        "capability": SECRET_ACCESS,
                        "observed_in": [run.label],
                        "evidence": dict(check),
                    }
                )

    external_reads = [
        event
        for event in all_events
        if event["kind"] == "FILE_READ" and event["target_class"] == "external"
    ]
    if external_reads:
        violations.append(
            {
                "type": "unapproved_external_file_read",
                "capability": "FILE_READ",
                "observed_in": sorted({e["run"] for e in external_reads}),
                "evidence": dict(external_reads[0]),
                "occurrences": len(external_reads),
            }
        )

    unexercisable = list(report.unexercisable)
    if violations:
        parts = []
        for violation in violations:
            part = (
                f"{violation['capability']} observed in "
                f"{','.join(violation['observed_in'])}"
                f" ({violation['type']})"
            )
            if part not in parts:
                parts.append(part)
        return DecisionResult(
            decision=REJECTED,
            reason=(
                "observed behavior violates the project capability contract: "
                + "; ".join(parts)
            ),
            violations=tuple(violations),
            residual_uncertainty=tuple(uncertainty),
            coverage=coverage,
        )

    if unexercisable:
        for trigger in unexercisable:
            uncertainty.append(
                f"high-risk condition could not be exercised: "
                f"{trigger.source_file}:{trigger.line} {trigger.predicate} "
                f"(kind={trigger.predicate_kind}, risk={trigger.risk})"
            )
        listed = "; ".join(
            f"{t.source_file}:{t.line} {t.predicate}" for t in unexercisable
        )
        return DecisionResult(
            decision=UNRESOLVED,
            reason=(
                "a security-sensitive condition could not be meaningfully "
                f"analyzed or activated in the sandbox: {listed}"
            ),
            violations=(),
            residual_uncertainty=tuple(uncertainty),
            coverage=coverage,
        )

    if not coverage["counterfactual_executed"]:
        uncertainty.append("counterfactual environment did not complete")
        return DecisionResult(
            decision=UNRESOLVED,
            reason="counterfactual coverage missing; cannot bound the decision",
            violations=(),
            residual_uncertainty=tuple(uncertainty),
            coverage=coverage,
        )

    observed = ", ".join(capabilities) or "none"
    return DecisionResult(
        decision=VERIFIED,
        reason=(
            "observed capabilities ("
            + observed
            + ") stay inside the declared contract in both normal and "
            "counterfactual execution; no prohibited capability observed"
        ),
        violations=(),
        residual_uncertainty=tuple(uncertainty),
        coverage=coverage,
    )
