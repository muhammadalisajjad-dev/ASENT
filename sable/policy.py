"""Bounded local IAM/S3 policy semantics for SABLE.

Only the subset needed for the least-privilege S3 obligation is modelled:
IAM policy documents (Terraform data documents, literal JSON and
``jsonencode``), policy attachments, principals, action sets and S3 resource
patterns.  Anything outside the subset is reported as an unsupported feature
instead of being guessed at.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from shared.model import Node, Project
from shared.values import (
    Bool,
    Call,
    ListVal,
    Null,
    Num,
    ObjectVal,
    Raw,
    Str,
    Template,
    literal_string,
    ref_address,
)

# Node families that belong to the authorization chain.  They are excluded
# from structural "references"/"dependency context" correspondence evidence so
# that re-wiring a policy is evaluated as policy evidence instead of being
# double counted as structural continuity.
AUTH_FAMILIES = frozenset(
    {
        "resource:aws_iam_policy",
        "resource:aws_iam_role_policy",
        "resource:aws_iam_user_policy",
        "resource:aws_iam_group_policy",
        "resource:aws_iam_role_policy_attachment",
        "resource:aws_iam_policy_attachment",
        "resource:aws_iam_role",
        "resource:aws_iam_user",
        "resource:aws_iam_group",
        "resource:aws_s3_bucket_policy",
        "data:aws_iam_policy_document",
    }
)

_POLICY_TYPES = {
    "aws_iam_policy": "managed",
    "aws_iam_role_policy": "inline",
    "aws_iam_user_policy": "inline",
    "aws_iam_group_policy": "inline",
    "aws_s3_bucket_policy": "bucket",
}

_INLINE_PRINCIPAL_ATTR = {
    "aws_iam_role_policy": "role",
    "aws_iam_user_policy": "user",
    "aws_iam_group_policy": "group",
    "aws_s3_bucket_policy": "bucket",
}

_BUCKET_LEVEL_ACTIONS = frozenset(
    {
        "s3:ListBucket",
        "s3:ListBucketVersions",
        "s3:ListBucketMultipartUploads",
        "s3:GetBucketLocation",
        "s3:GetBucketAcl",
        "s3:GetBucketPolicy",
        "s3:GetBucketPolicyStatus",
        "s3:GetBucketVersioning",
        "s3:GetBucketCors",
        "s3:GetBucketEncryption",
        "s3:GetBucketLifecycleConfiguration",
        "s3:GetBucketLogging",
        "s3:GetBucketNotification",
        "s3:GetBucketOwnershipControls",
        "s3:GetBucketPublicAccessBlock",
        "s3:GetBucketRequestPayment",
        "s3:GetBucketTagging",
        "s3:PutBucket*",
    }
)

_OBJECT_LEVEL_ACTIONS = frozenset(
    {
        "s3:GetObject",
        "s3:GetObjectAcl",
        "s3:GetObjectAttributes",
        "s3:GetObjectLegalHold",
        "s3:GetObjectRetention",
        "s3:GetObjectTagging",
        "s3:GetObjectVersion",
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:PutObjectTagging",
        "s3:DeleteObject",
        "s3:DeleteObjectVersion",
        "s3:RestoreObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts",
    }
)


def node_family(node: Node) -> str:
    return f"{node.kind}:{node.type or '-'}"


def glob_match(pattern: str, text: str) -> bool:
    """Glob match with ``*``/``?`` semantics (no character classes)."""
    return re.match(_glob_regex(pattern), text) is not None


_GLOB_CACHE: dict = {}


def _glob_regex(pattern: str) -> str:
    cached = _GLOB_CACHE.get(pattern)
    if cached is not None:
        return cached
    out = []
    for ch in pattern:
        if ch == "*":
            out.append(".*")
        elif ch == "?":
            out.append(".")
        else:
            out.append(re.escape(ch))
    regex = "^" + "".join(out) + "$"
    _GLOB_CACHE[pattern] = regex
    return regex


def action_covers(pattern: str, action: str) -> bool:
    """True when an IAM action pattern grants ``action``."""
    return glob_match(pattern, action)


def action_in_obligation(action: str, obligation_actions: tuple) -> bool:
    """True when a candidate action stays within the obligation action set."""
    if "*" not in action and "?" not in action:
        return any(action_covers(allowed, action) for allowed in obligation_actions)
    # A wildcard candidate action is only acceptable if the obligation grants
    # exactly the same pattern (an identical wildcard cannot be narrowed here).
    return action in obligation_actions


def s3_action_level(action: str) -> str | None:
    if action in _BUCKET_LEVEL_ACTIONS or any(
        action_covers(pattern, action) for pattern in _BUCKET_LEVEL_ACTIONS if "*" in pattern
    ):
        return "bucket"
    if action in _OBJECT_LEVEL_ACTIONS:
        return "objects"
    return None


def s3_pattern_level(pattern: str) -> str:
    if pattern.endswith("/*"):
        return "objects"
    if "*" in pattern or "?" in pattern:
        return "unknown"
    return "bucket"


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _literal_strings(value) -> tuple | None:
    """Return literal strings from a value, or None if any part is dynamic."""
    if value is None:
        return None
    if isinstance(value, Str):
        return (value.value,)
    if isinstance(value, Template):
        out = []
        for part in value.parts:
            if isinstance(part, str):
                out.append(part)
            else:
                return None
        return ("".join(out),)
    if isinstance(value, ListVal):
        out = []
        for item in value.items:
            strings = _literal_strings(item)
            if strings is None or len(strings) != 1:
                return None
            out.append(strings[0])
        return tuple(out)
    return None


@dataclass
class Statement:
    """One IAM policy statement."""

    source: str
    effect: str
    actions: tuple
    resource_values: tuple
    principals: tuple | None = None
    unsupported: tuple = ()
    has_not_actions: bool = False
    has_not_resources: bool = False
    scope: tuple = ()

    @property
    def is_allow(self) -> bool:
        return self.effect.lower() != "deny"


@dataclass
class Provider:
    """A policy carrier: managed policy, inline policy or bucket policy."""

    address: str
    kind: str  # managed | inline | bucket
    statements: tuple
    inline_principal: str | None = None
    document: str | None = None
    unsupported: tuple = ()
    resolved: bool = True


@dataclass
class PolicyModel:
    """Policy carriers plus the principal attachment graph of a project."""

    project: Project
    providers: tuple
    attachments: dict  # managed policy address -> [principal addresses]
    doc_statements: dict  # data document address -> [Statement]
    unsupported: tuple = ()

    def providers_for_principal(self, principal_address: str) -> list:
        out = []
        for provider in self.providers:
            if provider.kind == "managed":
                if principal_address in self.attachments.get(provider.address, []):
                    out.append(provider)
            elif provider.inline_principal == principal_address:
                out.append(provider)
        return out

    def bucket_providers(self, bucket_address: str) -> list:
        return [
            provider
            for provider in self.providers
            if provider.kind == "bucket" and provider.inline_principal == bucket_address
        ]


def build_policy_model(project: Project) -> PolicyModel:
    doc_statements: dict = {}
    unsupported: list = []
    for node in project.data_of_type("aws_iam_policy_document"):
        statements, notes = _document_statements(node, project)
        doc_statements[node.address] = statements
        unsupported.extend(f"{node.address}: {note}" for note in notes)

    providers: list = []
    for node in project.resources():
        policy_type = node.type if node.type in _POLICY_TYPES else None
        if policy_type is None:
            continue
        statements, notes, document, resolved = _policy_statements(node, project, doc_statements)
        inline_principal = None
        principal_attr = _INLINE_PRINCIPAL_ATTR.get(node.type)
        if principal_attr is not None:
            inline_principal = _resolve_principal_ref(node, principal_attr, project)
            if inline_principal is None:
                notes.append(f"{principal_attr} reference is not resolvable")
        providers.append(
            Provider(
                address=node.address,
                kind=_POLICY_TYPES[policy_type],
                statements=tuple(statements),
                inline_principal=inline_principal,
                document=document,
                unsupported=tuple(notes),
                resolved=resolved,
            )
        )
        unsupported.extend(f"{node.address}: {note}" for note in notes)

    attachments = _attachment_graph(project)
    return PolicyModel(
        project=project,
        providers=tuple(providers),
        attachments=attachments,
        doc_statements=doc_statements,
        unsupported=tuple(dict.fromkeys(unsupported)),
    )


def _document_statements(node: Node, project: Project) -> tuple:
    statements: list = []
    notes: list = []
    for body in node.body.blocks_of("statement"):
        statement, statement_notes = _statement_from_body(body, node.address, node.module_path, project)
        notes.extend(statement_notes)
        if statement is not None:
            statements.append(statement)
    return statements, notes


def _statement_from_body(body, source: str, scope: tuple, project: Project):
    notes: list = []
    effect_value = body.attr("effect")
    effect = "Allow"
    if effect_value is not None:
        literal = _literal_strings(effect_value)
        if literal is None or len(literal) != 1:
            notes.append("statement effect is not a literal")
        else:
            effect = literal[0]

    actions: list = []
    for key in ("actions", "action"):
        value = body.attr(key)
        if value is None:
            continue
        strings = _literal_strings(value)
        if strings is None:
            notes.append(f"statement {key} is not a literal list")
        else:
            actions.extend(strings)

    if body.attr("not_actions") is not None:
        notes.append("NotAction is outside the supported subset")
    if body.attr("not_resources") is not None:
        notes.append("NotResource is outside the supported subset")
    for block_type in ("condition",):
        if body.blocks_of(block_type):
            notes.append(f"policy {block_type} is outside the supported subset")

    resource_values: list = []
    for key in ("resources", "resource"):
        value = body.attr(key)
        if value is None:
            continue
        if isinstance(value, ListVal):
            resource_values.extend(value.items)
        else:
            resource_values.append(value)
    if not resource_values:
        notes.append("statement has no resources")

    principals = None
    principal_blocks = body.blocks_of("principals")
    if principal_blocks:
        identifiers: list = []
        for block in principal_blocks:
            strings = _literal_strings(block.attr("identifiers"))
            if strings is None:
                notes.append("principals identifiers are not literal")
            else:
                identifiers.extend(strings)
        principals = tuple(identifiers)

    statement = Statement(
        source=source,
        effect=effect,
        actions=tuple(actions),
        resource_values=tuple(resource_values),
        principals=principals,
        unsupported=tuple(notes),
        scope=scope,
    )
    return statement, notes


def _policy_statements(node: Node, project: Project, doc_statements: dict) -> tuple:
    notes: list = []
    policy_value = node.body.attr("policy")
    if policy_value is None:
        return [], ["policy attribute is missing"], None, False

    # data "aws_iam_policy_document" referenced through .json
    document = _document_reference(policy_value, node, project)
    if document is not None:
        statements = doc_statements.get(document)
        if statements is None:
            return [], [f"referenced policy document {document} was not parsed"], document, False
        return list(statements), notes, document, True

    literal = literal_string(policy_value)
    if literal is not None:
        stripped = literal.strip()
        if stripped.startswith("{"):
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                return [], [f"policy JSON is not valid: {exc}"], None, False
            statements, json_notes = _statements_from_json(data, node.address, node.module_path)
            notes.extend(json_notes)
            return statements, notes, None, True
        return [], ["policy attribute is not a JSON policy document"], None, False

    if isinstance(policy_value, Call) and policy_value.name == "jsonencode":
        data = _value_to_python(policy_value.args[0]) if policy_value.args else None
        if data is None:
            return [], ["jsonencode policy contains non-literal expressions"], None, False
        statements, json_notes = _statements_from_json(data, node.address, node.module_path)
        notes.extend(json_notes)
        return statements, notes, None, True

    source_json = node.body.attr("source_json")
    override_json = node.body.attr("override_json")
    if source_json is not None or override_json is not None:
        return [], ["source_json/override_json are outside the supported subset"], None, False
    return [], ["policy expression is outside the supported subset"], None, False


def _document_reference(value, node: Node, project: Project) -> str | None:
    """Recognize ``data.aws_iam_policy_document.<name>.json`` references."""
    path = None
    if hasattr(value, "path"):
        path = value.path
    elif isinstance(value, Template):
        refs = [part for part in value.parts if not isinstance(part, str)]
        if len(refs) == 1 and hasattr(refs[0], "path"):
            path = refs[0].path
    if path is None:
        return None
    if len(path) < 3 or path[0] != "data":
        return None
    address = ref_address(path, node.module_path)
    return address


def _statements_from_json(data, source: str, scope: tuple = ()) -> tuple:
    notes: list = []
    if not isinstance(data, dict):
        return [], ["policy JSON must be an object"]
    raw_statements = data.get("Statement", [])
    if not isinstance(raw_statements, list):
        return [], ["policy JSON Statement must be a list"]
    statements: list = []
    for entry in raw_statements:
        if not isinstance(entry, dict):
            notes.append("policy JSON statement must be an object")
            continue
        if "Condition" in entry:
            notes.append("policy JSON Condition is outside the supported subset")
        if "NotAction" in entry:
            notes.append("policy JSON NotAction is outside the supported subset")
        if "NotResource" in entry:
            notes.append("policy JSON NotResource is outside the supported subset")
        effect = str(entry.get("Effect", "Allow"))
        actions = entry.get("Action", [])
        resources = entry.get("Resource", [])
        action_values = tuple(Str(str(item)) for item in _as_list(actions))
        resource_values = tuple(Str(str(item)) for item in _as_list(resources))
        principals = None
        raw_principals = entry.get("Principal")
        if isinstance(raw_principals, dict):
            identifiers = []
            for value in raw_principals.values():
                identifiers.extend(str(item) for item in _as_list(value))
            principals = tuple(identifiers)
        elif isinstance(raw_principals, str):
            principals = (raw_principals,)
        statements.append(
            Statement(
                source=source,
                effect=effect,
                actions=action_values,
                resource_values=resource_values,
                principals=principals,
                scope=scope,
            )
        )
    if not statements:
        notes.append("policy JSON contains no statements")
    return statements, notes


def _value_to_python(value):
    if isinstance(value, Str):
        return value.value
    if isinstance(value, Num):
        try:
            return int(value.raw)
        except ValueError:
            try:
                return float(value.raw)
            except ValueError:
                return None
    if isinstance(value, Bool):
        return value.value
    if isinstance(value, Null):
        return None
    if isinstance(value, ListVal):
        out = []
        for item in value.items:
            converted = _value_to_python(item)
            if converted is None and not isinstance(item, Null):
                return None
            out.append(converted)
        return out
    if isinstance(value, ObjectVal):
        out = {}
        for key, item in value.entries:
            converted = _value_to_python(item)
            if converted is None and not isinstance(item, Null):
                return None
            out[key] = converted
        return out
    if isinstance(value, Template):
        text = []
        for part in value.parts:
            if isinstance(part, str):
                text.append(part)
            else:
                converted = _value_to_python(part)
                if converted is None or not isinstance(converted, str):
                    return None
                text.append(converted)
        return "".join(text)
    if isinstance(value, Call) and value.name == "jsonencode" and value.args:
        inner = _value_to_python(value.args[0])
        if inner is None:
            return None
        return inner
    return None


def _resolve_principal_ref(node: Node, attr: str, project: Project) -> str | None:
    value = node.body.attr(attr)
    if value is None:
        return None
    address, _suffix = resolve_reference(project, value, node.module_path)
    if address is not None and project.get(address) is not None:
        return address
    literal = literal_string(value) if not hasattr(value, "path") else None
    if literal is None and isinstance(value, Template):
        literal = literal_string(value)
    if literal:
        return _find_by_name(project, literal)
    return None


def _find_by_name(project: Project, name: str) -> str | None:
    matches = [
        node.address
        for node in project.resources()
        if node.type in ("aws_iam_role", "aws_iam_user", "aws_iam_group", "aws_s3_bucket")
        and literal_string(node.body.attr("name") or node.body.attr("bucket") or Raw(""))
        == name
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _attachment_graph(project: Project) -> dict:
    """Map managed policy addresses to the principals they are attached to."""
    attachments: dict = {}
    managed_names = {
        literal_string(node.body.attr("name"))
        for node in project.resources()
        if node.type == "aws_iam_policy"
    }

    def attach(policy_address: str | None, principal_address: str | None) -> None:
        if policy_address is None or principal_address is None:
            return
        attachments.setdefault(policy_address, [])
        if principal_address not in attachments[policy_address]:
            attachments[policy_address].append(principal_address)

    def resolve_policy(value, node: Node) -> str | None:
        address, _suffix = resolve_reference(project, value, node.module_path)
        if address is not None and project.get(address) is not None:
            return address
        literal = literal_string(value)
        if literal and literal.startswith("arn:aws:iam::"):
            policy_name = literal.rsplit("/", 1)[-1]
            if policy_name in managed_names:
                for candidate in project.resources():
                    if candidate.type == "aws_iam_policy" and literal_string(
                        candidate.body.attr("name")
                    ) == policy_name:
                        return candidate.address
        return None

    def principals_of(node: Node, attr: str) -> list:
        value = node.body.attr(attr)
        if value is None:
            return []
        out = []
        items = value.items if isinstance(value, ListVal) else [value]
        for item in items:
            address, _suffix = resolve_reference(project, item, node.module_path)
            if address is not None and project.get(address) is not None:
                out.append(address)
                continue
            literal = literal_string(item)
            if literal:
                found = _find_by_name(project, literal)
                if found:
                    out.append(found)
        return out

    for node in project.resources():
        if node.type == "aws_iam_role_policy_attachment":
            policy_address = resolve_policy(node.body.attr("policy_arn") or Raw(""), node)
            for principal in principals_of(node, "role"):
                attach(policy_address, principal)
        elif node.type == "aws_iam_policy_attachment":
            policy_address = resolve_policy(node.body.attr("policy_arn") or Raw(""), node)
            for attr in ("roles", "users", "groups"):
                for principal in principals_of(node, attr):
                    attach(policy_address, principal)
    return attachments


def resolve_reference(project: Project, value, scope: tuple) -> tuple:
    """Resolve a value to ``(address, suffix)`` for resource-like references.

    ``suffix`` carries trailing text such as ``/*`` from template strings.
    Module output references are unwrapped when the output value is a plain
    reference (optionally with a literal suffix).
    """
    path = None
    suffix = ""
    if hasattr(value, "path"):
        path = value.path
    elif isinstance(value, Template):
        refs = [part for part in value.parts if not isinstance(part, str)]
        literals = [part for part in value.parts if isinstance(part, str)]
        if len(refs) == 1 and len(literals) <= 2 and hasattr(refs[0], "path"):
            path = refs[0].path
            suffix = "".join(literals)
        else:
            return None, ""
    else:
        return None, ""

    if not path:
        return None, ""
    address = ref_address(path, scope)
    if address is None:
        return None, ""
    if path[0] == "module" and len(path) >= 3:
        unwrapped = _unwrap_module_output(project, address, path[2])
        if unwrapped is not None:
            inner_address, inner_suffix = unwrapped
            return inner_address, inner_suffix + suffix
    return address, suffix


def _unwrap_module_output(project: Project, module_address: str, output_name: str) -> tuple | None:
    node = project.get(f"{module_address}.output.{output_name}")
    if node is None:
        return None
    value = node.body.attr("value")
    if value is None:
        return None
    address, suffix = resolve_reference(project, value, node.module_path)
    if address is None:
        return None
    return address, suffix


@dataclass
class Target:
    """A resolved S3 resource target of a policy statement."""

    raw: str
    kind: str  # global | arn | address | unresolved
    address: str | None = None
    arn_pattern: str | None = None
    level: str = "unknown"
    note: str | None = None


def render_value(value) -> str:
    """Deterministic text rendering of a policy resource value."""
    literal = literal_string(value)
    if literal is not None:
        return literal
    if hasattr(value, "path"):
        return ".".join(str(part) for part in value.path)
    if isinstance(value, Template):
        parts = []
        for part in value.parts:
            if isinstance(part, str):
                parts.append(part)
            elif hasattr(part, "path"):
                parts.append(".".join(str(p) for p in part.path))
            else:
                parts.append("?")
        return "".join(parts)
    return str(value)


def resolve_target(project: Project, value, scope: tuple) -> Target:
    raw = render_value(value)
    literal = literal_string(value)
    if literal is not None:
        pattern = literal.strip()
        if pattern == "*":
            return Target(raw=raw, kind="global", level="unknown")
        return Target(
            raw=raw,
            kind="arn",
            arn_pattern=pattern,
            level=s3_pattern_level(pattern),
        )

    address, suffix = resolve_reference(project, value, scope)
    if address is None:
        return Target(raw=raw, kind="unresolved", note="expression is not a resolvable reference")
    node = project.get(address)
    if node is None:
        return Target(raw=raw, kind="unresolved", address=address, note="reference target not found")

    concrete = None
    if node.type == "aws_s3_bucket":
        bucket_value = node.body.attr("bucket")
        if bucket_value is not None:
            concrete = literal_string(bucket_value)
    if concrete:
        arn_pattern = f"arn:aws:s3:::{concrete}{suffix}"
        level = s3_pattern_level(arn_pattern)
        return Target(raw=raw, kind="address", address=address, arn_pattern=arn_pattern, level=level)
    level = "objects" if suffix == "/*" else ("bucket" if suffix == "" else "unknown")
    return Target(
        raw=raw,
        kind="address",
        address=address,
        arn_pattern=None,
        level=level,
        note="protected resource name is not a literal; ARN scope cannot be confirmed",
    )


def statement_targets(project: Project, statement: Statement, scope: tuple) -> list:
    if not statement.resource_values:
        return [
            Target(raw="<missing>", kind="unresolved", note="statement declares no resources")
        ]
    return [resolve_target(project, value, scope) for value in statement.resource_values]


def covers(target: Target, obligation_pattern: str) -> bool | None:
    """Whether a target applies to an obligation ARN pattern.

    ``None`` means the relationship cannot be decided from local evidence.
    """
    if target.kind == "global":
        return True
    if target.kind == "arn":
        return glob_match(target.arn_pattern or "", obligation_pattern)
    if target.kind == "address":
        if target.arn_pattern is not None:
            return glob_match(target.arn_pattern, obligation_pattern)
        return None
    return None


def is_broader(target: Target, obligation_patterns: tuple) -> bool:
    """Whether a target reaches beyond the obligation's resource scope."""
    if target.kind == "global":
        return bool(obligation_patterns)
    if target.kind == "arn" and target.arn_pattern is not None:
        for pattern in obligation_patterns:
            if glob_match(target.arn_pattern, pattern) and target.arn_pattern != pattern:
                return True
        return False
    if target.kind == "address" and target.arn_pattern is not None:
        for pattern in obligation_patterns:
            if glob_match(target.arn_pattern, pattern) and target.arn_pattern != pattern:
                return True
    return False
