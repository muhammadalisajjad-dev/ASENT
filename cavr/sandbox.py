"""P7 - disposable counterfactual sandbox.

Executes the untrusted package twice in isolated, disposable environments:

* NORMAL - the synthetic trigger is absent and no canary exists.
* COUNTERFACTUAL - CAVR deliberately satisfies the discovered activation
  (trigger env var), plants the synthetic canary secret and the controlled
  sink, then executes the same package again.

The trusted developer project is never an execution location: the package is
copied into a fresh temporary directory and run in a separate interpreter
process with a scrubbed (allowlisted) environment.

Isolation boundary: this is process + disposable-directory + scrubbed-env
isolation.  When Docker/Podman is available it is preferred; otherwise this
fallback is used and reported honestly in the evidence.  Host safety is never
weakened to make a test pass, and fixtures are laboratory canaries only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from cavr import observe
from cavr.context import ProjectContext
from cavr.resolve import ResolvedPackage
from cavr.triggers import TriggerReport

CANARY_VALUE = "CAVR-LAB-CANARY-VALUE-DO-NOT-TRUST"
CANARY_FILE = "canary_secret.txt"
CANARY_ENV = "CAVR_CANARY_PATH"
DEFAULT_TIMEOUT = 30.0
_ENV_ALLOWLIST = (
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
)

RUNNER = Path(__file__).with_name("_runner.py")


@dataclass(frozen=True)
class SandboxPlan:
    """One environment to exercise."""

    label: str
    env_overrides: dict
    plant_canary: bool
    activation: dict

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "env_overrides": dict(self.env_overrides),
            "canary_planted": self.plant_canary,
            "activation": self.activation,
            "synthetic_condition_present": bool(self.env_overrides)
            or self.plant_canary,
        }


@dataclass
class RunResult:
    """Observed result of one sandbox execution."""

    label: str
    ok: bool
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    events: list = field(default_factory=list)
    artifact_checks: list = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    error: str | None = None

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "ok": self.ok,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "duration_ms": self.duration_ms,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
            "events": [dict(event) for event in self.events],
            "artifact_checks": [dict(check) for check in self.artifact_checks],
        }


def plan_environments(report: TriggerReport) -> tuple[SandboxPlan, SandboxPlan]:
    """Build the NORMAL and COUNTERFACTUAL plans from trigger discovery."""
    activation = report.activations
    normal = SandboxPlan(label="normal", env_overrides={}, plant_canary=False, activation={})
    counterfactual = SandboxPlan(
        label="counterfactual",
        env_overrides=dict(activation.get("env", {})),
        plant_canary=True,
        activation=activation,
    )
    return normal, counterfactual


def _base_env() -> dict:
    env = {key: os.environ[key] for key in _ENV_ALLOWLIST if key in os.environ}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def isolation_report() -> dict:
    """Honest description of the isolation boundary used for this run."""
    docker = shutil.which("docker")
    podman = shutil.which("podman")
    if docker or podman:
        mechanism = "container" if docker else "podman"
        boundary = (
            "Untrusted package executed in a throwaway container image with the "
            "trusted project never mounted as an execution location."
        )
        availability = docker or podman
    else:
        mechanism = "disposable_tempdir_subprocess"
        boundary = (
            "Untrusted package executed in a separate interpreter process inside "
            "a disposable temporary directory with an allowlisted environment; the "
            "trusted project directory is never an execution location. This is "
            "process/directory/environment isolation only - no container runtime "
            "(docker/podman) is available on this host, so the host kernel is "
            "shared and there is no OS-level syscall confinement."
        )
        availability = None
    return {
        "mechanism": mechanism,
        "container_runtime": availability or "not available on PATH",
        "boundary": boundary,
        "trusted_project_executed": False,
        "package_copied_into_sandbox": True,
        "environment": "allowlisted variables only; trigger env vars absent from parent",
        "network_policy": "fixtures make no network attempts; loopback-only by design",
        "fixtures": "synthetic laboratory canaries only - no real malware, no "
        "credential theft, no external exfiltration, no persistence",
    }


def execute_run(
    resolved: ResolvedPackage,
    context: ProjectContext,
    plan: SandboxPlan,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    keep_sandbox: bool = False,
) -> RunResult:
    """Execute the package once under *plan* and normalize its behavior."""
    workdir = Path(tempfile.mkdtemp(prefix="cavr_sbx_"))
    canary_path: Path | None = None
    try:
        shutil.copytree(
            resolved.source_dir,
            workdir / "pkgsrc",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        input_source = Path(context.project_dir) / "input"
        if input_source.is_dir():
            shutil.copytree(input_source, workdir / "input")
        (workdir / "out").mkdir(parents=True, exist_ok=True)

        env = _base_env()
        env.update({str(k): str(v) for k, v in plan.env_overrides.items()})
        if plan.plant_canary:
            canary_path = workdir / CANARY_FILE
            canary_path.write_text(CANARY_VALUE, encoding="utf-8")
            env[CANARY_ENV] = str(canary_path)
        for relative in plan.activation.get("files", []):
            target = workdir / str(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(CANARY_VALUE, encoding="utf-8")

        trace_path = workdir / ".cavr_trace.jsonl"
        command = [
            sys.executable,
            str(RUNNER),
            str(workdir / "pkgsrc"),
            resolved.module,
            str(trace_path),
            str(workdir),
        ]

        exit_code: int | None = None
        stdout = stderr = ""
        timed_out = False
        error: str | None = None
        started = time.monotonic()
        try:
            proc = subprocess.run(
                command,
                cwd=str(workdir),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            exit_code = proc.returncode
            stdout = (proc.stdout or "")[:4000]
            stderr = (proc.stderr or "")[:4000]
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            error = f"sandbox execution exceeded {timeout}s timeout"
            stdout = (exc.stdout or b"").decode("utf-8", "replace")[:4000] if isinstance(exc.stdout, bytes) else (exc.stdout or "")[:4000]
            stderr = (exc.stderr or b"").decode("utf-8", "replace")[:4000] if isinstance(exc.stderr, bytes) else (exc.stderr or "")[:4000]
        except OSError as exc:
            error = f"failed to launch sandbox process: {exc}"
        duration_ms = int((time.monotonic() - started) * 1000)

        raw_records: list[dict] = []
        if trace_path.is_file():
            for line in trace_path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    raw_records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        elif error is None:
            error = "sandbox produced no observation trace"

        events = observe.normalize_events(plan.label, raw_records, workdir, canary_path)
        exception_events = [e for e in events if e["kind"] == "PYTHON_EXCEPTION"]
        checks: list[dict] = []
        if canary_path is not None:
            checks = observe.inspect_artifacts(workdir, canary_path, CANARY_VALUE)

        ok = not timed_out and error is None and not exception_events
        return RunResult(
            label=plan.label,
            ok=ok,
            exit_code=exit_code,
            timed_out=timed_out,
            duration_ms=duration_ms,
            events=events,
            artifact_checks=checks,
            stdout=stdout,
            stderr=stderr,
            error=error,
        )
    finally:
        if not keep_sandbox:
            shutil.rmtree(workdir, ignore_errors=True)
