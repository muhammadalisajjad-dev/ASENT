"""Machine-readable evidence document for every CAVR run.

All stages contribute an ``as_dict()`` section; this module assembles them
into one schema-versioned JSON document, provides a stable digest over the
non-volatile analysis content (for deterministic-repetition checks) and a
compact human summary mode.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys

SCHEMA_VERSION = "asent.cavr.evidence/0.1"

# Fields that legitimately vary between identical repeated runs.
_VOLATILE_KEYS = frozenset(
    {
        "run_id",
        "timestamp",
        "generated_at",
        "duration_ms",
        "stdout",
        "stderr",
        "workdir",
    }
)

# Top-level fields covered by the deterministic digest.
_STABLE_FIELDS = (
    "package",
    "requirement",
    "project",
    "capability_contract",
    "triggers",
    "environments",
    "events",
    "artifact_checks",
    "observed_capabilities",
    "prohibited_capabilities",
    "violations",
    "decision",
    "decision_reason",
    "coverage",
)


def build_evidence(
    *,
    action: dict,
    requirement: dict,
    package: dict,
    project: dict,
    capability_contract: dict,
    triggers: dict,
    environments: list,
    runs: list,
    events: list,
    artifact_checks: list,
    observed: list,
    prohibited: list,
    decision: str,
    decision_reason: str,
    violations: list,
    residual_uncertainty: list,
    coverage: dict,
    isolation: dict,
    prototype_parameters: dict,
    phase_reached: str,
    analysis_performed: bool,
) -> dict:
    """Assemble the complete evidence document."""
    import datetime as _dt

    return {
        "schema_version": SCHEMA_VERSION,
        "module": "CAVR",
        "phase_reached": phase_reached,
        "analysis_performed": analysis_performed,
        "run_id": action.get("run_id"),
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(
            timespec="seconds"
        ),
        "action": dict(action),
        "requirement": dict(requirement),
        "package": dict(package),
        "project": dict(project),
        "capability_contract": dict(capability_contract),
        "triggers": dict(triggers),
        "environments": list(environments),
        "execution_runs": [dict(run) for run in runs],
        "events": [dict(event) for event in events],
        "artifact_checks": [dict(check) for check in artifact_checks],
        "observed_capabilities": list(observed),
        "prohibited_capabilities": list(prohibited),
        "violations": [dict(v) for v in violations],
        "decision": decision,
        "decision_reason": decision_reason,
        "coverage": dict(coverage),
        "residual_uncertainty": list(residual_uncertainty),
        "isolation": dict(isolation),
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "prototype_parameters": dict(prototype_parameters),
        "bounded_claim": (
            "CAVR intercepted a dependency action, established a declared "
            "project-specific capability boundary, exercised supported "
            "security-sensitive conditions in a disposable environment, "
            "observed resulting behavior and produced this evidence-backed "
            "bounded decision. It does not establish general package safety."
        ),
    }


def _strip(value):
    if isinstance(value, dict):
        return {
            key: _strip(item)
            for key, item in value.items()
            if key not in _VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_strip(item) for item in value]
    return value


def stable_digest(document: dict) -> str:
    """SHA-256 over the non-volatile analysis content of the evidence."""
    stable = {field: _strip(document.get(field)) for field in _STABLE_FIELDS}
    payload = json.dumps(stable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_evidence(document: dict, path: str | Path) -> Path:
    """Write the evidence document as pretty-printed JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    return target


def load_evidence(path: str | Path) -> dict:
    source = Path(path)
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        from shared.errors import InputError

        raise InputError(f"cannot read evidence file {source}: {exc}") from exc


def summarize(document: dict) -> str:
    """Compact human-readable summary of an evidence document."""
    package = document.get("package", {})
    contract = document.get("capability_contract", {})
    triggers = document.get("triggers", {}).get("triggers", [])
    requirement = document.get("requirement", {}).get("decision", "?")
    observed = ", ".join(document.get("observed_capabilities", [])) or "none"
    analyzed = document.get("analysis_performed", True)

    version = package.get("version") or package.get("version_spec") or "?"
    artifact = package.get("artifact_hash")
    artifact_text = f"sha256:{artifact}" if artifact else "n/a (not resolved)"

    lines = [
        "CAVR dependency check",
        f"  package:     {package.get('name', '?')} {version}",
        f"  artifact:    {artifact_text}",
        f"  requirement: {requirement} ({document.get('requirement', {}).get('reason', '')})",
    ]
    if not analyzed:
        lines.append("  analysis:    not performed (stopped at requirement gate)")
        lines.append(f"  decision:    {document.get('decision', '?')}")
        lines.append(f"  reason:      {document.get('decision_reason', '')}")
        lines.append(f"  digest:      sha256:{stable_digest(document)}")
        return "\n".join(lines)

    lines.extend(
        [
            f"  intent:      {_short(document.get('project', {}).get('intent', ''))}",
            f"  contract:    required={list(contract.get('required', []))} "
            f"prohibited={list(contract.get('prohibited', []))}",
            f"  triggers:    {len(triggers)} discovered, "
            f"{sum(1 for t in triggers if t.get('activatable'))} activatable",
            "  environments:"
            + ", ".join(
                env.get("label", "?") for env in document.get("environments", [])
            ),
            f"  observed:    {observed}",
            f"  decision:    {document.get('decision', '?')}",
            f"  reason:      {document.get('decision_reason', '')}",
        ]
    )
    for violation in document.get("violations", []):
        lines.append(
            f"  violation:   {violation.get('type')} "
            f"({violation.get('capability')}) in "
            f"{','.join(violation.get('observed_in', []))}"
        )
    uncertainty = document.get("residual_uncertainty", [])
    lines.append(f"  uncertainty: {len(uncertainty)} note(s)")
    lines.append(f"  digest:      sha256:{stable_digest(document)}")
    return "\n".join(lines)


def _short(text: str, limit: int = 100) -> str:
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."
