"""P2 - requirement / policy gate.

Reads a simple local project policy (allowlist + version requirements) and
answers PERMITTED or BLOCK *before* any package security analysis happens.

PERMITTED does NOT mean TRUSTED.  The gate only says the requested dependency
is allowed by the approved project requirements; CAVR still has to verify the
package's behavior before its state reaches the trusted project.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from cavr.capture import DependencyAction
from shared.errors import InputError

PERMITTED = "PERMITTED"
BLOCK = "BLOCK"

_SPEC_RE = re.compile(r"^\s*(==|!=|>=|<=|~=|>|<)?\s*(.*?)\s*$")


def normalize_name(name: str) -> str:
    """Normalize a distribution name for comparison (PEP 503-ish)."""
    return re.sub(r"[-_.]+", "-", name.strip()).lower()


def load_policy(path: str | Path) -> dict:
    """Load the project requirement policy JSON file."""
    policy_path = Path(path)
    if not policy_path.is_file():
        raise InputError(f"policy file not found: {policy_path}")
    try:
        data = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"cannot read policy file {policy_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"policy file {policy_path} must contain a JSON object")
    return data


def _version_key(version: str) -> tuple:
    """Split a version into comparable numeric/string components."""
    parts = []
    for piece in re.split(r"[.\-+]", version.strip()):
        if piece.isdigit():
            parts.append((0, int(piece), ""))
        else:
            parts.append((1, 0, piece))
    return tuple(parts)


def version_satisfies(version: str, specifier: str) -> bool:
    """Minimal version-specifier evaluation (``== != >= <= > < ~=`` and bare).

    This is deliberately not a full PEP 440 implementation; the bounded first
    slice only needs deterministic matching for fixture versions like
    ``==1.0.0``.  The limitation is reported as residual uncertainty.
    """
    match = _SPEC_RE.match(specifier or "")
    if match is None:
        raise InputError(f"cannot parse version specifier {specifier!r}")
    operator = match.group(1) or "=="
    expected = match.group(2)
    if expected in ("", "*"):
        return True
    actual = version.strip()
    if operator == "==":
        return actual == expected
    if operator == "!=":
        return actual != expected
    try:
        left, right = _version_key(actual), _version_key(expected)
    except TypeError as exc:
        raise InputError(f"incomparable versions {version!r} vs {expected!r}") from exc
    if operator == ">=":
        return left >= right
    if operator == "<=":
        return left <= right
    if operator == ">":
        return left > right
    if operator == "<":
        return left < right
    if operator == "~=":
        if left < right:
            return False
        # compatible release: same leading components as the expected prefix
        prefix = expected.split(".")
        actual_parts = re.split(r"[.\-+]", actual)
        return actual_parts[: len(prefix) - 1] == prefix[:-1]
    raise InputError(f"unsupported version operator {operator!r}")


@dataclass(frozen=True)
class RequirementDecision:
    """Outcome of the P2 gate: PERMITTED or BLOCK, with evidence."""

    decision: str
    requested: dict
    matched_rule: str | None
    reason: str

    @property
    def permitted(self) -> bool:
        return self.decision == PERMITTED

    def as_dict(self) -> dict:
        return {
            "decision": self.decision,
            "requested": dict(self.requested),
            "matched_rule": self.matched_rule,
            "reason": self.reason,
            "note": "PERMITTED means allowed by requirements, not trusted",
        }


def evaluate_requirement(action: DependencyAction, policy: dict) -> RequirementDecision:
    """Evaluate the captured action against the project policy."""
    requested = {
        "package": action.package,
        "version_spec": action.version_spec,
        "action_type": action.action_type,
        "ecosystem": action.ecosystem,
    }
    allowed = policy.get("allowed_dependencies")
    if not isinstance(allowed, dict):
        raise InputError('policy requires an "allowed_dependencies" object')

    wanted = normalize_name(action.package)
    match_key = None
    for key in allowed:
        if normalize_name(str(key)) == wanted:
            match_key = key
            break

    if match_key is None:
        return RequirementDecision(
            decision=BLOCK,
            requested=requested,
            matched_rule=None,
            reason=(
                f"package {action.package!r} is not listed in allowed_dependencies"
            ),
        )

    rule_value = allowed[match_key]
    if isinstance(rule_value, list):
        specifiers = [str(v) for v in rule_value]
    elif rule_value is None:
        specifiers = ["*"]
    else:
        specifiers = [str(rule_value)]

    # The action carries a concrete target version (or a range); the gate
    # checks it against every accepted specifier for this package.
    target = action.version_spec.strip()
    if target.startswith(("==", ">=", "<=", "~=", ">", "<", "!=")):
        target_version = _SPEC_RE.match(target).group(2)  # type: ignore[union-attr]
    else:
        target_version = target

    for specifier in specifiers:
        try:
            if version_satisfies(target_version, specifier):
                return RequirementDecision(
                    decision=PERMITTED,
                    requested=requested,
                    matched_rule=f"{match_key} {specifier}",
                    reason=(
                        f"requested {action.package} {action.version_spec} satisfies "
                        f"project requirement {match_key} {specifier}"
                    ),
                )
        except InputError:
            continue

    return RequirementDecision(
        decision=BLOCK,
        requested=requested,
        matched_rule=f"{match_key} {' | '.join(specifiers)}",
        reason=(
            f"requested version {action.version_spec!r} does not satisfy "
            f"project requirement {match_key} {' | '.join(specifiers)}"
        ),
    )
