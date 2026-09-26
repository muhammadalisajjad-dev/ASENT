"""Differential comparison: baseline vs candidate probe behavior.

Compares the trusted execution records of the two sides probe by probe and
classifies each comparison.  The trusted baseline defines the ground truth:
an obligation the baseline satisfies and the candidate does not is a
regression; a baseline failure invalidates the evidence rather than
condemning the candidate.
"""

from __future__ import annotations

from dataclasses import dataclass

from satra_rv.contract import SecurityChangeContract
from satra_rv.execution import ExecutionResult, ProbeRecord

OUTCOME_HELD = "held"
OUTCOME_REGRESSION = "regression"
OUTCOME_BASELINE_FAILED = "baseline_failed"
OUTCOME_BASELINE_FAILED_CANDIDATE_HELD = "baseline_failed_candidate_held"


@dataclass(frozen=True)
class ProbeComparison:
    """Baseline/candidate pair for one invariant."""

    invariant_id: str
    kind: str
    bound: bool
    actor: str
    method: str
    path: str
    expected_statuses: tuple[int, ...]
    baseline: ProbeRecord | None
    candidate: ProbeRecord | None
    outcome: str

    @property
    def is_regression(self) -> bool:
        return self.outcome == OUTCOME_REGRESSION

    @property
    def baseline_failed(self) -> bool:
        return self.outcome in (
            OUTCOME_BASELINE_FAILED,
            OUTCOME_BASELINE_FAILED_CANDIDATE_HELD,
        )

    def as_dict(self) -> dict:
        return {
            "invariant_id": self.invariant_id,
            "kind": self.kind,
            "bound": self.bound,
            "actor": self.actor,
            "method": self.method,
            "path": self.path,
            "expected_statuses": list(self.expected_statuses),
            "outcome": self.outcome,
            "baseline": self.baseline.as_dict() if self.baseline else None,
            "candidate": self.candidate.as_dict() if self.candidate else None,
        }


@dataclass(frozen=True)
class DifferentialResult:
    """Probe-by-probe comparison of the two sides."""

    comparisons: tuple[ProbeComparison, ...]
    execution_complete: bool

    @property
    def regressions(self) -> tuple[ProbeComparison, ...]:
        return tuple(c for c in self.comparisons if c.is_regression)

    @property
    def bound_regressions(self) -> tuple[ProbeComparison, ...]:
        return tuple(c for c in self.regressions if c.bound)

    @property
    def security_regressions(self) -> tuple[ProbeComparison, ...]:
        """Candidate regressions that matter to the decision."""
        return tuple(c for c in self.regressions if c.bound or c.kind == "deny")

    @property
    def baseline_failures(self) -> tuple[ProbeComparison, ...]:
        return tuple(c for c in self.comparisons if c.baseline_failed)

    @property
    def bound_baseline_failures(self) -> tuple[ProbeComparison, ...]:
        return tuple(c for c in self.baseline_failures if c.bound)

    def as_dict(self) -> dict:
        return {
            "execution_complete": self.execution_complete,
            "comparison_count": len(self.comparisons),
            "regression_count": len(self.regressions),
            "security_regression_count": len(self.security_regressions),
            "bound_baseline_failure_count": len(self.bound_baseline_failures),
            "comparisons": [c.as_dict() for c in self.comparisons],
        }


def _classify(baseline: ProbeRecord | None, candidate: ProbeRecord | None) -> str:
    if baseline is None or candidate is None:
        return OUTCOME_BASELINE_FAILED
    if baseline.satisfied and candidate.satisfied:
        return OUTCOME_HELD
    if baseline.satisfied and not candidate.satisfied:
        return OUTCOME_REGRESSION
    if not baseline.satisfied and candidate.satisfied:
        return OUTCOME_BASELINE_FAILED_CANDIDATE_HELD
    return OUTCOME_BASELINE_FAILED


def compare(
    contract: SecurityChangeContract,
    baseline: ExecutionResult,
    candidate: ExecutionResult,
) -> DifferentialResult:
    """Compare baseline and candidate probe records against the contract."""
    obligations = {o.invariant_id: o for o in contract.obligations}
    ordered_ids: list[str] = []
    for record in baseline.probes + candidate.probes:
        if record.invariant_id not in ordered_ids:
            ordered_ids.append(record.invariant_id)

    comparisons: list[ProbeComparison] = []
    for invariant_id in ordered_ids:
        base = baseline.probe(invariant_id)
        cand = candidate.probe(invariant_id)
        obligation = obligations.get(invariant_id)
        anchor = base or cand
        comparison = ProbeComparison(
            invariant_id=invariant_id,
            kind=(obligation.kind if obligation else (anchor.kind if anchor else "")),
            bound=obligation is not None,
            actor=anchor.actor if anchor else "",
            method=anchor.method if anchor else "",
            path=anchor.path if anchor else "",
            expected_statuses=(
                obligation.expected_statuses
                if obligation
                else (anchor.expected_statuses if anchor else ())
            ),
            baseline=base,
            candidate=cand,
            outcome=_classify(base, cand),
        )
        comparisons.append(comparison)

    execution_complete = baseline.complete and candidate.complete
    return DifferentialResult(
        comparisons=tuple(comparisons), execution_complete=execution_complete
    )
