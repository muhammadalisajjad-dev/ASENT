"""CAVR: Counterfactual Activation, Verified Repair & Recovery.

First vertical slice (dependency security, Python/PyPI-style fixtures):

    capture     (cavr.capture)      P1 dependency action record
    policy      (cavr.policy)       P2 requirement gate: PERMITTED | BLOCK
    context     (cavr.context)      P3 minimal project context
    capability  (cavr.capability)   P4 deterministic capability contract
    resolve     (cavr.resolve)      P5 exact local package fixture resolution
    triggers    (cavr.triggers)     P6 security trigger discovery (static, best-effort)
    sandbox     (cavr.sandbox)      P7 disposable counterfactual execution
    observe     (cavr.observe)      P8 normalized behavior events
    decision    (cavr.decision)     P9 evidence-backed bounded decision
    evidence    (cavr.evidence)     machine-readable evidence document

Bounded claim: CAVR can intercept a dependency action, establish a declared
project-specific capability boundary, deliberately exercise a supported
security-sensitive condition in a disposable environment, observe the
resulting behavior, and produce an evidence-backed bounded decision.  It does
NOT establish general package safety.
"""

from __future__ import annotations

__all__ = [
    "capability",
    "capture",
    "cli",
    "context",
    "decision",
    "evidence",
    "observe",
    "pipeline",
    "policy",
    "resolve",
    "sandbox",
    "triggers",
]
