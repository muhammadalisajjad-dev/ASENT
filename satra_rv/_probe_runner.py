"""Trusted deterministic probe runner (M5), executed in a subprocess.

Loads the application under review from ``--app-dir``, exercises the trusted
probe plan from :mod:`satra_rv.dictionary` against it using Flask's test
client, and writes a machine-readable execution record to ``--output``.

Trust boundary: the runner and the probe plan are trusted code; the
application module is candidate-controlled.  Expectations (allowed status
sets) come from the trusted dictionary, never from the application.  Any
setup failure (import error, missing factory, failed login) or per-probe
fault is recorded explicitly so the caller can report insufficient evidence
instead of guessing.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path

from satra_rv.dictionary import INVARIANTS

MODULE_NAME = "satra_fixture_app"
OUTCOME_SATISFIED = "satisfied"
OUTCOME_VIOLATED = "violated"
OUTCOME_FAULT = "fault"
OUTCOME_SKIPPED = "skipped"


def _load_scenario(path: Path) -> dict:
    scenario = json.loads(path.read_text(encoding="utf-8"))
    for key in ("application", "session", "actors", "path_params"):
        if key not in scenario:
            raise RuntimeError(f"scenario is missing required key {key!r}")
    return scenario


def _load_application(app_dir: Path, module_file: str, factory: str):
    if not app_dir.is_dir():
        raise RuntimeError(f"application directory not found: {app_dir}")
    module_path = app_dir / module_file
    if not module_path.is_file():
        raise RuntimeError(f"application module not found: {module_path}")
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    spec = importlib.util.spec_from_file_location(MODULE_NAME, module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot create import spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    create = getattr(module, factory, None)
    if not callable(create):
        raise RuntimeError(f"application module does not expose {factory}()")
    return create()


def _format_path(template: str, path_params: dict) -> str:
    try:
        return template.format(**path_params)
    except KeyError as exc:
        raise RuntimeError(f"path parameter missing from scenario: {exc}") from exc


def _login(app, scenario: dict, actor_id: str) -> tuple[object, dict]:
    """Create an authenticated test client for one scenario actor."""
    session = scenario["session"]
    actor = next((a for a in scenario["actors"] if a.get("id") == actor_id), None)
    if actor is None:
        raise RuntimeError(f"scenario does not define actor {actor_id!r}")
    client = app.test_client()
    response = client.post(
        session["login_path"],
        json={
            session.get("username_field", "username"): actor["username"],
            session.get("password_field", "password"): actor["password"],
        },
    )
    step = {
        "step": "login",
        "actor": actor_id,
        "path": session["login_path"],
        "status": response.status_code,
        "expected_status": session.get("success_status", 200),
    }
    step["ok"] = response.status_code == step["expected_status"]
    return client, step


def _run_probe(client, invariant, path: str) -> dict:
    record = {
        "invariant_id": invariant.id,
        "kind": invariant.kind,
        "actor": invariant.probe.actor,
        "method": invariant.probe.method,
        "path": path,
        "expected_statuses": list(invariant.expected_statuses),
        "status": None,
        "outcome": OUTCOME_SKIPPED,
        "satisfied": False,
        "error": None,
        "elapsed_ms": None,
        "response_snippet": None,
    }
    started = time.monotonic()
    try:
        response = client.open(
            path,
            method=invariant.probe.method,
            json=dict(invariant.probe.body) if invariant.probe.body else None,
        )
        record["status"] = response.status_code
        body = response.get_data(as_text=True)
        record["response_snippet"] = body[:400]
    except Exception as exc:  # noqa: BLE001 - candidate may raise anything
        record["outcome"] = OUTCOME_FAULT
        record["satisfied"] = False
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
        return record
    record["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
    record["outcome"] = (
        OUTCOME_SATISFIED
        if record["status"] in invariant.expected_statuses
        else OUTCOME_VIOLATED
    )
    record["satisfied"] = record["outcome"] == OUTCOME_SATISFIED
    return record


def run(app_dir: Path, scenario_path: Path) -> dict:
    """Execute the trusted probe plan against one application directory."""
    record: dict = {
        "ok": False,
        "app_dir": str(app_dir),
        "scenario": str(scenario_path),
        "module": None,
        "factory": None,
        "python": sys.version.split()[0],
        "steps": [],
        "probes": [],
        "error": None,
    }
    scenario = _load_scenario(scenario_path)
    application = scenario["application"]
    record["module"] = application.get("module")
    record["factory"] = application.get("factory")
    path_params = scenario["path_params"]

    app = _load_application(
        app_dir, application.get("module", "app.py"), application.get("factory", "create_app")
    )
    record["steps"].append({"step": "load_application", "ok": True})

    clients: dict[str, object] = {}
    login_failures: list[str] = []
    for actor_id in sorted({inv.probe.actor for inv in INVARIANTS} - {"anonymous"}):
        client, step = _login(app, scenario, actor_id)
        record["steps"].append(step)
        if step["ok"]:
            clients[actor_id] = client
        else:
            login_failures.append(actor_id)
    clients["anonymous"] = app.test_client()

    if login_failures:
        record["error"] = (
            "scenario login failed for actor(s): " + ", ".join(login_failures)
        )
        record["probes"] = [
            {
                "invariant_id": inv.id,
                "kind": inv.kind,
                "actor": inv.probe.actor,
                "method": inv.probe.method,
                "path": _format_path(inv.probe.path_template, path_params),
                "expected_statuses": list(inv.expected_statuses),
                "status": None,
                "outcome": OUTCOME_SKIPPED,
                "satisfied": False,
                "error": "login failed; probe not executed",
                "elapsed_ms": None,
                "response_snippet": None,
            }
            for inv in INVARIANTS
        ]
        return record

    faults: list[str] = []
    for inv in INVARIANTS:
        path = _format_path(inv.probe.path_template, path_params)
        probe_record = _run_probe(clients[inv.probe.actor], inv, path)
        record["probes"].append(probe_record)
        if probe_record["outcome"] == OUTCOME_FAULT:
            faults.append(f"{inv.id} ({probe_record['error']})")

    if faults:
        record["error"] = "probe fault(s): " + "; ".join(faults)
        return record
    record["ok"] = True
    return record


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="satra-rv-probe-runner",
        description="trusted deterministic probe runner for SATRA-RV",
    )
    parser.add_argument("--app-dir", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    record: dict
    try:
        record = run(Path(args.app_dir), Path(args.scenario))
    except Exception:  # noqa: BLE001 - always report, never crash silently
        record = {
            "ok": False,
            "app_dir": args.app_dir,
            "scenario": args.scenario,
            "steps": [],
            "probes": [],
            "error": traceback.format_exc(),
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return 0 if record.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
