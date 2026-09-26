"""Trusted SATRA-RV baseline: invoice service with owner-only access.

Demonstration application for the SATRA-RV fixture suite.  Every invoice is
owned by exactly one user; only the owner may read or update it.  The
session is established through POST /api/login and carried by the standard
Flask cookie session.
"""

from __future__ import annotations

from dataclasses import dataclass

from flask import Flask, abort, jsonify, request, session

from formatting import format_cents


@dataclass
class Invoice:
    invoice_id: int
    owner_id: int
    title: str
    status: str
    amount_cents: int

    def as_dict(self) -> dict:
        return {
            "invoice_id": self.invoice_id,
            "owner_id": self.owner_id,
            "title": self.title,
            "status": self.status,
            "amount_cents": self.amount_cents,
            "amount_display": format_cents(self.amount_cents),
        }


# Fixture world: user 1 (alice) owns invoice 1; user 2 (bob) does not.
USERS: dict[int, dict] = {
    1: {"user_id": 1, "username": "alice", "password": "alice-invoice-secret", "name": "Alice"},
    2: {"user_id": 2, "username": "bob", "password": "bob-invoice-secret", "name": "Bob"},
}
USERNAME_INDEX = {user["username"]: user for user in USERS.values()}

INVOICES: dict[int, Invoice] = {
    1: Invoice(
        invoice_id=1,
        owner_id=1,
        title="Consulting retainer Q1",
        status="sent",
        amount_cents=250000,
    ),
}


def _current_user() -> dict:
    user_id = session.get("user_id")
    if user_id is None:
        abort(401)
    user = USERS.get(int(user_id))
    if user is None:
        abort(401)
    return user


def _load_invoice(invoice_id: int) -> Invoice:
    invoice = INVOICES.get(invoice_id)
    if invoice is None:
        abort(404)
    return invoice


def create_app() -> Flask:
    # Fixture-only session key; a real deployment would source it from the
    # environment.  It is not part of the security property under review.
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "satra-rv-fixture-session-key"
    app.config["TESTING"] = True

    @app.post("/api/login")
    def login():
        payload = request.get_json(silent=True) or {}
        user = USERNAME_INDEX.get(str(payload.get("username", "")))
        if user is None or payload.get("password") != user["password"]:
            abort(401)
        session["user_id"] = user["user_id"]
        return jsonify({"user_id": user["user_id"], "username": user["username"]})

    @app.get("/api/me")
    def me():
        user = _current_user()
        return jsonify({"user_id": user["user_id"], "username": user["username"]})

    @app.get("/api/invoices")
    def list_invoices():
        user = _current_user()
        owned = [
            invoice.as_dict()
            for invoice in INVOICES.values()
            if invoice.owner_id == user["user_id"]
        ]
        return jsonify({"invoices": owned})

    @app.get("/api/invoices/<int:invoice_id>")
    def get_invoice(invoice_id: int):
        user = _current_user()
        invoice = _load_invoice(invoice_id)
        if invoice.owner_id != user["user_id"]:
            abort(403)
        return jsonify(invoice.as_dict())

    @app.patch("/api/invoices/<int:invoice_id>")
    def update_invoice(invoice_id: int):
        user = _current_user()
        invoice = _load_invoice(invoice_id)
        if invoice.owner_id != user["user_id"]:
            abort(403)
        payload = request.get_json(silent=True) or {}
        if "title" in payload:
            invoice.title = str(payload["title"])
        return jsonify(invoice.as_dict())

    return app
