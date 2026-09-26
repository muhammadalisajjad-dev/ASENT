"""SATRA-RV: Security Assertion, Testing, Repair & Verification.

First vertical slice (Python/Flask, authorization / ownership regression):

    capture       (satra_rv.capture)       M1 repository / diff capture
    localization  (satra_rv.localization)  M2 security-change localizer
    contract      (satra_rv.contract)      M3 Security Change Contract
    dictionary    (satra_rv.dictionary)    M4 trusted security dictionary
    execution     (satra_rv.execution)     M5 trusted deterministic probes
    _probe_runner (satra_rv._probe_runner) subprocess probe execution
    differential  (satra_rv.differential)  baseline vs candidate comparison
    decision      (satra_rv.decision)      ACCEPTED | REJECTED | INCONCLUSIVE
    evidence      (satra_rv.evidence)      machine-readable evidence bundle
    pipeline      (satra_rv.pipeline)      end-to-end orchestration
    cli           (satra_rv.cli)           ``python -m satra_rv analyze``

Planned, not implemented in this slice: optional local Ollama-backed dynamic
test generation (M6) and its validator (M7).  The decision is produced by the
deterministic core and must remain independent of any model.

Bounded claim: SATRA-RV can capture a candidate change, localize the
security-sensitive region, declare an independent Security Change Contract,
execute trusted deterministic security tests against baseline and candidate,
differentially compare observed behavior, and produce an evidence-backed
accept/reject decision.  Whether this protocol provides measurable benefit
over existing baselines (CodeQL, Semgrep, Bandit, DAST, mutation testing,
LLM test generation) is an open empirical question.
"""

from __future__ import annotations

__all__ = [
    "capture",
    "cli",
    "contract",
    "decision",
    "differential",
    "dictionary",
    "evidence",
    "execution",
    "localization",
    "pipeline",
]
