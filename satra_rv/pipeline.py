"""SATRA-RV pipeline orchestration: capture through decision.

    M1 capture -> M2 localization -> M3 contract -> M5 deterministic
    execution on both sides -> differential comparison -> decision ->
    machine-readable evidence.

The Security Change Contract is declared before any candidate execution;
the decision is derived only from deterministic probe outcomes recorded in
subprocesses.  Exit codes: 0 ACCEPTED, 3 REJECTED, 4 INCONCLUSIVE,
1 usage/input error.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from satra_rv import capture, contract, decision, dictionary, differential, evidence, execution, localization
from shared.errors import InputError

PROTOTYPE_PARAMETERS = {
    "scope": "Python/Flask authorization and ownership changes (first slice)",
    "localizer": "satra_rv_security_localizer_v1 (bounded static heuristic)",
    "dictionary": dictionary.DICTIONARY_VERSION,
    "probe_runner": "satra_rv._probe_runner (subprocess, Flask test client)",
    "probe_timeout_seconds": execution.DEFAULT_TIMEOUT,
    "llm_used": False,
    "dynamic_test_generation": "disabled (deterministic core only)",
}

EXIT_CODES = {
    decision.ACCEPTED: 0,
    decision.REJECTED: 3,
    decision.INCONCLUSIVE: 4,
}


@dataclass
class AnalyzeResult:
    """Outcome of one full SATRA-RV analysis."""

    evidence: dict
    decision: str
    exit_code: int

    @property
    def stable_digest(self) -> str:
        return evidence.stable_digest(self.evidence)


def _resolve_scenario(baseline_dir: Path, scenario_path: str | Path | None) -> Path:
    if scenario_path is not None:
        return Path(scenario_path)
    default = baseline_dir.parent / "scenario.json"
    if not default.is_file():
        raise InputError(
            f"scenario file not found: {default} (pass --scenario explicitly)"
        )
    return default


def run_analyze(
    baseline_dir: str | Path,
    candidate_dir: str | Path,
    scenario_path: str | Path | None = None,
    *,
    timeout: float = execution.DEFAULT_TIMEOUT,
) -> AnalyzeResult:
    """Execute the SATRA-RV vertical slice for one baseline/candidate pair."""
    baseline = Path(baseline_dir)
    candidate = Path(candidate_dir)
    if not baseline.is_dir():
        raise InputError(f"baseline directory not found: {baseline}")
    if not candidate.is_dir():
        raise InputError(f"candidate directory not found: {candidate}")
    scenario = _resolve_scenario(baseline, scenario_path)
    execution.load_scenario(scenario)

    # M1 - repository / diff capture.
    diff = capture.capture_diff(baseline, candidate)

    # M2 - security-sensitive change localization.
    localization_result = localization.localize(diff)

    # M3 - Security Change Contract, declared before any execution.
    change_contract = contract.build_contract(localization_result.primary)

    # M5 - trusted deterministic execution on both sides.
    baseline_run = execution.run_probes("baseline", baseline, scenario, timeout=timeout)
    candidate_run = execution.run_probes(
        "candidate", candidate, scenario, timeout=timeout
    )

    # Differential comparison of observed behavior.
    diff_result = differential.compare(change_contract, baseline_run, candidate_run)

    # Decision.
    verdict = decision.decide(change_contract, localization_result, diff_result)

    document = evidence.build_evidence(
        inputs={
            "baseline_dir": str(baseline),
            "candidate_dir": str(candidate),
            "scenario": str(scenario),
            "baseline_id": diff.baseline_id,
            "candidate_id": diff.candidate_id,
            "identical": diff.baseline_id == diff.candidate_id,
        },
        capture=diff.as_dict(),
        localization=localization_result.as_dict(),
        contract=change_contract.as_dict(),
        dictionary=dictionary.as_dict(),
        execution={
            "baseline": baseline_run.as_dict(),
            "candidate": candidate_run.as_dict(),
            "timeout_seconds": timeout,
        },
        differential=diff_result.as_dict(),
        decision=verdict.decision,
        decision_reason=verdict.reason,
        findings=list(verdict.findings),
        coverage=verdict.coverage,
        residual_uncertainty=list(verdict.residual_uncertainty),
        prototype_parameters=PROTOTYPE_PARAMETERS,
    )
    return AnalyzeResult(
        evidence=document,
        decision=verdict.decision,
        exit_code=EXIT_CODES[verdict.decision],
    )
