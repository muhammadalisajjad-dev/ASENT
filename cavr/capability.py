"""P4 - minimum capability contract.

Deterministic, project-specific security contract derived from the declared
project intent.  Each capability is either REQUIRED (with evidence explaining
why the project needs it) or PROHIBITED.  Rules are plain keyword matching
over the declared intent - intentionally narrow, explicitly not universal
semantic inference, and no LLM anywhere in CAVR.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from cavr.context import ProjectContext

FILE_READ = "FILE_READ"
FILE_WRITE = "FILE_WRITE"
NETWORK_CONNECT = "NETWORK_CONNECT"
PROCESS_CREATE = "PROCESS_CREATE"
SECRET_ACCESS = "SECRET_ACCESS"

CAPABILITIES = (FILE_READ, FILE_WRITE, NETWORK_CONNECT, PROCESS_CREATE, SECRET_ACCESS)

# Capabilities no first-slice fixture may legitimately require.
BASELINE_PROHIBITED = (NETWORK_CONNECT, PROCESS_CREATE, SECRET_ACCESS)

DERIVATION = "deterministic_intent_rules_v1"

_INTENT_READ_RE = re.compile(
    r"\b(extract|read|parse|inspect|load|open)\b.*\b(pdf|invoice|document|file|text|attachment)s?\b"
    r"|\b(pdf|invoice|document)s?\b.*\b(extract|read|parse)\b",
    re.IGNORECASE | re.DOTALL,
)
_INTENT_STORE_RE = re.compile(
    r"\b(store|save|persist|write|output|process|index)\b", re.IGNORECASE
)


@dataclass(frozen=True)
class CapabilityRule:
    """One line of the contract: capability + role + evidence."""

    capability: str
    role: str  # "required" | "prohibited"
    rule_id: str
    evidence: str

    def as_dict(self) -> dict:
        return {
            "capability": self.capability,
            "role": self.role,
            "rule_id": self.rule_id,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class CapabilityContract:
    """Machine-readable project-specific capability contract."""

    derivation: str
    rules: tuple[CapabilityRule, ...]

    @property
    def required(self) -> tuple[str, ...]:
        return tuple(r.capability for r in self.rules if r.role == "required")

    @property
    def prohibited(self) -> tuple[str, ...]:
        return tuple(r.capability for r in self.rules if r.role == "prohibited")

    @property
    def conflicts(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.required) & set(self.prohibited)))

    def as_dict(self) -> dict:
        return {
            "derivation": self.derivation,
            "required": list(self.required),
            "prohibited": list(self.prohibited),
            "conflicts": list(self.conflicts),
            "rules": [rule.as_dict() for rule in self.rules],
        }


def derive_contract(context: ProjectContext) -> CapabilityContract:
    """Derive the capability contract from declared project intent.

    Rules (rule ids are part of the evidence):

    * ``intent_document_read`` - intent mentions reading/extracting
      documents -> FILE_READ required.
    * ``intent_result_store`` - intent mentions storing/processing the
      result -> FILE_WRITE required.
    * ``baseline_least_privilege`` - NETWORK_CONNECT, PROCESS_CREATE and
      SECRET_ACCESS are always prohibited in this slice.
    * ``baseline_unjustified_<cap>`` - any other capability that the intent
      does not justify is prohibited.
    """
    intent = context.intent
    rules: list[CapabilityRule] = []

    needs_read = bool(_INTENT_READ_RE.search(intent))
    needs_store = bool(_INTENT_STORE_RE.search(intent))

    if needs_read:
        rules.append(
            CapabilityRule(
                capability=FILE_READ,
                role="required",
                rule_id="intent_document_read",
                evidence=(
                    f"declared intent justifies reading input documents: "
                    f"{_quote(intent)}"
                ),
            )
        )
    if needs_store:
        rules.append(
            CapabilityRule(
                capability=FILE_WRITE,
                role="required",
                rule_id="intent_result_store",
                evidence=(
                    f"declared intent justifies storing the processed result: "
                    f"{_quote(intent)}"
                ),
            )
        )

    for capability in CAPABILITIES:
        if capability in BASELINE_PROHIBITED:
            rules.append(
                CapabilityRule(
                    capability=capability,
                    role="prohibited",
                    rule_id="baseline_least_privilege",
                    evidence=(
                        "first-slice baseline: dependency behavior for this "
                        "project type never requires this capability"
                    ),
                )
            )
        elif capability not in (r.capability for r in rules):
            rules.append(
                CapabilityRule(
                    capability=capability,
                    role="prohibited",
                    rule_id=f"baseline_unjustified_{capability.lower()}",
                    evidence="declared intent provides no justification for this capability",
                )
            )

    ordered = sorted(
        rules,
        key=lambda r: (CAPABILITIES.index(r.capability), r.role != "required"),
    )
    return CapabilityContract(derivation=DERIVATION, rules=tuple(ordered))


def _quote(text: str, limit: int = 160) -> str:
    flat = " ".join(text.split())
    if len(flat) > limit:
        flat = flat[: limit - 3] + "..."
    return repr(flat)
