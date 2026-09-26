"""P1 - dependency action capture.

A normalized record of a dependency-changing action.  In this first slice the
action arrives via an explicit CLI invocation (``python -m cavr check ...``);
that invocation *represents* the captured action and is the future hook point
for a real coding agent / package-manager interception.  Nothing here fakes
interception: the record simply states where the request came from.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from shared.errors import InputError

ECOSYSTEMS = ("pypi",)
ACTION_TYPES = ("install",)
REQUEST_SOURCES = ("cli", "agent-hook", "package-manager-hook")


@dataclass(frozen=True)
class DependencyAction:
    """Normalized dependency-changing action record (P1)."""

    ecosystem: str
    package: str
    version_spec: str
    action_type: str
    project: str
    source: str
    run_id: str
    timestamp: str

    def as_dict(self) -> dict:
        return {
            "ecosystem": self.ecosystem,
            "package": self.package,
            "version_spec": self.version_spec,
            "action_type": self.action_type,
            "project": self.project,
            "source": self.source,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
        }


def capture_action(
    package: str,
    version_spec: str,
    project: str,
    *,
    ecosystem: str = "pypi",
    action_type: str = "install",
    source: str = "cli",
) -> DependencyAction:
    """Build a :class:`DependencyAction` from explicit invocation inputs.

    Raises :class:`shared.errors.InputError` for values outside the bounded
    first-slice vocabulary.
    """
    if not package or not package.strip():
        raise InputError("dependency action requires a non-empty package name")
    if not version_spec or not version_spec.strip():
        raise InputError("dependency action requires a version specifier")
    if not project or not project.strip():
        raise InputError("dependency action requires a requesting project path")
    if ecosystem not in ECOSYSTEMS:
        raise InputError(
            f"unsupported ecosystem {ecosystem!r} (first slice supports {ECOSYSTEMS})"
        )
    if action_type not in ACTION_TYPES:
        raise InputError(
            f"unsupported action type {action_type!r} (first slice supports {ACTION_TYPES})"
        )
    if source not in REQUEST_SOURCES:
        raise InputError(
            f"unsupported request source {source!r} (expected one of {REQUEST_SOURCES})"
        )
    return DependencyAction(
        ecosystem=ecosystem,
        package=package.strip(),
        version_spec=version_spec.strip(),
        action_type=action_type,
        project=project,
        source=source,
        run_id=uuid.uuid4().hex,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
