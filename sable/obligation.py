"""Baseline security obligation model (SABLE phase 3).

The obligation file is the declared least-privilege boundary.  The trusted
baseline is *independently* re-derived from its Terraform source and checked
before any baseline-to-candidate comparison is performed; a baseline that does
not realize its own obligation is rejected instead of trusted.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from pathlib import Path

from shared.errors import BaselineValidationError, ObligationError
from shared.model import Project, load_json
from shared.values import literal_string
from .authorize import AuthorizationResult, evaluate
from .policy import PolicyModel, statement_targets

SUPPORTED_ACTION_PREFIX = "s3:"


@dataclass(frozen=True)
class Obligation:
    """A declared least-privilege S3 obligation."""

    obligation_id: str
    principal_address: str
    actions: tuple
    protected_asset: str
    scope_patterns: tuple
    principal_kind: str | None = None
    principal_name: str | None = None
    source_file: str | None = None
    content_hash: str | None = None

    def as_dict(self) -> dict:
        return {
            "obligation_id": self.obligation_id,
            "principal": self.principal_address,
            "principal_kind": self.principal_kind,
            "principal_name": self.principal_name,
            "actions": list(self.actions),
            "protected_asset": self.protected_asset,
            "resource_scope": list(self.scope_patterns),
            "source_file": self.source_file,
            "source_sha256": self.content_hash,
        }


@dataclass
class DerivedBoundary:
    """Authorization boundary re-derived from a Terraform configuration."""

    principal_address: str
    protected_asset: str
    actions: tuple
    scope_patterns: tuple
    providers: tuple
    statement_count: int
    concrete_scope: bool = True
    notes: tuple = ()

    def as_dict(self) -> dict:
        return {
            "principal": self.principal_address,
            "protected_asset": self.protected_asset,
            "actions": list(self.actions),
            "resource_scope": list(self.scope_patterns),
            "providers": list(self.providers),
            "statement_count": self.statement_count,
            "scope_is_concrete": self.concrete_scope,
            "notes": list(self.notes),
        }


@dataclass
class BaselineModel:
    """Validated baseline obligation plus its supporting Terraform nodes."""

    obligation: Obligation
    derived: DerivedBoundary
    checks: list = field(default_factory=list)
    supporting_nodes: tuple = ()
    authorization: AuthorizationResult | None = None

    @property
    def validated(self) -> bool:
        return all(check["status"] == "pass" for check in self.checks)

    def as_dict(self) -> dict:
        return {
            "status": "validated" if self.validated else "rejected",
            "checks": self.checks,
            "derived_boundary": self.derived.as_dict(),
            "supporting_nodes": list(self.supporting_nodes),
            "authorization": self.authorization.as_dict() if self.authorization else None,
        }


def load_obligation(path: str) -> Obligation:
    """Load and validate a local obligation JSON document."""
    data = load_json(path)
    for key in ("obligation_id", "principal", "actions", "protected_asset", "resource_scope"):
        if key not in data:
            raise ObligationError(f"{path}: obligation is missing required field '{key}'")
    obligation_id = data["obligation_id"]
    principal = data["principal"]
    actions = data["actions"]
    protected_asset = data["protected_asset"]
    scope = data["resource_scope"]
    if not isinstance(obligation_id, str) or not obligation_id.strip():
        raise ObligationError(f"{path}: obligation_id must be a non-empty string")
    if not isinstance(principal, str) or "." not in principal:
        raise ObligationError(f"{path}: principal must be a Terraform address such as 'aws_iam_role.app'")
    if not isinstance(actions, list) or not actions or not all(
        isinstance(action, str) for action in actions
    ):
        raise ObligationError(f"{path}: actions must be a non-empty list of strings")
    unsupported_actions = [action for action in actions if not action.startswith(SUPPORTED_ACTION_PREFIX)]
    if unsupported_actions:
        raise ObligationError(
            f"{path}: actions outside the bounded S3 scope: {', '.join(unsupported_actions)}"
        )
    if not isinstance(protected_asset, str) or "." not in protected_asset:
        raise ObligationError(f"{path}: protected_asset must be a Terraform address")
    if isinstance(scope, str):
        patterns = (scope,)
    elif isinstance(scope, list) and scope and all(isinstance(item, str) for item in scope):
        patterns = tuple(scope)
    else:
        raise ObligationError(f"{path}: resource_scope must be a string or list of strings")
    for pattern in patterns:
        if not pattern.startswith("arn:aws:s3:::"):
            raise ObligationError(
                f"{path}: resource_scope pattern is outside the bounded S3 model: {pattern}"
            )
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return Obligation(
        obligation_id=obligation_id,
        principal_address=principal,
        actions=tuple(actions),
        protected_asset=protected_asset,
        scope_patterns=patterns,
        content_hash=digest,
        source_file=str(path),
    )


def bind_baseline(project: Project, obligation: Obligation) -> Obligation:
    """Fill principal kind/name from the trusted baseline configuration."""
    node = project.get(obligation.principal_address)
    principal_kind = node.type if node is not None else None
    principal_name = literal_string(node.body.attr("name")) if node is not None else None
    return replace(
        obligation,
        principal_kind=principal_kind,
        principal_name=principal_name,
    )


def derive_boundary(project: Project, model: PolicyModel) -> DerivedBoundary:
    """Re-derive the S3 boundary carried by a configuration."""
    entries: dict = {}
    for provider in model.providers:
        principals = []
        if provider.kind == "managed":
            principals = list(model.attachments.get(provider.address, []))
        elif provider.inline_principal:
            principals = [provider.inline_principal]
        if not principals:
            continue
        for statement in provider.statements:
            if statement.effect.lower() == "deny":
                continue
            s3_actions = tuple(action for action in statement.actions if action.startswith("s3:"))
            if not s3_actions:
                continue
            targets = statement_targets(project, statement, statement.scope)
            for target in targets:
                asset = None
                concrete = True
                if target.kind == "address" and target.address:
                    node = project.get(target.address)
                    if node is None or node.type != "aws_s3_bucket":
                        continue
                    asset = target.address
                    if target.arn_pattern is None:
                        concrete = False
                        pattern = target.raw
                    else:
                        pattern = target.arn_pattern
                elif target.kind == "arn" and target.arn_pattern:
                    asset = _arn_to_bucket(project, target.arn_pattern)
                    if asset is None:
                        continue
                    pattern = target.arn_pattern
                else:
                    continue
                for principal in principals:
                    key = (principal, asset)
                    entry = entries.setdefault(
                        key,
                        {
                            "actions": set(),
                            "patterns": set(),
                            "providers": set(),
                            "count": 0,
                            "concrete": True,
                        },
                    )
                    entry["actions"].update(s3_actions)
                    entry["patterns"].add(pattern)
                    entry["providers"].add(provider.address)
                    entry["count"] += 1
                    entry["concrete"] = entry["concrete"] and concrete

    if not entries:
        raise BaselineValidationError(
            "baseline does not realize any S3 authorization boundary that can be derived"
        )
    if len(entries) > 1:
        described = "; ".join(
            f"{principal} -> {asset}" for principal, asset in sorted(entries)
        )
        raise BaselineValidationError(
            "baseline realizes more than one S3 boundary; the obligation must "
            f"disambiguate it (found: {described})"
        )
    (principal, asset), entry = next(iter(entries.items()))
    scope = tuple(sorted(entry["patterns"]))
    return DerivedBoundary(
        principal_address=principal,
        protected_asset=asset,
        actions=tuple(sorted(entry["actions"])),
        scope_patterns=scope,
        providers=tuple(sorted(entry["providers"])),
        statement_count=entry["count"],
        concrete_scope=entry["concrete"],
    )


def _arn_to_bucket(project: Project, arn_pattern: str) -> str | None:
    prefix = "arn:aws:s3:::"
    if not arn_pattern.startswith(prefix):
        return None
    name = arn_pattern[len(prefix) :].split("/", 1)[0].rstrip("*")
    for node in project.resources():
        if node.type != "aws_s3_bucket":
            continue
        literal = literal_string(node.body.attr("bucket"))
        if literal is not None and (literal == name or name == ""):
            return node.address
    return None


def validate_baseline(
    project: Project, model: PolicyModel, obligation: Obligation
) -> BaselineModel:
    """Independently check the trusted baseline against the obligation."""
    checks: list = []

    def add(check_id: str, title: str, status: str, expected, actual, detail: str) -> None:
        checks.append(
            {
                "id": check_id,
                "title": title,
                "status": status,
                "expected": expected,
                "actual": actual,
                "detail": detail,
            }
        )

    principal_node = project.get(obligation.principal_address)
    if principal_node is None:
        add(
            "principal_exists",
            "obligation principal exists in baseline",
            "fail",
            obligation.principal_address,
            None,
            "principal address not found in the trusted baseline",
        )
        raise BaselineValidationError(
            f"baseline does not define the obligation principal {obligation.principal_address}"
        )
    add(
        "principal_exists",
        "obligation principal exists in baseline",
        "pass",
        obligation.principal_address,
        principal_node.address,
        "principal found in the trusted baseline",
    )

    asset_node = project.get(obligation.protected_asset)
    if asset_node is None or asset_node.kind != "resource" or asset_node.type != "aws_s3_bucket":
        add(
            "asset_exists",
            "obligation protected asset exists in baseline",
            "fail",
            obligation.protected_asset,
            asset_node.address if asset_node else None,
            "protected asset address not found or is not an S3 bucket",
        )
        raise BaselineValidationError(
            f"baseline does not define the obligation protected asset {obligation.protected_asset}"
        )
    add(
        "asset_exists",
        "obligation protected asset exists in baseline",
        "pass",
        obligation.protected_asset,
        asset_node.address,
        "protected asset found in the trusted baseline",
    )

    derived = derive_boundary(project, model)

    if derived.principal_address != obligation.principal_address:
        add(
            "principal_match",
            "derived principal matches the obligation",
            "fail",
            obligation.principal_address,
            derived.principal_address,
            "the baseline boundary belongs to a different principal",
        )
    else:
        add(
            "principal_match",
            "derived principal matches the obligation",
            "pass",
            obligation.principal_address,
            derived.principal_address,
            "derived principal matches the obligation",
        )

    if derived.protected_asset != obligation.protected_asset:
        add(
            "asset_match",
            "derived protected asset matches the obligation",
            "fail",
            obligation.protected_asset,
            derived.protected_asset,
            "the baseline boundary governs a different asset",
        )
    else:
        add(
            "asset_match",
            "derived protected asset matches the obligation",
            "pass",
            obligation.protected_asset,
            derived.protected_asset,
            "derived protected asset matches the obligation",
        )

    if set(derived.actions) != set(obligation.actions):
        add(
            "actions_match",
            "derived action set matches the obligation",
            "fail",
            sorted(obligation.actions),
            sorted(derived.actions),
            "derived actions differ from the declared obligation",
        )
    else:
        add(
            "actions_match",
            "derived action set matches the obligation",
            "pass",
            sorted(obligation.actions),
            sorted(derived.actions),
            "derived action set matches the obligation",
        )

    if derived.concrete_scope:
        if set(derived.scope_patterns) != set(obligation.scope_patterns):
            add(
                "scope_match",
                "derived resource scope matches the obligation",
                "fail",
                sorted(obligation.scope_patterns),
                sorted(derived.scope_patterns),
                "derived scope differs from the declared obligation",
            )
        else:
            add(
                "scope_match",
                "derived resource scope matches the obligation",
                "pass",
                sorted(obligation.scope_patterns),
                sorted(derived.scope_patterns),
                "derived resource scope matches the obligation",
            )
    else:
        add(
            "scope_match",
            "derived resource scope matches the obligation",
            "pass",
            sorted(obligation.scope_patterns),
            "symbolic",
            "baseline bucket name is not literal; scope equality check skipped",
        )

    failures = [check for check in checks if check["status"] == "fail"]
    if failures:
        raise BaselineValidationError(
            "baseline does not realize its own obligation: "
            + "; ".join(f"{check['title']} ({check['detail']})" for check in failures)
        )

    authorization = evaluate(project, model, obligation, obligation.protected_asset)
    if authorization.status != "satisfied":
        raise BaselineValidationError(
            "baseline authorization check failed: " + authorization.reason()
        )
    add(
        "authorization",
        "baseline satisfies the obligation on the protected asset",
        "pass",
        "satisfied",
        authorization.status,
        "baseline authorization verified locally",
    )

    supporting = set(derived.providers) | {derived.principal_address, derived.protected_asset}
    for provider in model.providers:
        if provider.address in derived.providers and provider.document:
            supporting.add(provider.document)
    for node in project.resources():
        if node.type in ("aws_iam_role_policy_attachment", "aws_iam_policy_attachment"):
            if any(policy in node.refs for policy in derived.providers):
                supporting.add(node.address)
    return BaselineModel(
        obligation=obligation,
        derived=derived,
        checks=checks,
        supporting_nodes=tuple(sorted(supporting)),
        authorization=authorization,
    )
