"""M4 - trusted security dictionary (deterministic, bounded).

A curated, versioned set of security invariants for Python/Flask
authorization/ownership behavior.  Every invariant carries:

* a stable identifier and security family,
* an explicit obligation statement (what must hold),
* a kind: ``deny`` (a security invariant that must refuse access) or
  ``allow`` (required ordinary functionality that must keep working),
* the Flask route template it applies to,
* a trusted deterministic probe (actor, HTTP method, path template, body,
  expected status set) that witnesses the invariant under execution.

The dictionary is trusted code in this repository: it is *not* derived from
the candidate change, and it is fixed before any candidate is executed.
Probes are plain HTTP requests against the application under review; nothing
in the dictionary encodes a candidate-specific attacker condition.
"""

from __future__ import annotations

from dataclasses import dataclass

FAMILY_AUTHORIZATION = "authorization_ownership"

KIND_DENY = "deny"
KIND_ALLOW = "allow"

DICTIONARY_VERSION = "satra_rv_trusted_security_dictionary/0.1"

DETAIL_ROUTE = "/api/invoices/<int:invoice_id>"


@dataclass(frozen=True)
class ProbeSpec:
    """A trusted deterministic HTTP probe witness for one invariant."""

    actor: str  # "owner" | "non_owner" | "anonymous"
    method: str
    path_template: str  # formatted with the scenario path parameters
    body: dict | None = None


@dataclass(frozen=True)
class SecurityInvariant:
    """One trusted security invariant and how to witness it."""

    id: str
    family: str
    kind: str  # KIND_DENY | KIND_ALLOW
    title: str
    route: str
    obligation: str
    expected_statuses: tuple[int, ...]
    probe: ProbeSpec
    rationale: str

    @property
    def is_security_invariant(self) -> bool:
        """True for invariants whose violation is a security regression."""
        return self.kind == KIND_DENY

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "family": self.family,
            "kind": self.kind,
            "title": self.title,
            "route": self.route,
            "obligation": self.obligation,
            "expected_statuses": list(self.expected_statuses),
            "probe": {
                "actor": self.probe.actor,
                "method": self.probe.method,
                "path_template": self.probe.path_template,
                "body": dict(self.probe.body) if self.probe.body else None,
            },
            "rationale": self.rationale,
        }


INVARIANTS: tuple[SecurityInvariant, ...] = (
    SecurityInvariant(
        id="OWN-READ-ALLOW",
        family=FAMILY_AUTHORIZATION,
        kind=KIND_ALLOW,
        title="owner may read their own invoice",
        route=DETAIL_ROUTE,
        obligation=(
            "An authenticated user who owns the invoice must receive HTTP 200 "
            "with the invoice body when requesting it."
        ),
        expected_statuses=(200,),
        probe=ProbeSpec(
            actor="owner",
            method="GET",
            path_template="/api/invoices/{invoice_id}",
        ),
        rationale=(
            "Ordinary owner functionality is a required behavior: a change "
            "that locks the owner out is a regression even if it is 'secure'."
        ),
    ),
    SecurityInvariant(
        id="OWN-READ-DENY",
        family=FAMILY_AUTHORIZATION,
        kind=KIND_DENY,
        title="cross-owner read must be denied",
        route=DETAIL_ROUTE,
        obligation=(
            "An authenticated user who does not own the invoice must be "
            "refused (HTTP 401 or 403) when requesting it."
        ),
        expected_statuses=(401, 403),
        probe=ProbeSpec(
            actor="non_owner",
            method="GET",
            path_template="/api/invoices/{invoice_id}",
        ),
        rationale=(
            "Core ownership/IDOR invariant: resource identity must not be "
            "sufficient for access; ownership must be re-checked per request."
        ),
    ),
    SecurityInvariant(
        id="AUTHN-READ-DENY",
        family=FAMILY_AUTHORIZATION,
        kind=KIND_DENY,
        title="unauthenticated read must be denied",
        route=DETAIL_ROUTE,
        obligation=(
            "An unauthenticated requester must be refused (HTTP 401 or 403) "
            "when requesting the invoice."
        ),
        expected_statuses=(401, 403),
        probe=ProbeSpec(
            actor="anonymous",
            method="GET",
            path_template="/api/invoices/{invoice_id}",
        ),
        rationale=(
            "Authentication precondition: ownership logic is only reachable "
            "behind an authenticated principal."
        ),
    ),
    SecurityInvariant(
        id="OWN-UPDATE-ALLOW",
        family=FAMILY_AUTHORIZATION,
        kind=KIND_ALLOW,
        title="owner may update their own invoice",
        route=DETAIL_ROUTE,
        obligation=(
            "An authenticated owner must receive HTTP 200 when updating "
            "their own invoice."
        ),
        expected_statuses=(200,),
        probe=ProbeSpec(
            actor="owner",
            method="PATCH",
            path_template="/api/invoices/{invoice_id}",
            body={"title": "Consulting retainer Q1 (amended)"},
        ),
        rationale="Ordinary owner write functionality must keep working.",
    ),
    SecurityInvariant(
        id="OWN-UPDATE-DENY",
        family=FAMILY_AUTHORIZATION,
        kind=KIND_DENY,
        title="cross-owner update must be denied",
        route=DETAIL_ROUTE,
        obligation=(
            "An authenticated user who does not own the invoice must be "
            "refused (HTTP 401 or 403) when updating it."
        ),
        expected_statuses=(401, 403),
        probe=ProbeSpec(
            actor="non_owner",
            method="PATCH",
            path_template="/api/invoices/{invoice_id}",
            body={"title": "Rewritten by someone else"},
        ),
        rationale=(
            "Write-side ownership invariant: mutations must be owner-gated "
            "independently of reads."
        ),
    ),
)

_BY_ID = {invariant.id: invariant for invariant in INVARIANTS}


def invariant(invariant_id: str) -> SecurityInvariant:
    """Look up one trusted invariant by id."""
    try:
        return _BY_ID[invariant_id]
    except KeyError:  # pragma: no cover - trusted dictionary misuse
        from shared.errors import InputError

        raise InputError(f"unknown security invariant: {invariant_id}") from None


def invariants_for_route(route: str | None) -> tuple[SecurityInvariant, ...]:
    """All trusted invariants bound to a Flask route template."""
    if not route:
        return ()
    return tuple(inv for inv in INVARIANTS if inv.route == route)


def security_invariants(invariants: tuple[SecurityInvariant, ...]) -> tuple[SecurityInvariant, ...]:
    """Subset whose violation is a security regression (kind == deny)."""
    return tuple(inv for inv in invariants if inv.kind == KIND_DENY)


def as_dict() -> dict:
    """Dictionary section for the evidence document."""
    return {
        "version": DICTIONARY_VERSION,
        "family": FAMILY_AUTHORIZATION,
        "trust": (
            "trusted, versioned, curated in-repo dictionary; fixed before any "
            "candidate execution and independent of the candidate change"
        ),
        "invariants": [inv.as_dict() for inv in INVARIANTS],
    }
