"""P8 - observation of actual package behavior.

Normalizes raw sandbox trace records into evidence events with a small,
explicit vocabulary: FILE_READ, FILE_WRITE, PROCESS_CREATE, NETWORK_CONNECT.
A file read of a designated canary/sensitive target is additionally classified
as SECRET_ACCESS (the capability, not a new event kind).

Backend: CPython audit hooks installed by :mod:`cavr._runner`.  This is a
clearly labelled prototype fallback for hosts without OS-level tracing: it
does NOT provide full syscall or native-code visibility.
"""

from __future__ import annotations

from pathlib import Path

FILE_READ = "FILE_READ"
FILE_WRITE = "FILE_WRITE"
PROCESS_CREATE = "PROCESS_CREATE"
NETWORK_CONNECT = "NETWORK_CONNECT"
SECRET_ACCESS = "SECRET_ACCESS"

EVENT_KINDS = (FILE_READ, FILE_WRITE, PROCESS_CREATE, NETWORK_CONNECT)
NON_CAPABILITY_KINDS = ("RUN_START", "PYTHON_EXCEPTION", "RUN_END")

SENSITIVE_MARKERS = (
    "canary",
    ".ssh",
    ".aws",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "secret",
    ".env",
    "password",
    "token",
)

_CLASS_CANARY = "canary_secret"
_CLASS_PROJECT_INPUT = "project_input"
_CLASS_PACKAGE_SOURCE = "package_source"
_CLASS_SANDBOX = "sandbox"
_CLASS_SENSITIVE_EXTERNAL = "sensitive_external"
_CLASS_EXTERNAL = "external"


def _slash(path: str) -> str:
    return path.replace("\\", "/")


def _is_under(path: str, root: str) -> bool:
    slashed_path, slashed_root = _slash(path), _slash(root).rstrip("/")
    return slashed_path == slashed_root or slashed_path.startswith(slashed_root + "/")


def _classify_path(path: str, workdir: Path, canary_path: Path | None) -> tuple[str, str]:
    """Return (target, target_class) for an absolute path from the trace."""
    slashed = _slash(path)
    if canary_path is not None and slashed == _slash(str(canary_path)):
        return str(canary_path.name), _CLASS_CANARY
    if _is_under(path, str(workdir)):
        relative = _slash(str(Path(path).relative_to(workdir)))
        if relative.startswith("input/"):
            return relative, _CLASS_PROJECT_INPUT
        if relative.startswith("pkgsrc/"):
            return relative, _CLASS_PACKAGE_SOURCE
        return relative, _CLASS_SANDBOX
    lowered = slashed.lower()
    if any(marker in lowered for marker in SENSITIVE_MARKERS):
        return slashed, _CLASS_SENSITIVE_EXTERNAL
    return slashed, _CLASS_EXTERNAL


def normalize_events(
    label: str,
    raw_records: list[dict],
    workdir: Path,
    canary_path: Path | None,
) -> list[dict]:
    """Turn raw runner records into normalized, sandbox-relative events."""
    events: list[dict] = []
    for record in raw_records:
        kind = record.get("kind")
        if kind in NON_CAPABILITY_KINDS:
            events.append(
                {
                    "run": label,
                    "kind": kind,
                    "target": str(record.get("module") or record.get("exception") or ""),
                    "target_class": "run",
                    "detail": record.get("via"),
                }
            )
            continue
        if kind not in EVENT_KINDS:
            continue
        if kind in (FILE_READ, FILE_WRITE):
            path = str(record.get("path", ""))
            target, target_class = _classify_path(path, workdir, canary_path)
            event = {
                "run": label,
                "kind": kind,
                "target": target,
                "target_class": target_class,
                "detail": record.get("via"),
            }
            # The audit hook fires before the open completes; record whether
            # the target actually existed so attempts are not reported as
            # completed reads/writes.
            if not Path(path).exists():
                event["target_absent"] = True
            events.append(event)
        else:
            events.append(
                {
                    "run": label,
                    "kind": kind,
                    "target": str(record.get("target", "")),
                    "target_class": "process" if kind == PROCESS_CREATE else "network",
                    "detail": record.get("via"),
                }
            )
    return events


def event_capability(event: dict) -> str:
    """Capability represented by one normalized event."""
    if (
        event.get("kind") == FILE_READ
        and event.get("target_class") in (_CLASS_CANARY, _CLASS_SENSITIVE_EXTERNAL)
    ):
        return SECRET_ACCESS
    return str(event.get("kind", ""))


def observed_capabilities(events: list[dict]) -> list[str]:
    """Deterministically ordered capability set over all events."""
    from cavr.capability import CAPABILITIES

    seen = {event_capability(event) for event in events}
    return [capability for capability in CAPABILITIES if capability in seen]


def inspect_artifacts(workdir: Path, canary_path: Path, canary_value: str) -> list[dict]:
    """Post-run inspection of the controlled sink (counterfactual only)."""
    sink = workdir / "out" / "canary_sink.txt"
    if not sink.is_file():
        return [
            {
                "check": "counterfactual_canary_reached_sink",
                "passed": False,
                "interpretation": "violation if true",
                "detail": "designated sink was not written",
            }
        ]
    try:
        content = sink.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [
            {
                "check": "counterfactual_canary_reached_sink",
                "passed": False,
                "interpretation": "violation if true",
                "detail": f"sink unreadable: {exc}",
            }
        ]
    matched = content == canary_value
    return [
        {
            "check": "counterfactual_canary_reached_sink",
            "passed": matched,
            "interpretation": "violation if true",
            "detail": (
                "sink contains the exact synthetic canary value"
                if matched
                else "sink content does not match the synthetic canary value"
            ),
        }
    ]
