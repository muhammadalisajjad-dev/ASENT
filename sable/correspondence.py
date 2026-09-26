"""Candidate successor correspondence (SABLE phase 4).

Bounded, deterministic evidence signals decide which candidate resource is the
logical successor of the protected baseline asset.  Name similarity is
recorded as evidence but is never sufficient to identify a successor, and
conflicting evidence produces UNKNOWN rather than a guess.

Correspondence answers an *identification* question only.  Whether the
baseline least-privilege obligation still holds on the identified successor
is decided separately by :mod:`sable.authorize`; the ``policy_target`` signal
is therefore only structural relationship evidence ("some S3 policy covers
this candidate") and is never treated as proof that the obligation survived.

All deterministic thresholds and weights live in the single PROTOTYPE
PARAMETERS section below and are echoed through :func:`prototype_parameters`.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from shared.model import MoveEdge, Node, Project
from shared.values import literal_string

from .policy import AUTH_FAMILIES, PolicyModel, glob_match, node_family, statement_targets

# ---------------------------------------------------------------------------
# PROTOTYPE PARAMETERS (the single traceable configuration section)
#
# Every deterministic weight and threshold used by this module is declared
# here and only here.  These are *initial prototype parameters* for the SABLE
# POC: they are chosen deterministically so runs are reproducible, but they
# are NOT claimed to be scientifically optimal and are intended to be
# evaluated empirically as the evidence corpus grows.  Evidence documents
# echo this section (see :func:`prototype_parameters`) so every decision can
# be traced back to the parameters that produced it.
# ---------------------------------------------------------------------------

# Evidence weights (relative influence of each signal on the composite score).
WEIGHTS = {
    "moved": 3.0,
    "address_identity": 2.5,
    "attributes": 3.0,
    "references": 1.5,
    "module_path_position": 1.5,
    "dependency_context": 1.0,
    "policy_target": 1.5,
    # Name similarity is deliberately the weakest signal: it can contribute
    # evidence but can never establish succession on its own.
    "name_similarity": 0.5,
}

# Signals that count as structural/semantic evidence.  Identity signals
# (moved, address_identity), policy relationship evidence and name similarity
# are deliberately excluded from this set.
STRUCTURAL_SIGNALS = (
    "attributes",
    "references",
    "module_path_position",
    "dependency_context",
)

# Prototype thresholds (all empirically unvalidated).
ATTRIBUTES_STRONG = 0.75  # configuration continuity considered "strong"
ATTRIBUTES_WEAK = 0.5  # configuration continuity considered "materially weak"
ATTRIBUTES_AMBIGUITY_GAP = 0.25  # max attribute gap for two candidates to stay comparable
SUPPORT_THRESHOLD = 0.6  # per-signal score counted as structural support
SCORE_THRESHOLD = 0.35  # minimum composite score for a qualifying candidate
MARGIN_THRESHOLD = 0.10  # minimum composite-score gap to claim a unique successor
MIN_STRUCTURAL_SUPPORT = 2  # independent structural signals needed to identify
STRUCTURAL_CONTRADICTION_MARGIN = 0.20  # structural-score gap that contradicts identity evidence

PROTOTYPE_PARAMETER_NOTE = (
    "Initial prototype parameters for the SABLE POC.  They are deterministic "
    "and traceable, but they are not empirically validated and are not claimed "
    "to be scientifically optimal; they must be evaluated against a growing "
    "evidence corpus."
)


def prototype_parameters() -> dict:
    """Echo every deterministic parameter of this module for traceability."""
    return {
        "weights": dict(WEIGHTS),
        "structural_signals": list(STRUCTURAL_SIGNALS),
        "thresholds": {
            "attributes_strong": ATTRIBUTES_STRONG,
            "attributes_weak": ATTRIBUTES_WEAK,
            "attributes_ambiguity_gap": ATTRIBUTES_AMBIGUITY_GAP,
            "support_threshold": SUPPORT_THRESHOLD,
            "score_threshold": SCORE_THRESHOLD,
            "margin_threshold": MARGIN_THRESHOLD,
            "min_structural_support": MIN_STRUCTURAL_SUPPORT,
            "structural_contradiction_margin": STRUCTURAL_CONTRADICTION_MARGIN,
        },
        "note": PROTOTYPE_PARAMETER_NOTE,
    }



@dataclass
class Signal:
    id: str
    applicable: bool
    score: float | None
    weight: float
    detail: str
    supporting: bool = False

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "applicable": self.applicable,
            "score": None if self.score is None else round(self.score, 6),
            "weight": self.weight,
            "structural_support": self.supporting,
            "detail": self.detail,
        }


@dataclass
class Hypothesis:
    address: str
    signals: dict
    score: float
    structural_support: tuple

    def signal(self, signal_id: str) -> Signal:
        return self.signals[signal_id]

    def as_dict(self, selected: bool) -> dict:
        return {
            "address": self.address,
            "score": round(self.score, 6),
            "selected": selected,
            "structural_support": list(self.structural_support),
            "signals": [
                self.signals[signal_id].as_dict()
                for signal_id in [
                    "resource_type",
                    "moved",
                    "address_identity",
                    "attributes",
                    "references",
                    "module_path_position",
                    "dependency_context",
                    "policy_target",
                    "name_similarity",
                ]
                if signal_id in self.signals
            ],
        }


@dataclass
class CorrespondenceResult:
    status: str  # identified | ambiguous | conflict | insufficient | no_candidates
    rule: str
    selected: str | None
    margin: float | None
    hypotheses: tuple
    conflicts: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    unknown_reasons: list = field(default_factory=list)
    baseline_asset: str = ""
    candidate_type: str = ""

    @property
    def identified(self) -> bool:
        return self.status == "identified" and self.selected is not None

    def as_dict(self) -> dict:
        selected_hypothesis = next(
            (hypothesis for hypothesis in self.hypotheses if hypothesis.address == self.selected),
            None,
        )
        return {
            "status": self.status,
            "rule": self.rule,
            "baseline_asset": self.baseline_asset,
            "candidate_type": self.candidate_type,
            "candidate_count": len(self.hypotheses),
            "selected_successor": self.selected,
            "selected_candidate": None
            if selected_hypothesis is None
            else selected_hypothesis.as_dict(selected=True),
            "competing_candidates": [
                {
                    "address": hypothesis.address,
                    "score": round(hypothesis.score, 6),
                    "structural_support": list(hypothesis.structural_support),
                    "attributes": None
                    if hypothesis.signal("attributes").score is None
                    else round(hypothesis.signal("attributes").score, 6),
                    "policy_targeted": bool(
                        hypothesis.signal("policy_target").applicable
                        and (hypothesis.signal("policy_target").score or 0.0) >= 1.0
                    ),
                }
                for hypothesis in self.hypotheses
                if hypothesis.address != self.selected
            ],
            "margin": None if self.margin is None else round(self.margin, 6),
            "conflicts": self.conflicts,
            "notes": self.notes,
            "unknown_reasons": self.unknown_reasons,
            "hypotheses": [
                hypothesis.as_dict(selected=hypothesis.address == self.selected)
                for hypothesis in self.hypotheses
            ],
        }


def _jaccard_counter(left: list, right: list) -> float:
    counter_left = Counter(left)
    counter_right = Counter(right)
    keys = set(counter_left) | set(counter_right)
    if not keys:
        return 1.0
    intersection = sum(min(counter_left[key], counter_right[key]) for key in keys)
    union = sum(max(counter_left[key], counter_right[key]) for key in keys)
    return intersection / union if union else 1.0


def _jaccard_mapping(left: dict, right: dict) -> tuple:
    keys_left = set(left)
    keys_right = set(right)
    union = keys_left | keys_right
    if not union:
        return 1.0, 0, 0
    matched = sum(1 for key in keys_left & keys_right if left[key] == right[key])
    return matched / len(union), matched, len(union)


def referrer_families(project: Project, address: str) -> list:
    """Families of nodes referencing ``address``, excluding policy wiring."""
    return sorted(
        node_family(node)
        for node in project.incoming(address)
        if node_family(node) not in AUTH_FAMILIES
    )


def outgoing_families(project: Project, node: Node) -> list:
    return sorted(kind for kind in node.ref_kinds if kind not in AUTH_FAMILIES)


def neighbourhood_families(project: Project, address: str, depth: int = 2) -> list:
    """Two-hop structural neighbourhood families, excluding policy wiring."""
    visited = {address}
    frontier = {address}
    collected: list = []
    for _level in range(depth):
        next_frontier: set = set()
        for current in frontier:
            node = project.get(current)
            neighbours: set = set()
            if node is not None:
                neighbours.update(node.refs)
            neighbours.update(referrer.address for referrer in project.incoming(current))
            for neighbour in sorted(neighbours):
                if neighbour in visited:
                    continue
                neighbour_node = project.get(neighbour)
                if neighbour_node is None:
                    continue
                if node_family(neighbour_node) in AUTH_FAMILIES:
                    continue
                visited.add(neighbour)
                next_frontier.add(neighbour)
                collected.append(node_family(neighbour_node))
        frontier = next_frontier
        if not frontier:
            break
    return sorted(collected)


def _asset_arns(project: Project, address: str) -> set:
    node = project.get(address)
    if node is None or node.type != "aws_s3_bucket":
        return set()
    name = literal_string(node.body.attr("bucket"))
    if not name:
        return set()
    return {f"arn:aws:s3:::{name}", f"arn:aws:s3:::{name}/*"}


def _boundary_actions(project: Project, model: PolicyModel, address: str) -> tuple:
    """Whether S3 allow statements cover ``address`` (relationship evidence).

    This is *structural* relationship evidence only: it records which
    candidate an S3 policy wiring happens to point at.  It says nothing about
    whether the baseline least-privilege obligation survives - that is
    verified separately in :mod:`sable.authorize`.
    """
    arns = _asset_arns(project, address)
    actions: set = set()
    providers: set = set()
    for provider in model.providers:
        for statement in provider.statements:
            if statement.effect.lower() == "deny":
                continue
            s3_actions = tuple(action for action in statement.actions if action.startswith("s3:"))
            if not s3_actions:
                continue
            for target in statement_targets(project, statement, statement.scope):
                if target.kind == "address" and target.address == address:
                    covered = True
                elif target.kind == "global":
                    covered = True
                elif target.arn_pattern is not None:
                    covered = any(glob_match(target.arn_pattern, arn) for arn in arns)
                else:
                    covered = False
                if covered:
                    actions.update(s3_actions)
                    providers.add(provider.address)
                    break
    return bool(providers), actions, sorted(providers)


def _name_tokens(name: str | None) -> set:
    if not name:
        return set()
    return {token for token in name.lower().replace("-", "_").split("_") if token}


def correspond(
    baseline_project: Project,
    candidate_project: Project,
    obligation,
    baseline_model: PolicyModel,
    candidate_model: PolicyModel,
    move_edges: list,
) -> CorrespondenceResult:
    """Generate successor hypotheses and apply the identification rules."""
    baseline_asset = baseline_project.get(obligation.protected_asset)
    if baseline_asset is None:
        raise ValueError("baseline asset missing")  # guarded by baseline validation

    candidates = candidate_project.of_type(baseline_asset.type)
    base_result = dict(
        baseline_asset=baseline_asset.address,
        candidate_type=baseline_asset.type,
    )
    if not candidates:
        return CorrespondenceResult(
            status="no_candidates",
            rule="none",
            selected=None,
            margin=None,
            hypotheses=(),
            unknown_reasons=[
                f"candidate configuration defines no {baseline_asset.type} resource"
            ],
            notes=["no successor hypothesis could be generated"],
            **base_result,
        )

    baseline_signature = baseline_asset.signature()
    baseline_in = referrer_families(baseline_project, baseline_asset.address)
    baseline_out = outgoing_families(baseline_project, baseline_asset)
    baseline_neighbourhood = neighbourhood_families(baseline_project, baseline_asset.address)
    baseline_targeted, baseline_boundary_actions, baseline_providers = _boundary_actions(
        baseline_project, baseline_model, baseline_asset.address
    )
    baseline_name_tokens = _name_tokens(baseline_asset.name)
    edges_from_baseline = [edge for edge in move_edges if edge.from_address == baseline_asset.address]

    hypotheses: list = []
    for candidate in sorted(candidates, key=lambda node: node.address):
        signals: dict = {}

        signals["resource_type"] = Signal(
            id="resource_type",
            applicable=True,
            score=1.0,
            weight=0.0,
            detail=f"candidate resource type {candidate.type} equals the baseline asset type",
        )

        if edges_from_baseline:
            matches = [edge for edge in edges_from_baseline if edge.to_address == candidate.address]
            signals["moved"] = Signal(
                id="moved",
                applicable=True,
                score=1.0 if matches else 0.0,
                weight=WEIGHTS["moved"],
                detail=(
                    "explicit move: " + "; ".join(f"{edge.from_address} -> {edge.to_address}" for edge in matches)
                    if matches
                    else "explicit move information exists but does not target this resource"
                ),
            )
        else:
            signals["moved"] = Signal(
                id="moved",
                applicable=False,
                score=None,
                weight=WEIGHTS["moved"],
                detail="no explicit move information for the baseline asset",
            )

        signals["address_identity"] = Signal(
            id="address_identity",
            applicable=True,
            score=1.0 if candidate.address == baseline_asset.address else 0.0,
            weight=WEIGHTS["address_identity"],
            detail=(
                "identical Terraform address"
                if candidate.address == baseline_asset.address
                else f"address changed: {baseline_asset.address} -> {candidate.address}"
            ),
        )

        ratio, matched, union = _jaccard_mapping(baseline_signature, candidate.signature())
        signals["attributes"] = Signal(
            id="attributes",
            applicable=True,
            score=ratio,
            weight=WEIGHTS["attributes"],
            detail=f"{matched}/{union} normalized attributes match the baseline asset configuration",
        )

        candidate_in = referrer_families(candidate_project, candidate.address)
        candidate_out = outgoing_families(candidate_project, candidate)
        directions: list = []
        reference_parts: list = []
        if baseline_in:
            directions.append(_jaccard_counter(baseline_in, candidate_in))
            reference_parts.append(
                f"incoming structural referrers {baseline_in or '[]'} -> {candidate_in or '[]'}"
            )
        if baseline_out:
            directions.append(_jaccard_counter(baseline_out, candidate_out))
            reference_parts.append(
                f"outgoing references {baseline_out or '[]'} -> {candidate_out or '[]'}"
            )
        signals["references"] = Signal(
            id="references",
            applicable=bool(directions),
            score=sum(directions) / len(directions) if directions else None,
            weight=WEIGHTS["references"],
            detail="; ".join(reference_parts)
            if reference_parts
            else "baseline asset has no non-policy structural references to compare",
        )

        candidate_path = candidate.module_path
        if candidate_path == baseline_asset.module_path:
            path_score = 1.0
            path_detail = "same module path"
        elif candidate_path[: len(baseline_asset.module_path)] == baseline_asset.module_path or (
            baseline_asset.module_path[: len(candidate_path)] == candidate_path
        ):
            path_score = 0.5
            path_detail = f"module path changed: {list(baseline_asset.module_path)} -> {list(candidate_path)}"
        else:
            path_score = 0.0
            path_detail = f"unrelated module path: {list(baseline_asset.module_path)} -> {list(candidate_path)}"
        file_score = 1.0 if candidate.file == baseline_asset.file else 0.0
        index_score = max(0.0, 1.0 - abs(candidate.ordinal - baseline_asset.ordinal) / 5.0)
        position_score = 0.4 * path_score + 0.3 * file_score + 0.3 * index_score
        signals["module_path_position"] = Signal(
            id="module_path_position",
            applicable=True,
            score=position_score,
            weight=WEIGHTS["module_path_position"],
            detail=(
                f"{path_detail}; file {baseline_asset.file} -> {candidate.file}; "
                f"position among {baseline_asset.type} resources "
                f"{baseline_asset.ordinal} -> {candidate.ordinal}"
            ),
        )

        candidate_neighbourhood = neighbourhood_families(candidate_project, candidate.address)
        signals["dependency_context"] = Signal(
            id="dependency_context",
            applicable=bool(baseline_neighbourhood),
            score=_jaccard_counter(baseline_neighbourhood, candidate_neighbourhood)
            if baseline_neighbourhood
            else None,
            weight=WEIGHTS["dependency_context"],
            detail=(
                f"two-hop structural neighbourhood {baseline_neighbourhood} -> {candidate_neighbourhood}"
                if baseline_neighbourhood
                else "baseline asset has no structural dependency context to compare"
            ),
        )

        targeted, actions, providers = _boundary_actions(
            candidate_project, candidate_model, candidate.address
        )
        # Relationship evidence only: *whether* an S3 policy wiring covers the
        # candidate.  Conformance with the baseline obligation action/scope set
        # is deliberately NOT evaluated here - that check belongs to the
        # authorization stage (sable.authorize) and is reported separately.
        if not baseline_targeted:
            policy_score = None
            policy_detail = "baseline asset is not covered by any S3 policy statement"
            policy_applicable = False
        elif not targeted:
            policy_score = 0.0
            policy_detail = "no S3 allow statement covers this candidate resource"
            policy_applicable = True
        else:
            policy_score = 1.0
            policy_detail = (
                f"S3 allow statements from {', '.join(providers)} cover this candidate "
                "resource (relationship evidence only; obligation conformance is verified "
                "separately in the authorization stage)"
            )
            policy_applicable = True
        signals["policy_target"] = Signal(
            id="policy_target",
            applicable=policy_applicable,
            score=policy_score,
            weight=WEIGHTS["policy_target"],
            detail=policy_detail,
        )

        candidate_tokens = _name_tokens(candidate.name)
        if baseline_name_tokens and candidate_tokens:
            name_score = len(baseline_name_tokens & candidate_tokens) / len(
                baseline_name_tokens | candidate_tokens
            )
        else:
            name_score = 0.0
        signals["name_similarity"] = Signal(
            id="name_similarity",
            applicable=True,
            score=name_score,
            weight=WEIGHTS["name_similarity"],
            detail=(
                f"resource-name token similarity {baseline_asset.name!r} vs {candidate.name!r} "
                f"= {name_score:.2f} (weakest signal: recorded as evidence, never "
                "sufficient to establish succession and never able to outweigh "
                "structural evidence)"
            ),
        )

        applicable = [
            signal
            for signal in signals.values()
            if signal.applicable and signal.weight > 0
        ]
        denominator = sum(signal.weight for signal in applicable)
        score = (
            sum(signal.weight * (signal.score or 0.0) for signal in applicable) / denominator
            if denominator
            else 0.0
        )
        support = tuple(
            signal_id
            for signal_id in STRUCTURAL_SIGNALS
            if signals[signal_id].applicable
            and signals[signal_id].score is not None
            and signals[signal_id].score >= SUPPORT_THRESHOLD
        )
        for signal_id in STRUCTURAL_SIGNALS:
            signals[signal_id].supporting = signal_id in support
        hypotheses.append(
            Hypothesis(
                address=candidate.address,
                signals=signals,
                score=score,
                structural_support=support,
            )
        )

    hypotheses.sort(key=lambda hypothesis: (-hypothesis.score, hypothesis.address))
    return _identify(hypotheses, edges_from_baseline, baseline_asset, **base_result)


def _attributes_score(hypothesis: Hypothesis) -> float:
    return hypothesis.signal("attributes").score or 0.0


def _structural_score(hypothesis: Hypothesis) -> float:
    """Weighted structural/semantic evidence only.

    Identity signals (``moved``, ``address_identity``), the ``policy_target``
    relationship signal and ``name_similarity`` are deliberately excluded:
    this score exists to test identity claims *against* configuration,
    reference, position and dependency evidence.
    """
    applicable = [
        hypothesis.signal(signal_id)
        for signal_id in STRUCTURAL_SIGNALS
        if hypothesis.signal(signal_id).applicable
        and hypothesis.signal(signal_id).score is not None
    ]
    denominator = sum(signal.weight for signal in applicable)
    if not denominator:
        return 0.0
    return sum(signal.weight * (signal.score or 0.0) for signal in applicable) / denominator


def _contradiction(target: Hypothesis, others: list, source: str) -> dict | None:
    """Detect structural/semantic evidence that materially contradicts a claim.

    Explicit ``moved`` metadata and an unchanged Terraform address are strong
    evidence, but neither is unconditional proof of logical security-asset
    continuity.  A conflict is returned whenever another candidate is
    materially better supported by the bounded structural evidence, so the
    caller reports UNKNOWN instead of silently trusting the identity claim.
    """
    if not others:
        return None
    by_attributes = sorted(
        others, key=lambda hypothesis: (-_attributes_score(hypothesis), hypothesis.address)
    )[0]
    by_structure = sorted(
        others, key=lambda hypothesis: (-_structural_score(hypothesis), hypothesis.address)
    )[0]

    reasons: list = []
    conflicting: list = []
    if (
        _attributes_score(target) < ATTRIBUTES_WEAK
        and _attributes_score(by_attributes) >= ATTRIBUTES_STRONG
    ):
        conflicting.append(by_attributes.address)
        reasons.append(
            f"{source} points at {target.address}, which preserves only "
            f"{_attributes_score(target):.2f} of the baseline configuration, while "
            f"{by_attributes.address} preserves {_attributes_score(by_attributes):.2f}"
        )
    if (
        len(by_structure.structural_support) >= MIN_STRUCTURAL_SUPPORT
        and _structural_score(by_structure) - _structural_score(target)
        >= STRUCTURAL_CONTRADICTION_MARGIN
    ):
        if by_structure.address not in conflicting:
            conflicting.append(by_structure.address)
        reasons.append(
            f"structural/semantic evidence for {by_structure.address} "
            f"(score {_structural_score(by_structure):.2f}, supports "
            f"{list(by_structure.structural_support)}) exceeds the evidence for "
            f"{source} target {target.address} "
            f"(score {_structural_score(target):.2f}, supports "
            f"{list(target.structural_support)}) by at least the prototype "
            f"contradiction margin {STRUCTURAL_CONTRADICTION_MARGIN}"
        )
    if not reasons:
        return None
    return {
        "source": source,
        "selected_by_source": target.address,
        "conflicting_candidate": conflicting[0],
        "conflicting_candidates": conflicting,
        "detail": "; ".join(reasons),
    }


def _identify(
    hypotheses: list,
    edges_from_baseline: list,
    baseline_node: Node,
    **base_result,
) -> CorrespondenceResult:
    notes: list = []

    # Rule 1: explicit Terraform moved information.
    # Strong evidence, but it must not override materially stronger
    # structural/semantic evidence from a competing candidate.
    if edges_from_baseline:
        targets = [
            hypothesis
            for hypothesis in hypotheses
            if hypothesis.signal("moved").applicable
            and (hypothesis.signal("moved").score or 0.0) >= 1.0
        ]
        if len(targets) > 1:
            return CorrespondenceResult(
                status="ambiguous",
                rule="explicit_moved",
                selected=None,
                margin=None,
                hypotheses=tuple(hypotheses),
                conflicts=[
                    {
                        "source": "moved_block",
                        "detail": "multiple move targets claim the baseline asset",
                        "candidates": [target.address for target in targets],
                    }
                ],
                unknown_reasons=["explicit move information names multiple successors"],
                notes=["explicit moved evidence is ambiguous"],
                **base_result,
            )
        if len(targets) == 1:
            target = targets[0]
            others = [h for h in hypotheses if h.address != target.address]
            conflict = _contradiction(target, others, "moved_block")
            if conflict is not None:
                return CorrespondenceResult(
                    status="conflict",
                    rule="explicit_moved",
                    selected=None,
                    margin=_margin(hypotheses),
                    hypotheses=tuple(hypotheses),
                    conflicts=[conflict],
                    unknown_reasons=[
                        "explicit move information conflicts with stronger "
                        "structural/semantic evidence"
                    ],
                    notes=[
                        "moved metadata is strong evidence but is not unconditional "
                        "proof; contradictory structural evidence was not overridden"
                    ],
                    **base_result,
                )
            return _identified(
                hypotheses,
                target,
                "explicit_moved",
                notes=[
                    "explicit move target accepted: no competing candidate holds "
                    f"materially stronger structural evidence "
                    f"(structural supports {list(target.structural_support) or '[]'})"
                ],
                **base_result,
            )
        notes.append(
            "explicit move information exists but its target is absent from the candidate"
        )

    # Rule 2: identical Terraform address.
    # Strong identity evidence, but configuration/policy/resource evidence can
    # still contradict it, in which case the result is UNKNOWN.
    identical = [
        hypothesis
        for hypothesis in hypotheses
        if hypothesis.address == baseline_node.address
    ]
    if identical:
        target = identical[0]
        others = [h for h in hypotheses if h.address != target.address]
        conflict = _contradiction(target, others, "address_identity")
        if conflict is not None:
            return CorrespondenceResult(
                status="conflict",
                rule="address_identity",
                selected=None,
                margin=_margin(hypotheses),
                hypotheses=tuple(hypotheses),
                conflicts=[conflict],
                unknown_reasons=[
                    "resource identity conflicts with structural/semantic evidence"
                ],
                notes=[
                    "an unchanged Terraform address is identity evidence, not proof "
                    "of logical succession"
                ],
                **base_result,
            )
        return _identified(
            hypotheses,
            target,
            "address_identity",
            notes=[
                "unchanged address accepted: no competing candidate holds materially "
                f"stronger structural evidence "
                f"(structural supports {list(target.structural_support) or '[]'})"
            ],
            **base_result,
        )

    # Rule 3: configuration continuity, but only as part of the multi-signal
    # model.  A high attribute-similarity score may identify a successor only
    # when independent structural signals corroborate it, no competitor
    # contradicts it and no rival candidate remains comparably supported.
    strong = [
        hypothesis
        for hypothesis in hypotheses
        if _attributes_score(hypothesis) >= ATTRIBUTES_STRONG
    ]
    if len(strong) > 1:
        return CorrespondenceResult(
            status="ambiguous",
            rule="config_continuity",
            selected=None,
            margin=_margin(hypotheses),
            hypotheses=tuple(hypotheses),
            unknown_reasons=[
                "multiple candidate resources preserve the protected asset configuration"
            ],
            conflicts=[
                {
                    "source": "config_continuity",
                    "detail": "several candidates match the baseline configuration",
                    "candidates": [hypothesis.address for hypothesis in strong],
                }
            ],
            notes=["configuration continuity does not select a unique successor"],
            **base_result,
        )
    if len(strong) == 1:
        target = strong[0]
        others = [hypothesis for hypothesis in hypotheses if hypothesis.address != target.address]
        conflict = _contradiction(target, others, "config_continuity")
        if conflict is not None:
            return CorrespondenceResult(
                status="conflict",
                rule="config_continuity",
                selected=None,
                margin=_margin(hypotheses),
                hypotheses=tuple(hypotheses),
                conflicts=[conflict],
                unknown_reasons=[
                    "high attribute similarity is contradicted by stronger "
                    "structural/semantic evidence"
                ],
                notes=[
                    "attribute similarity alone does not establish succession when "
                    "other correspondence evidence disagrees"
                ],
                **base_result,
            )
        support = target.structural_support
        corroborated = len(support) >= MIN_STRUCTURAL_SUPPORT and any(
            signal_id != "attributes" for signal_id in support
        )
        if not corroborated:
            return CorrespondenceResult(
                status="insufficient",
                rule="config_continuity",
                selected=None,
                margin=_margin(hypotheses),
                hypotheses=tuple(hypotheses),
                unknown_reasons=[
                    "attribute similarity is not corroborated by independent structural "
                    f"signals: {target.address} preserves "
                    f"{_attributes_score(target):.2f} of the baseline configuration but "
                    f"only supports {list(support) or '[]'}"
                ],
                conflicts=[
                    {
                        "source": "config_continuity",
                        "detail": (
                            f"{target.address} matches the baseline configuration but "
                            "lacks independent structural corroboration"
                        ),
                        "candidates": [target.address],
                    }
                ],
                notes=[
                    "the prototype attribute threshold is a necessary but not "
                    "sufficient condition for identification"
                ],
                **base_result,
            )
        if others:
            runner_up = sorted(others, key=lambda h: (-h.score, h.address))[0]
            gap = target.score - runner_up.score
            if gap < MARGIN_THRESHOLD:
                return CorrespondenceResult(
                    status="ambiguous",
                    rule="config_continuity",
                    selected=None,
                    margin=gap,
                    hypotheses=tuple(hypotheses),
                    unknown_reasons=[
                        "correspondence evidence does not separate the leading candidates"
                    ],
                    conflicts=[
                        {
                            "source": "config_continuity",
                            "detail": (
                                f"{target.address} ({target.score:.3f}) and "
                                f"{runner_up.address} ({runner_up.score:.3f}) are within "
                                "the prototype ambiguity margin"
                            ),
                            "candidates": [target.address, runner_up.address],
                        }
                    ],
                    notes=["scores are too close to select a unique successor"],
                    **base_result,
                )
        return _identified(
            hypotheses,
            target,
            "config_continuity",
            notes=[
                "configuration continuity corroborated by structural signals "
                f"{list(support)} (prototype threshold ATTRIBUTES_STRONG="
                f"{ATTRIBUTES_STRONG}, unvalidated)"
            ],
            **base_result,
        )

    # Rule 4: multi-signal structural correspondence.
    # Requires several independent structural signals, a winning margin and a
    # unique successor: a rival with comparable configuration/support keeps the
    # result UNKNOWN instead of being broken by name similarity or weight luck.
    qualifying = [
        hypothesis
        for hypothesis in hypotheses
        if hypothesis.score >= SCORE_THRESHOLD
        and len(hypothesis.structural_support) >= MIN_STRUCTURAL_SUPPORT
    ]
    if qualifying:
        top = qualifying[0]
        runner_up = next(
            (h for h in hypotheses if h.address != top.address), None
        )
        if runner_up is not None and (top.score - runner_up.score) < MARGIN_THRESHOLD:
            return CorrespondenceResult(
                status="ambiguous",
                rule="multi_signal_score",
                selected=None,
                margin=top.score - runner_up.score,
                hypotheses=tuple(hypotheses),
                unknown_reasons=["correspondence evidence does not separate the leading candidates"],
                conflicts=[
                    {
                        "source": "multi_signal_score",
                        "detail": (
                            f"{top.address} ({top.score:.3f}) and {runner_up.address} "
                            f"({runner_up.score:.3f}) are within the ambiguity margin"
                        ),
                        "candidates": [top.address, runner_up.address],
                    }
                ],
                notes=["scores are too close to select a unique successor"],
                **base_result,
            )
        rival = next(
            (
                hypothesis
                for hypothesis in hypotheses
                if hypothesis.address != top.address
                and len(hypothesis.structural_support) >= MIN_STRUCTURAL_SUPPORT
                and _attributes_score(hypothesis)
                >= _attributes_score(top) - ATTRIBUTES_AMBIGUITY_GAP
            ),
            None,
        )
        if rival is not None:
            return CorrespondenceResult(
                status="ambiguous",
                rule="multi_signal_score",
                selected=None,
                margin=top.score - rival.score,
                hypotheses=tuple(hypotheses),
                unknown_reasons=[
                    "the evidence does not establish a unique successor: a rival "
                    "candidate remains comparably supported"
                ],
                conflicts=[
                    {
                        "source": "multi_signal_score",
                        "detail": (
                            f"{top.address} and {rival.address} both carry "
                            f"{MIN_STRUCTURAL_SUPPORT}+ structural supports with "
                            "comparable configuration similarity "
                            f"({_attributes_score(top):.2f} vs "
                            f"{_attributes_score(rival):.2f}); name similarity or "
                            "minor weight differences cannot break the tie"
                        ),
                        "candidates": [top.address, rival.address],
                    }
                ],
                notes=["comparable rivals keep the correspondence ambiguous"],
                **base_result,
            )
        return _identified(
            hypotheses,
            top,
            "multi_signal_score",
            notes=[
                "identified from at least "
                f"{MIN_STRUCTURAL_SUPPORT} independent structural signals "
                f"{list(top.structural_support)} with a winning margin"
            ],
            **base_result,
        )

    best = hypotheses[0]
    if best.score < SCORE_THRESHOLD:
        reason = (
            "no candidate reached the correspondence threshold "
            f"({best.address} scored {best.score:.3f} < {SCORE_THRESHOLD})"
        )
    else:
        reason = (
            f"leading candidate lacks {MIN_STRUCTURAL_SUPPORT} independent structural "
            f"signals: {best.address} supports {list(best.structural_support) or '[]'}"
        )
    return CorrespondenceResult(
        status="insufficient",
        rule="none",
        selected=None,
        margin=_margin(hypotheses),
        hypotheses=tuple(hypotheses),
        unknown_reasons=[reason],
        notes=["structural correspondence evidence is insufficient"],
        **base_result,
    )


def _identified(
    hypotheses: list,
    target: Hypothesis,
    rule: str,
    notes: list | None = None,
    **base_result,
) -> CorrespondenceResult:
    return CorrespondenceResult(
        status="identified",
        rule=rule,
        selected=target.address,
        margin=_margin(hypotheses),
        hypotheses=tuple(hypotheses),
        notes=list(notes or []),
        **base_result,
    )


def _margin(hypotheses: list) -> float | None:
    if len(hypotheses) < 2:
        return None
    return hypotheses[0].score - hypotheses[1].score
