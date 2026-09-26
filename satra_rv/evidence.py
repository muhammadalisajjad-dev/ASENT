"""Machine-readable evidence document for every SATRA-RV run.

Each stage contributes a section; this module assembles them into one
schema-versioned JSON document, provides a stable digest over the
non-volatile analysis content (for deterministic-repetition checks) and a
compact human summary.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys

SCHEMA_VERSION = "asent.satra_rv.evidence/0.1"

# Fields that legitimately vary between identical repeated runs.
_VOLATILE_KEYS = frozenset(
    {
        "generated_at",
        "timestamp",
        "duration_ms",
        "elapsed_ms",
        "command",
        "run_id",
    }
)

# Top-level fields covered by the deterministic digest.
_STABLE_FIELDS = (
    "inputs",
    "capture",
    "localization",
    "contract",
    "dictionary",
    "execution",
    "differential",
    "decision",
    "decision_reason",
    "findings",
    "coverage",
)


def build_evidence(
    *,
    inputs: dict,
    capture: dict,
    localization: dict,
    contract: dict,
    dictionary: dict,
    execution: dict,
    differential: dict,
    decision: str,
    decision_reason: str,
    findings: list,
    coverage: dict,
    residual_uncertainty: list,
    prototype_parameters: dict,
) -> dict:
    """Assemble the complete evidence document."""
    import datetime as _dt

    return {
        "schema_version": SCHEMA_VERSION,
        "module": "SATRA-RV",
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(
            timespec="seconds"
        ),
        "inputs": dict(inputs),
        "capture": dict(capture),
        "localization": dict(localization),
        "contract": dict(contract),
        "dictionary": dict(dictionary),
        "execution": dict(execution),
        "differential": dict(differential),
        "decision": decision,
        "decision_reason": decision_reason,
        "findings": [dict(f) for f in findings],
        "coverage": dict(coverage),
        "residual_uncertainty": list(residual_uncertainty),
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "prototype_parameters": dict(prototype_parameters),
        "bounded_claim": (
            "SATRA-RV captured the change between a trusted baseline and a "
            "candidate Flask application, localized the security-sensitive "
            "changed region, declared a Security Change Contract from a "
            "trusted dictionary, executed deterministic authorization probes "
            "against both sides and produced this evidence-backed bounded "
            "decision. It does not establish general security of the "
            "candidate change."
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
    capture = document.get("capture", {})
    localization = document.get("localization", {})
    contract = document.get("contract", {})
    differential = document.get("differential", {})
    counts = contract.get("counts", {})
    regions = localization.get("regions", [])
    primary = localization.get("primary") or {}

    changed = capture.get("changed_paths", [])
    lines = [
        "SATRA-RV security change review",
        f"  baseline:   {capture.get('baseline', {}).get('dir', '?')}",
        f"  candidate:  {capture.get('candidate', {}).get('dir', '?')}",
        "  changed:    "
        + (f"{len(changed)} file(s): {', '.join(changed)}" if changed else "none"),
        "  regions:    "
        + (
            f"{len(regions)} localized "
            f"({primary.get('security_family', '?')}, "
            f"{primary.get('method') or '?'} {primary.get('route') or '?'})"
            if regions
            else "none localized"
        ),
        "  contract:   "
        + (
            f"{counts.get('total', 0)} obligation(s) "
            f"({counts.get('security_denials', 0)} security denials, "
            f"{counts.get('required_behavior', 0)} required behavior)"
            if contract.get("scope", {}).get("localized")
            else "not bound (no localized security region)"
        ),
        "  probes:     "
        + ", ".join(
            f"{side} {section.get('satisfied_count', 0)}/{section.get('probe_count', 0)}"
            for side, section in document.get("execution", {}).items()
            if isinstance(section, dict) and "satisfied_count" in section
        ),
        f"  comparisons:{differential.get('comparison_count', 0)}"
        f" compared, {differential.get('regression_count', 0)} regression(s)",
        f"  decision:   {document.get('decision', '?')}",
        f"  reason:     {document.get('decision_reason', '')}",
    ]
    for finding in document.get("findings", []):
        lines.append(
            f"  finding:    {finding.get('type')} {finding.get('invariant_id')} "
            f"baseline={finding.get('baseline_status')} "
            f"candidate={finding.get('candidate_status')}"
        )
    uncertainty = document.get("residual_uncertainty", [])
    lines.append(f"  uncertainty: {len(uncertainty)} note(s)")
    lines.append(f"  digest:     sha256:{stable_digest(document)}")
    return "\n".join(lines)
