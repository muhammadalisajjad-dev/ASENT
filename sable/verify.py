"""End-to-end SABLE verification of a baseline/candidate fixture pair.

The two questions are deliberately kept apart:

1. *Correspondence* (:mod:`sable.correspondence`): which candidate resource,
   if any, is the logical successor of the protected baseline asset?  Policy
   relationship evidence may support this identification.
2. *Authorization* (:mod:`sable.authorize`): does the baseline least-privilege
   obligation still hold on that successor?  This check never trusts the
   correspondence stage - "a policy covers the candidate" is never equivalent
   to "the obligation is preserved".

Only their combination yields the final decision:

    PRESERVED  correspondence identified a successor AND the obligation is
               satisfied on exactly that successor
    REGRESSED  correspondence identified a successor BUT the obligation is
               violated on it (or on the boundary that should cover it)
    UNKNOWN    correspondence did not establish a unique successor, or the
               authorization result is indeterminate/not evaluable
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from shared.model import build_project

from .authorize import AuthorizationResult, describe_boundaries, evaluate, not_evaluated
from .correspondence import CorrespondenceResult, correspond, prototype_parameters
from .obligation import BaselineModel, Obligation, bind_baseline, load_obligation, validate_baseline
from .policy import PolicyModel, build_policy_model

DECISIONS = ("PRESERVED", "REGRESSED", "UNKNOWN")


@dataclass
class VerificationResult:
    """Full evidence document for one fixture pair."""

    case: str
    decision: str
    decision_reasons: list
    baseline_path: str
    candidate_path: str
    obligation: Obligation
    baseline: BaselineModel
    correspondence: CorrespondenceResult
    authorization: AuthorizationResult
    moved_edges: tuple = ()
    candidate_warnings: tuple = ()
    boundary_map: tuple = ()
    expected_decision: str | None = None

    @property
    def achieved(self) -> bool | None:
        if self.expected_decision is None:
            return None
        return self.decision == self.expected_decision

    @property
    def ok(self) -> bool:
        return self.achieved is not False

    def as_dict(self) -> dict:
        return {
            "case": self.case,
            "decision": self.decision,
            "decision_reasons": self.decision_reasons,
            "expected_decision": self.expected_decision,
            "expected_achieved": self.achieved,
            "baseline": {
                "path": self.baseline_path,
                "validation": self.baseline.as_dict(),
            },
            "candidate": {
                "path": self.candidate_path,
                "moved_edges": [edge.as_dict() for edge in self.moved_edges],
                "warnings": list(self.candidate_warnings),
            },
            "obligation": self.obligation.as_dict(),
            "correspondence": self.correspondence.as_dict(),
            "authorization": self.authorization.as_dict(),
            "diagnostics": {"candidate_boundary_map": list(self.boundary_map)},
            "prototype_parameters": prototype_parameters(),
        }


def decide(
    correspondence: CorrespondenceResult, authorization: AuthorizationResult
) -> tuple:
    """Map (correspondence, authorization) onto the final SABLE decision."""
    if not correspondence.identified:
        detail = "; ".join(correspondence.unknown_reasons) or correspondence.status
        return (
            "UNKNOWN",
            [
                "correspondence did not establish a unique successor "
                f"({correspondence.status}/{correspondence.rule}): {detail}"
            ],
        )
    successor = correspondence.selected
    if authorization.status == "satisfied":
        return (
            "PRESERVED",
            [
                f"the baseline obligation is verified on the identified successor "
                f"{successor}"
            ],
        )
    if authorization.status == "violated":
        return (
            "REGRESSED",
            [
                f"the identified successor {successor} no longer preserves the baseline "
                f"obligation: {authorization.reason()}"
            ],
        )
    if authorization.status == "not_evaluated":
        detail = "; ".join(authorization.notes) or "not evaluated"
        return ("UNKNOWN", [f"authorization was not evaluated for {successor}: {detail}"])
    return (
        "UNKNOWN",
        [
            f"authorization for the identified successor {successor} is "
            f"{authorization.status}: {authorization.reason()}"
        ],
    )


def verify_pair(
    baseline_dir: str | Path,
    candidate_dir: str | Path,
    obligation_path: str | Path,
    case: str = "",
    expected_decision: str | None = None,
) -> VerificationResult:
    """Run validation -> correspondence -> authorization -> decision."""
    baseline_project = build_project(baseline_dir)
    candidate_project = build_project(candidate_dir)
    baseline_model: PolicyModel = build_policy_model(baseline_project)
    candidate_model: PolicyModel = build_policy_model(candidate_project)

    obligation: Obligation = bind_baseline(baseline_project, load_obligation(obligation_path))
    baseline: BaselineModel = validate_baseline(baseline_project, baseline_model, obligation)

    correspondence = correspond(
        baseline_project,
        candidate_project,
        obligation,
        baseline_model,
        candidate_model,
        candidate_project.moved,
    )

    if correspondence.identified:
        authorization = evaluate(
            candidate_project, candidate_model, obligation, correspondence.selected
        )
    else:
        # Without an identified successor the obligation cannot be attributed;
        # the candidate boundary map is still reported as diagnostics.
        authorization = not_evaluated(
            "no unique successor was identified, so the baseline obligation "
            "cannot be attributed to a candidate resource"
        )

    decision, reasons = decide(correspondence, authorization)
    boundary_map = describe_boundaries(candidate_project, candidate_model, obligation)

    return VerificationResult(
        case=case,
        decision=decision,
        decision_reasons=reasons,
        baseline_path=str(baseline_dir),
        candidate_path=str(candidate_dir),
        obligation=obligation,
        baseline=baseline,
        correspondence=correspondence,
        authorization=authorization,
        moved_edges=tuple(candidate_project.moved),
        candidate_warnings=tuple(candidate_project.warnings),
        boundary_map=tuple(boundary_map),
        expected_decision=expected_decision,
    )


def verify_fixture(case_dir: str | Path) -> VerificationResult:
    """Verify a POC fixture directory (baseline/, candidate/, obligation.json)."""
    case_dir = Path(case_dir)
    expected = None
    truth_path = case_dir / "ground_truth.json"
    if truth_path.is_file():
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        expected = truth.get("expected_decision")
    return verify_pair(
        case_dir / "baseline",
        case_dir / "candidate",
        case_dir / "obligation.json",
        case=case_dir.name,
        expected_decision=expected,
    )
