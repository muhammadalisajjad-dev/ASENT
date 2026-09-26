"""Local evaluation of the bounded S3/IAM least-privilege obligation.

The evaluator answers one question: does the designated principal still hold
exactly the obligation's action set on exactly the obligation's resource
scope, and is that boundary attached to the identified successor asset?
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shared.model import Node, Project
from shared.values import literal_string
from .policy import (
    PolicyModel,
    Statement,
    Target,
    action_covers,
    action_in_obligation,
    covers,
    is_broader,
    s3_action_level,
    s3_pattern_level,
    statement_targets,
)


@dataclass
class Check:
    id: str
    title: str
    status: str  # pass | fail | unknown
    expected: str | None = None
    actual: str | None = None
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "expected": self.expected,
            "actual": self.actual,
            "detail": self.detail,
        }


@dataclass
class StatementView:
    provider: str
    source: str
    effect: str
    actions: tuple
    targets: tuple
    applies: str  # yes | maybe | no

    def as_dict(self) -> dict:
        return {
            "provider": self.provider,
            "source": self.source,
            "effect": self.effect,
            "actions": list(self.actions),
            "targets": [
                {
                    "raw": target.raw,
                    "kind": target.kind,
                    "address": target.address,
                    "arn_pattern": target.arn_pattern,
                    "level": target.level,
                }
                for target in self.targets
            ],
            "applies_to_obligation_scope": self.applies,
        }


@dataclass
class AuthorizationResult:
    status: str  # satisfied | violated | indeterminate | not_evaluated
    principal: str | None
    principal_resolution: str
    actions: tuple
    resource: str | None
    scope_patterns: tuple
    checks: list = field(default_factory=list)
    statements: list = field(default_factory=list)
    other_asset_bindings: list = field(default_factory=list)
    unsupported: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return any(check.status == "fail" for check in self.checks)

    @property
    def indeterminate(self) -> bool:
        return any(check.status == "unknown" for check in self.checks)

    def reason(self) -> str:
        failures = [check for check in self.checks if check.status == "fail"]
        if failures:
            return "; ".join(f"{check.title}: {check.detail}" for check in failures)
        unknowns = [check for check in self.checks if check.status == "unknown"]
        if unknowns:
            return "; ".join(f"{check.title}: {check.detail}" for check in unknowns)
        return "the obligation is satisfied on the identified successor"

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "principal": self.principal,
            "principal_resolution": self.principal_resolution,
            "actions": list(self.actions),
            "resource": self.resource,
            "resource_scope": list(self.scope_patterns),
            "checks": [check.as_dict() for check in self.checks],
            "statements": [statement.as_dict() for statement in self.statements],
            "other_asset_bindings": self.other_asset_bindings,
            "unsupported_features": self.unsupported,
            "notes": self.notes,
        }


def resolve_principal(project: Project, obligation) -> tuple:
    """Resolve the obligation principal inside a configuration."""
    node = project.get(obligation.principal_address)
    if node is not None:
        return node.address, "address", None
    principal_type = obligation.principal_address.split(".")[0]
    name = obligation.principal_name
    if name:
        matches = [
            candidate
            for candidate in project.resources()
            if candidate.type == principal_type
            and literal_string(candidate.body.attr("name")) == name
        ]
        if len(matches) == 1:
            return (
                matches[0].address,
                "name",
                f"principal resolved by IAM name '{name}'",
            )
        if len(matches) > 1:
            return (
                None,
                "ambiguous",
                f"multiple {principal_type} resources carry the name '{name}'",
            )
    return None, "missing", None


def _statement_covers(view: StatementView, pattern: str) -> bool | None:
    results = [covers(target, pattern) for target in view.targets]
    if any(result is True for result in results):
        return True
    if any(result is None for result in results):
        return None
    return False


def _applies(view: StatementView, patterns: tuple) -> str:
    states = [_statement_covers(view, pattern) for pattern in patterns]
    if any(state is True for state in states):
        return "yes"
    if any(state is None for state in states):
        return "maybe"
    return "no"


def _grants(view: StatementView, action: str) -> bool:
    return any(action_covers(statement_action, action) for statement_action in view.actions)


def _bucket_policy_matches(provider, principal_name: str | None) -> bool:
    if principal_name is None:
        return False
    for statement in provider.statements:
        if statement.principals is None:
            return True
        for identifier in statement.principals:
            if identifier == "*" or identifier == principal_name or identifier.endswith(
                "/" + principal_name
            ):
                return True
    return False


def _collect_views(
    project: Project,
    model: PolicyModel,
    principal_address: str | None,
    successor_address: str | None,
    obligation,
) -> tuple:
    views: list = []
    unsupported: list = []
    notes: list = []
    providers = []
    if principal_address is not None:
        providers.extend(model.providers_for_principal(principal_address))
    if successor_address is not None:
        principal_name = obligation.principal_name
        for provider in model.bucket_providers(successor_address):
            if _bucket_policy_matches(provider, principal_name):
                providers.append(provider)
                notes.append(f"bucket policy {provider.address} also governs the successor")
    for provider in providers:
        unsupported.extend(f"{provider.address}: {note}" for note in provider.unsupported)
        for statement in provider.statements:
            targets = statement_targets(project, statement, statement.scope)
            view = StatementView(
                provider=provider.address,
                source=statement.source,
                effect=statement.effect,
                actions=statement.actions,
                targets=tuple(targets),
                applies="no",
            )
            view.applies = _applies(view, obligation.scope_patterns)
            views.append(view)
    return views, sorted(set(unsupported)), notes, providers


def evaluate(
    project: Project,
    model: PolicyModel,
    obligation,
    successor_address: str | None,
) -> AuthorizationResult:
    """Evaluate the obligation against an identified successor."""
    principal_address, resolution, principal_note = resolve_principal(project, obligation)
    result = AuthorizationResult(
        status="indeterminate",
        principal=principal_address,
        principal_resolution=resolution,
        actions=tuple(obligation.actions),
        resource=successor_address,
        scope_patterns=tuple(obligation.scope_patterns),
    )
    if principal_note:
        result.notes.append(principal_note)

    views, unsupported, collection_notes, providers = _collect_views(
        project, model, principal_address, successor_address, obligation
    )
    result.statements = [view for view in views if view.applies != "no"]
    result.unsupported = unsupported
    result.notes.extend(collection_notes)

    allow_views = [view for view in views if view.effect.lower() != "deny"]
    deny_views = [view for view in views if view.effect.lower() == "deny"]
    applying = [view for view in allow_views if view.applies == "yes"]
    maybe = [view for view in allow_views if view.applies == "maybe"]

    # --- check 1: principal present -------------------------------------
    if principal_address is None:
        result.checks.append(
            Check(
                id="principal_present",
                title="designated principal exists",
                status="fail",
                expected=obligation.principal_address,
                actual=None,
                detail=(
                    f"principal could not be resolved ({resolution})"
                    + (f": {principal_note}" if principal_note else "")
                ),
            )
        )
    else:
        result.checks.append(
            Check(
                id="principal_present",
                title="designated principal exists",
                status="pass",
                expected=obligation.principal_address,
                actual=principal_address,
                detail="principal resolved" + (f" by {resolution}" if resolution != "address" else ""),
            )
        )

    # --- check 2: policy attachment --------------------------------------
    attached_allow = [
        view for view in allow_views if any(action.startswith("s3:") for action in view.actions)
    ]
    if not providers:
        result.checks.append(
            Check(
                id="policy_attachment",
                title="principal still carries an S3 policy",
                status="fail",
                expected="at least one attached policy with S3 statements",
                actual="none",
                detail="no policy is attached to the principal in the candidate configuration",
            )
        )
    elif not attached_allow:
        unresolved_providers = [provider for provider in providers if not provider.resolved]
        if unresolved_providers or unsupported:
            result.checks.append(
                Check(
                    id="policy_attachment",
                    title="principal still carries an S3 policy",
                    status="unknown",
                    expected="readable attached policy with S3 statements",
                    actual="unreadable policy",
                    detail="attached policies could not be interpreted: "
                    + "; ".join(unsupported or ["policy not readable"]),
                )
            )
        else:
            result.checks.append(
                Check(
                    id="policy_attachment",
                    title="principal still carries an S3 policy",
                    status="fail",
                    expected="attached policy with S3 statements",
                    actual="policy without S3 statements",
                    detail="attached policies contain no S3 statements",
                )
            )
    else:
        result.checks.append(
            Check(
                id="policy_attachment",
                title="principal still carries an S3 policy",
                status="pass",
                expected="attached policy with S3 statements",
                actual=", ".join(sorted({view.provider for view in attached_allow})),
                detail="S3 statements remain attached to the principal",
            )
        )

    # --- check 3: boundary attached to the successor ----------------------
    bound = [
        view
        for view in applying
        for target in view.targets
        if target.address is not None and target.address == successor_address
    ]
    if applying and bound:
        result.checks.append(
            Check(
                id="successor_binding",
                title="boundary is attached to the identified successor",
                status="pass",
                expected=successor_address,
                actual=successor_address,
                detail="an attached allow statement targets the successor resource address",
            )
        )
    elif applying:
        result.checks.append(
            Check(
                id="successor_binding",
                title="boundary is attached to the identified successor",
                status="pass",
                expected=successor_address,
                actual="literal ARN scope",
                detail="allow statements cover the obligation scope by literal ARN pattern",
            )
        )
    elif maybe:
        result.checks.append(
            Check(
                id="successor_binding",
                title="boundary is attached to the identified successor",
                status="unknown",
                expected=successor_address,
                actual="unresolvable scope",
                detail="allow statements exist but their resource scope cannot be resolved locally",
            )
        )
    else:
        bindings = _other_bindings(allow_views, successor_address)
        result.other_asset_bindings = bindings
        detail = "no attached allow statement covers the obligation scope"
        if bindings:
            detail += "; the boundary now governs: " + ", ".join(
                binding["asset"] for binding in bindings
            )
        result.checks.append(
            Check(
                id="successor_binding",
                title="boundary is attached to the identified successor",
                status="fail",
                expected=f"scope {', '.join(obligation.scope_patterns)} on {successor_address}",
                actual=", ".join(binding["asset"] for binding in bindings) or "none",
                detail=detail,
            )
        )

    # --- check 4: action coverage ----------------------------------------
    missing: list = []
    indeterminate: list = []
    for action in obligation.actions:
        level = s3_action_level(action)
        if level is None:
            required = list(obligation.scope_patterns)
        else:
            required = [
                pattern
                for pattern in obligation.scope_patterns
                if s3_pattern_level(pattern) == level
            ] or list(obligation.scope_patterns)
        for pattern in required:
            covered = False
            unresolved = False
            for view in applying:
                if _grants(view, action) and _statement_covers(view, pattern) is True:
                    covered = True
                    break
            if not covered:
                for view in maybe:
                    if _grants(view, action) and _statement_covers(view, pattern) is None:
                        unresolved = True
                        break
                if unresolved:
                    indeterminate.append(f"{action} on {pattern}")
                else:
                    missing.append(f"{action} on {pattern}")
    if missing:
        result.checks.append(
            Check(
                id="action_coverage",
                title="obligation actions remain granted on the obligation scope",
                status="fail",
                expected=", ".join(obligation.actions),
                actual="missing: " + ", ".join(missing),
                detail="the verified action set is no longer granted on the verified scope",
            )
        )
    elif indeterminate:
        result.checks.append(
            Check(
                id="action_coverage",
                title="obligation actions remain granted on the obligation scope",
                status="unknown",
                expected=", ".join(obligation.actions),
                actual="unresolved: " + ", ".join(indeterminate),
                detail="scope cannot be resolved to a concrete ARN locally",
            )
        )
    else:
        result.checks.append(
            Check(
                id="action_coverage",
                title="obligation actions remain granted on the obligation scope",
                status="pass",
                expected=", ".join(obligation.actions),
                actual=", ".join(obligation.actions),
                detail="every obligation action is granted on every obligation scope pattern",
            )
        )

    # --- check 5: action widening ----------------------------------------
    allowed_actions: set = set()
    for view in applying:
        allowed_actions.update(view.actions)
    extras = sorted(
        action
        for action in allowed_actions
        if not action_in_obligation(action, obligation.actions)
    )
    if extras:
        result.checks.append(
            Check(
                id="action_widening",
                title="principal receives no actions beyond the obligation",
                status="fail",
                expected="subset of " + ", ".join(obligation.actions),
                actual=", ".join(extras),
                detail="allowed actions on the protected scope are broader than the verified boundary",
            )
        )
    elif allowed_actions:
        result.checks.append(
            Check(
                id="action_widening",
                title="principal receives no actions beyond the obligation",
                status="pass",
                expected="subset of " + ", ".join(obligation.actions),
                actual=", ".join(sorted(allowed_actions)),
                detail="no additional actions are granted on the protected scope",
            )
        )
    else:
        result.checks.append(
            Check(
                id="action_widening",
                title="principal receives no actions beyond the obligation",
                status="unknown",
                expected="subset of " + ", ".join(obligation.actions),
                actual="no readable actions",
                detail="no readable allow statement covers the obligation scope",
            )
        )

    # --- check 6: resource scope widening ---------------------------------
    broader: list = []
    for view in applying:
        for target in view.targets:
            if is_broader(target, tuple(obligation.scope_patterns)):
                broader.append(target.raw)
    if broader:
        result.checks.append(
            Check(
                id="scope_widening",
                title="resource scope is not broader than the obligation",
                status="fail",
                expected=", ".join(obligation.scope_patterns),
                actual=", ".join(sorted(set(broader))),
                detail="the boundary reaches resources outside the verified scope",
            )
        )
    else:
        result.checks.append(
            Check(
                id="scope_widening",
                title="resource scope is not broader than the obligation",
                status="pass",
                expected=", ".join(obligation.scope_patterns),
                actual=", ".join(obligation.scope_patterns),
                detail="no grant reaches beyond the verified resource scope",
            )
        )

    # --- check 7: deny conflicts ------------------------------------------
    deny_fail: list = []
    deny_unknown: list = []
    for view in deny_views:
        if view.applies == "no":
            continue
        for action in obligation.actions:
            if not _grants(view, action):
                continue
            if view.applies == "yes":
                deny_fail.append(f"{action} denied by {view.provider}")
            else:
                deny_unknown.append(f"{action} possibly denied by {view.provider}")
    if deny_fail:
        result.checks.append(
            Check(
                id="deny_conflict",
                title="no deny statement revokes the obligation actions",
                status="fail",
                expected="no deny on the obligation scope",
                actual=", ".join(sorted(set(deny_fail))),
                detail="a deny statement revokes part of the verified boundary",
            )
        )
    elif deny_unknown:
        result.checks.append(
            Check(
                id="deny_conflict",
                title="no deny statement revokes the obligation actions",
                status="unknown",
                expected="no deny on the obligation scope",
                actual=", ".join(sorted(set(deny_unknown))),
                detail="a deny statement may apply but its scope is unresolved",
            )
        )
    else:
        result.checks.append(
            Check(
                id="deny_conflict",
                title="no deny statement revokes the obligation actions",
                status="pass",
                expected="no deny on the obligation scope",
                actual="none",
                detail="no attached deny statement touches the obligation",
            )
        )

    # --- check 8: interpretability ---------------------------------------
    if unsupported:
        result.checks.append(
            Check(
                id="policy_interpretability",
                title="attached policies are fully interpretable",
                status="unknown",
                expected="no unsupported policy features",
                actual="; ".join(unsupported),
                detail="attached policies use features outside the supported subset",
            )
        )
    else:
        result.checks.append(
            Check(
                id="policy_interpretability",
                title="attached policies are fully interpretable",
                status="pass",
                expected="no unsupported policy features",
                actual="none",
                detail="all attached policies were interpreted locally",
            )
        )

    if successor_address is None:
        result.other_asset_bindings = _other_bindings(allow_views, None)
    else:
        result.other_asset_bindings = _other_bindings(allow_views, successor_address)

    if result.failed:
        result.status = "violated"
    elif result.indeterminate:
        result.status = "indeterminate"
    else:
        result.status = "satisfied"
    return result


def _other_bindings(allow_views: list, successor_address: str | None) -> list:
    bindings: dict = {}
    for view in allow_views:
        for target in view.targets:
            if target.kind == "address" and target.address and target.address != successor_address:
                entry = bindings.setdefault(
                    target.address,
                    {"asset": target.address, "actions": set(), "providers": set()},
                )
                entry["actions"].update(view.actions)
                entry["providers"].add(view.provider)
            elif target.kind == "arn" and target.arn_pattern:
                entry = bindings.setdefault(
                    target.arn_pattern,
                    {"asset": target.arn_pattern, "actions": set(), "providers": set()},
                )
                entry["actions"].update(view.actions)
                entry["providers"].add(view.provider)
    out = []
    for key in sorted(bindings):
        entry = bindings[key]
        out.append(
            {
                "asset": entry["asset"],
                "actions": sorted(entry["actions"]),
                "providers": sorted(entry["providers"]),
            }
        )
    return out


def describe_boundaries(project: Project, model: PolicyModel, obligation) -> list:
    """Map every asset that receives S3 grants from any policy in the project.

    Used as diagnostic evidence when no defensible successor exists.
    """
    bindings: dict = {}
    for provider in model.providers:
        for statement in provider.statements:
            if statement.effect.lower() == "deny":
                continue
            s3_actions = tuple(action for action in statement.actions if action.startswith("s3:"))
            if not s3_actions:
                continue
            targets = statement_targets(project, statement, statement.scope)
            for target in targets:
                if target.kind == "address" and target.address:
                    key = target.address
                elif target.kind == "arn" and target.arn_pattern:
                    key = target.arn_pattern
                elif target.kind == "global":
                    key = "*"
                else:
                    key = target.raw
                entry = bindings.setdefault(
                    key,
                    {"asset": key, "actions": set(), "providers": set(), "principals": set()},
                )
                entry["actions"].update(s3_actions)
                entry["providers"].add(provider.address)
                if provider.inline_principal:
                    entry["principals"].add(provider.inline_principal)
                else:
                    for principal in model.attachments.get(provider.address, []):
                        entry["principals"].add(principal)
    out = []
    for key in sorted(bindings):
        entry = bindings[key]
        out.append(
            {
                "asset": entry["asset"],
                "actions": sorted(entry["actions"]),
                "providers": sorted(entry["providers"]),
                "principals": sorted(entry["principals"]),
            }
        )
    return out


def not_evaluated(reason: str) -> AuthorizationResult:
    return AuthorizationResult(
        status="not_evaluated",
        principal=None,
        principal_resolution="not_evaluated",
        actions=(),
        resource=None,
        scope_patterns=(),
        notes=[reason],
    )
