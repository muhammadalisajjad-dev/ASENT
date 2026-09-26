"""Decision: ACCEPTED | REJECTED | INCONCLUSIVE.

Deterministic, evidence-backed rules evaluated in fixed order:

1. incomplete execution (setup fault, login failure, probe fault, timeout)
   -> INCONCLUSIVE: no classifiable evidence,
2. no localized security-sensitive region -> INCONCLUSIVE: nothing to
   review, contract cannot be bound,
3. no bound security-denial obligation -> INCONCLUSIVE: the change is not
   covered by a trusted security invariant,
4. the trusted baseline fails a bound obligation -> INCONCLUSIVE: the
   ground truth itself is invalid,
5. the candidate regresses any bound obligation, or any security denial
   (bound or not) -> REJECTED,
6. otherwise -> ACCEPTED.

ACCEPTED never means "provably safe": it means the declared obligations were
witnessed on both sides by real execution.
"""

from __future__ import annotations

from dataclasses import dataclass

from satra_rv.contract import SecurityChangeContract
from satra_rv.differential import DifferentialResult
from satra_rv.localization import LocalizationResult

ACCEPTED = "ACCEPTED"
REJECTED = "REJECTED"
INCONCLUSIVE = "INCONCLUSIVE"

DECISIONS = (ACCEPTED, REJECTED, INCONCLUSIVE)

_BASE_UNCERTAINTY = (
    "security-change localization is a bounded static heuristic over the "
    "changed Flask region, not complete program analysis "
    "(satra_rv_security_localizer_v1)",
    "the trusted dictionary covers Python/Flask authorization and ownership "
    "behavior only; other security families are out of scope for this slice",
    "the candidate application code is executed in a subprocess with a "
    "timeout, not in a hardened sandbox; no network isolation is claimed",
    "the decision is deterministic and independent of any language model; no "
    "dynamically generated tests were used in this slice",
    "SATRA-RV observes HTTP behavior only: it does not prove the absence of "
    "latent authorization defects outside the probed obligations",
)


@dataclass(frozen=True)
class DecisionResult:
    """Evidence-backed bounded decision with explicit uncertainty."""

    decision: str
    reason: str
    findings: tuple[dict, ...]
    residual_uncertainty: tuple[str, ...]
    coverage: dict

    def as_dict(self) -> dict:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "findings": [dict(f) for f in self.findings],
            "residual_uncertainty": list(self.residual_uncertainty),
            "coverage": dict(self.coverage),
        }


def _coverage(
    localization: LocalizationResult,
    contract: SecurityChangeContract,
    differential: DifferentialResult,
) -> dict:
    return {
        "regions_localized": len(localization.regions),
        "contract_id": contract.contract_id,
        "obligations_bound": len(contract.obligations),
        "security_denials_bound": len(contract.security_obligations),
        "required_behavior_bound": len(contract.functionality_obligations),
        "probes_compared": len(differential.comparisons),
        "execution_complete": differential.execution_complete,
        "regressions": len(differential.regressions),
        "security_regressions": len(differential.security_regressions),
        "bound_baseline_failures": len(differential.bound_baseline_failures),
    }


def _incomplete_reason(differential: DifferentialResult) -> str:
    incomplete = [
        c
        for c in differential.comparisons
        if (c.baseline and not c.baseline.satisfied and c.baseline.outcome not in ("satisfied", "violated"))
        or (c.candidate and not c.candidate.satisfied and c.candidate.outcome not in ("satisfied", "violated"))
    ]
    details = ", ".join(sorted({c.invariant_id for c in incomplete})) or "probe records missing"
    return (
        "deterministic probe execution did not complete with classifiable "
        f"outcomes ({details}); evidence is insufficient to decide"
    )


def decide(
    contract: SecurityChangeContract,
    localization: LocalizationResult,
    differential: DifferentialResult,
) -> DecisionResult:
    """Derive the SATRA-RV decision from contract, localization and diff."""
    uncertainty = list(_BASE_UNCERTAINTY)
    coverage = _coverage(localization, contract, differential)

    if not differential.execution_complete:
        uncertainty.append("candidate or baseline execution was incomplete")
        return DecisionResult(
            decision=INCONCLUSIVE,
            reason=_incomplete_reason(differential),
            findings=(),
            residual_uncertainty=tuple(uncertainty),
            coverage=coverage,
        )

    if not localization.regions:
        return DecisionResult(
            decision=INCONCLUSIVE,
            reason=(
                "no security-sensitive change could be localized in the "
                "candidate; there is no Security Change Contract to check "
                "and therefore no sufficient evidence to decide"
            ),
            findings=(),
            residual_uncertainty=tuple(uncertainty),
            coverage=coverage,
        )

    if not contract.security_obligations:
        return DecisionResult(
            decision=INCONCLUSIVE,
            reason=(
                "the localized security-sensitive change is not covered by "
                "any trusted security-denial invariant; evidence is "
                "insufficient to decide"
            ),
            findings=(),
            residual_uncertainty=tuple(uncertainty),
            coverage=coverage,
        )

    baseline_failures = differential.bound_baseline_failures
    if baseline_failures:
        detail = "; ".join(
            f"{c.invariant_id} expected {list(c.expected_statuses)} "
            f"got {c.baseline.status if c.baseline else None}"
            for c in baseline_failures
        )
        uncertainty.append("trusted baseline did not satisfy its own contract")
        return DecisionResult(
            decision=INCONCLUSIVE,
            reason=(
                "trusted baseline fails bound obligation(s), so the ground "
                f"truth is invalid: {detail}"
            ),
            findings=(),
            residual_uncertainty=tuple(uncertainty),
            coverage=coverage,
        )

    findings: list[dict] = []
    for comparison in differential.regressions:
        if not (comparison.bound or comparison.kind == "deny"):
            uncertainty.append(
                f"unbound non-security regression observed: "
                f"{comparison.invariant_id}"
            )
            continue
        findings.append(
            {
                "type": (
                    "security_regression"
                    if comparison.kind == "deny"
                    else "functionality_regression"
                ),
                "invariant_id": comparison.invariant_id,
                "kind": comparison.kind,
                "bound": comparison.bound,
                "actor": comparison.actor,
                "method": comparison.method,
                "path": comparison.path,
                "expected_statuses": list(comparison.expected_statuses),
                "baseline_status": comparison.baseline.status
                if comparison.baseline
                else None,
                "candidate_status": comparison.candidate.status
                if comparison.candidate
                else None,
                "candidate_outcome": comparison.candidate.outcome
                if comparison.candidate
                else None,
            }
        )

    if findings:
        parts = [
            f"{f['invariant_id']} ({f['method']} {f['path']} as {f['actor']}) "
            f"expected {f['expected_statuses']} baseline={f['baseline_status']} "
            f"candidate={f['candidate_status']}"
            for f in findings
        ]
        security = sum(1 for f in findings if f["type"] == "security_regression")
        return DecisionResult(
            decision=REJECTED,
            reason=(
                f"candidate regresses {len(findings)} declared obligation(s) "
                f"satisfied by the trusted baseline ({security} security): "
                + "; ".join(parts)
            ),
            findings=tuple(findings),
            residual_uncertainty=tuple(uncertainty),
            coverage=coverage,
        )

    satisfied = differential.comparisons
    return DecisionResult(
        decision=ACCEPTED,
        reason=(
            "candidate satisfies all "
            f"{len(contract.obligations)} bound obligation(s) of the Security "
            f"Change Contract ({len(contract.security_obligations)} security "
            f"denials, {len(contract.functionality_obligations)} required "
            f"behaviors) as witnessed by {len(satisfied)} deterministic probe "
            "comparison(s); no regression observed against the trusted baseline"
        ),
        findings=(),
        residual_uncertainty=tuple(uncertainty),
        coverage=coverage,
    )
