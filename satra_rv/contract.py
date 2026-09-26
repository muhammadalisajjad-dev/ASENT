"""M3 - Security Change Contract (deterministic, bounded).

The contract is declared *before* any candidate execution: it binds the
localized security-sensitive region (M2) to the trusted invariants of the
security dictionary (M4) and turns each bound invariant into an explicit
obligation that the deterministic probes (M5) will witness.

Two obligation kinds:

* security denials   (``deny``)   - must refuse access; a candidate failure
  here is a security regression,
* required behavior  (``allow``)  - ordinary owner functionality that must
  keep working; a candidate failure here is a functionality regression.

If no security-sensitive region can be localized, no contract can be bound
and the pipeline reports insufficient evidence rather than inventing one.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from satra_rv import dictionary
from satra_rv.localization import SecurityRegion

CONTRACT_SCHEMA = "satra_rv_security_change_contract/0.1"


@dataclass(frozen=True)
class ContractObligation:
    """One bound invariant turned into an executable obligation."""

    invariant_id: str
    kind: str  # dictionary.KIND_DENY | dictionary.KIND_ALLOW
    route: str
    method: str
    actor: str
    probe_method: str
    expected_statuses: tuple[int, ...]
    statement: str
    source: str

    @property
    def is_security_obligation(self) -> bool:
        return self.kind == dictionary.KIND_DENY

    def as_dict(self) -> dict:
        return {
            "invariant_id": self.invariant_id,
            "kind": self.kind,
            "route": self.route,
            "method": self.method,
            "actor": self.actor,
            "probe_method": self.probe_method,
            "expected_statuses": list(self.expected_statuses),
            "statement": self.statement,
            "source": self.source,
        }


@dataclass(frozen=True)
class SecurityChangeContract:
    """Declared obligations for one localized security-sensitive change."""

    contract_id: str
    family: str
    scope: dict
    obligations: tuple[ContractObligation, ...]
    binding_notes: tuple[str, ...]
    dictionary_version: str
    declared_before_execution: bool = True

    @property
    def security_obligations(self) -> tuple[ContractObligation, ...]:
        return tuple(o for o in self.obligations if o.is_security_obligation)

    @property
    def functionality_obligations(self) -> tuple[ContractObligation, ...]:
        return tuple(o for o in self.obligations if not o.is_security_obligation)

    @property
    def bound_route(self) -> str | None:
        route = self.scope.get("route")
        return route if isinstance(route, str) else None

    def obligation_ids(self) -> tuple[str, ...]:
        return tuple(o.invariant_id for o in self.obligations)

    def as_dict(self) -> dict:
        return {
            "schema": CONTRACT_SCHEMA,
            "contract_id": self.contract_id,
            "family": self.family,
            "scope": dict(self.scope),
            "dictionary_version": self.dictionary_version,
            "declared_before_execution": self.declared_before_execution,
            "obligations": [o.as_dict() for o in self.obligations],
            "binding_notes": list(self.binding_notes),
            "counts": {
                "total": len(self.obligations),
                "security_denials": len(self.security_obligations),
                "required_behavior": len(self.functionality_obligations),
            },
        }


def _contract_id(scope: dict, obligations: tuple[ContractObligation, ...]) -> str:
    payload = {
        "scope": scope,
        "obligations": sorted(o.invariant_id for o in obligations),
        "dictionary": dictionary.DICTIONARY_VERSION,
        "schema": CONTRACT_SCHEMA,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_contract(region: SecurityRegion | None) -> SecurityChangeContract:
    """Bind the localized region to the trusted dictionary (declared a priori).

    A ``region`` of ``None`` yields an empty contract with an explicit note:
    the caller must treat that as insufficient evidence, never as approval.
    """
    if region is None:
        scope: dict = {"localized": False}
        notes = [
            "no security-sensitive region was localized from the change set; "
            "no security obligation can be bound to this change"
        ]
        obligations: tuple[ContractObligation, ...] = ()
        return SecurityChangeContract(
            contract_id=_contract_id(scope, obligations),
            family=dictionary.FAMILY_AUTHORIZATION,
            scope=scope,
            obligations=obligations,
            binding_notes=tuple(notes),
            dictionary_version=dictionary.DICTIONARY_VERSION,
        )

    scope = {
        "localized": True,
        "file": region.file,
        "function": region.function,
        "route": region.route,
        "method": region.method,
        "line_range": [region.start_line, region.end_line],
        "confidence": region.confidence,
        "confidence_label": region.confidence_label,
        "mapping_reason": region.mapping_reason,
    }
    notes: list[str] = []
    bound = dictionary.invariants_for_route(region.route)
    if not bound:
        notes.append(
            f"localized region route {region.route!r} has no trusted "
            "dictionary invariant; contract is empty"
        )
    obligations = tuple(
        ContractObligation(
            invariant_id=inv.id,
            kind=inv.kind,
            route=inv.route,
            method=region.method or "",
            actor=inv.probe.actor,
            probe_method=inv.probe.method,
            expected_statuses=inv.expected_statuses,
            statement=inv.obligation,
            source=f"dictionary:{dictionary.DICTIONARY_VERSION}",
        )
        for inv in bound
    )
    notes.append(
        f"bound {len(obligations)} trusted invariant(s) of family "
        f"{dictionary.FAMILY_AUTHORIZATION} to route {region.route!r} "
        f"(localized at {region.file}:{region.start_line}-{region.end_line}, "
        f"confidence {region.confidence:.2f} {region.confidence_label})"
    )
    return SecurityChangeContract(
        contract_id=_contract_id(scope, obligations),
        family=dictionary.FAMILY_AUTHORIZATION,
        scope=scope,
        obligations=obligations,
        binding_notes=tuple(notes),
        dictionary_version=dictionary.DICTIONARY_VERSION,
    )
