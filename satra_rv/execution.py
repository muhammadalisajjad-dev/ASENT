"""M5 - trusted deterministic security test execution.

Runs the trusted probe plan of :mod:`satra_rv.dictionary` against the
baseline application and the candidate application in separate subprocesses
(:mod:`satra_rv._probe_runner`) and returns typed execution records.

Everything here is deterministic: fixed probe order, fixed expectations, no
network, no model calls, no randomness.  The candidate is only ever observed
through HTTP requests; it is never trusted to declare its own outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from shared.errors import InputError

DEFAULT_TIMEOUT = 60.0

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_MODULE = "satra_rv._probe_runner"

COMPLETE_OUTCOMES = ("satisfied", "violated")


@dataclass(frozen=True)
class ProbeRecord:
    """One observed probe outcome on one side of the comparison."""

    invariant_id: str
    kind: str
    actor: str
    method: str
    path: str
    expected_statuses: tuple[int, ...]
    status: int | None
    outcome: str
    satisfied: bool
    error: str | None
    elapsed_ms: float | None
    response_snippet: str | None

    def as_dict(self) -> dict:
        return {
            "invariant_id": self.invariant_id,
            "kind": self.kind,
            "actor": self.actor,
            "method": self.method,
            "path": self.path,
            "expected_statuses": list(self.expected_statuses),
            "status": self.status,
            "outcome": self.outcome,
            "satisfied": self.satisfied,
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
            "response_snippet": self.response_snippet,
        }


@dataclass(frozen=True)
class ExecutionResult:
    """Full execution record for one side (baseline or candidate)."""

    side: str
    app_dir: str
    ok: bool
    steps: tuple[dict, ...]
    probes: tuple[ProbeRecord, ...]
    error: str | None
    returncode: int | None
    duration_ms: float
    command: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """True when every probe produced a classifiable outcome."""
        return self.ok and all(
            probe.outcome in COMPLETE_OUTCOMES for probe in self.probes
        )

    def probe(self, invariant_id: str) -> ProbeRecord | None:
        return next(
            (p for p in self.probes if p.invariant_id == invariant_id), None
        )

    @property
    def satisfied_count(self) -> int:
        return sum(1 for p in self.probes if p.satisfied)

    def as_dict(self) -> dict:
        return {
            "side": self.side,
            "app_dir": self.app_dir,
            "ok": self.ok,
            "complete": self.complete,
            "error": self.error,
            "returncode": self.returncode,
            "duration_ms": self.duration_ms,
            "command": list(self.command),
            "steps": [dict(step) for step in self.steps],
            "probe_count": len(self.probes),
            "satisfied_count": self.satisfied_count,
            "probes": [probe.as_dict() for probe in self.probes],
        }


def load_scenario(path: str | Path) -> dict:
    """Load and validate the trusted scenario file."""
    scenario_path = Path(path)
    if not scenario_path.is_file():
        raise InputError(f"scenario file not found: {scenario_path}")
    try:
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"cannot read scenario file {scenario_path}: {exc}") from exc
    if not isinstance(scenario, dict):
        raise InputError(f"scenario file must contain a JSON object: {scenario_path}")
    for key in ("application", "session", "actors", "path_params"):
        if key not in scenario:
            raise InputError(f"scenario file is missing required key {key!r}")
    application = scenario["application"]
    if not isinstance(application, dict) or "module" not in application:
        raise InputError("scenario 'application' must declare a 'module'")
    actors = scenario["actors"]
    if not isinstance(actors, list) or not actors:
        raise InputError("scenario 'actors' must be a non-empty list")
    for actor in actors:
        if not isinstance(actor, dict) or "id" not in actor:
            raise InputError("every scenario actor needs an 'id'")
        for field in ("username", "password"):
            if field not in actor:
                raise InputError(f"scenario actor {actor.get('id')!r} lacks {field!r}")
    return scenario


def _parse_record(payload: dict, side: str, app_dir: Path) -> ExecutionResult:
    probes = tuple(
        ProbeRecord(
            invariant_id=str(item.get("invariant_id")),
            kind=str(item.get("kind", "")),
            actor=str(item.get("actor", "")),
            method=str(item.get("method", "")),
            path=str(item.get("path", "")),
            expected_statuses=tuple(item.get("expected_statuses") or ()),
            status=item.get("status"),
            outcome=str(item.get("outcome", "skipped")),
            satisfied=bool(item.get("satisfied")),
            error=item.get("error"),
            elapsed_ms=item.get("elapsed_ms"),
            response_snippet=item.get("response_snippet"),
        )
        for item in payload.get("probes", [])
    )
    return ExecutionResult(
        side=side,
        app_dir=str(app_dir),
        ok=bool(payload.get("ok")),
        steps=tuple(payload.get("steps", [])),
        probes=probes,
        error=payload.get("error"),
        returncode=0,
        duration_ms=0.0,
        command=(),
    )


def run_probes(
    side: str,
    app_dir: str | Path,
    scenario_path: str | Path,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> ExecutionResult:
    """Execute the trusted probe plan against one application directory."""
    app = Path(app_dir)
    if not app.is_dir():
        raise InputError(f"application directory not found: {app}")
    load_scenario(scenario_path)

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="satra_rv_probe_") as tmp:
        output = Path(tmp) / "result.json"
        command = [
            sys.executable,
            "-m",
            RUNNER_MODULE,
            "--app-dir",
            str(app),
            "--scenario",
            str(scenario_path),
            "--output",
            str(output),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                side=side,
                app_dir=str(app),
                ok=False,
                steps=(),
                probes=(),
                error=f"probe runner timed out after {timeout:g}s",
                returncode=None,
                duration_ms=round((time.monotonic() - started) * 1000, 3),
                command=tuple(command),
            )

        duration_ms = round((time.monotonic() - started) * 1000, 3)
        if not output.is_file():
            stderr_tail = (completed.stderr or "").strip()[-2000:]
            return ExecutionResult(
                side=side,
                app_dir=str(app),
                ok=False,
                steps=(),
                probes=(),
                error=(
                    f"probe runner exited with code {completed.returncode} "
                    f"without an execution record"
                    + (f": {stderr_tail}" if stderr_tail else "")
                ),
                returncode=completed.returncode,
                duration_ms=duration_ms,
                command=tuple(command),
            )
        try:
            payload = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return ExecutionResult(
                side=side,
                app_dir=str(app),
                ok=False,
                steps=(),
                probes=(),
                error=f"probe runner produced unreadable output: {exc}",
                returncode=completed.returncode,
                duration_ms=duration_ms,
                command=tuple(command),
            )

    result = _parse_record(payload, side, app)
    ok = bool(payload.get("ok")) and completed.returncode == 0
    error = payload.get("error")
    if not ok and not error:
        error = f"probe runner exited with code {completed.returncode}"
    return ExecutionResult(
        side=result.side,
        app_dir=result.app_dir,
        ok=ok,
        steps=result.steps,
        probes=result.probes,
        error=error,
        returncode=completed.returncode,
        duration_ms=duration_ms,
        command=tuple(command),
    )
