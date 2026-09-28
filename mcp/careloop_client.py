"""CareLoop REST API client for the MCP server.

Everything talks to the CareLoop API over HTTP (httpx) — no direct database
access, no Backend imports. The MCP server is just another API consumer: it
logs in once with a service account (env `CARELOOP_USERNAME` /
`CARELOOP_PASSWORD`, default dr_smith/password) and sends
`Authorization: Bearer <token>` on every call.

Env vars:
    CARELOOP_API_URL   base URL (default http://localhost:8000/api)
    CARELOOP_USERNAME  service account username (default dr_smith)
    CARELOOP_PASSWORD  service account password (default password)

Known API limitations (handled here, not hidden):
    * No GET /cards/{id} — we filter the GET /cards list by id.
    * PATCH /cards/{id} has no reason field, so flag-at-risk can only set the
      status; the reason is echoed back in the tool result instead.
"""

from __future__ import annotations

import os
from datetime import datetime

import httpx

DEFAULT_API_URL = os.environ.get("CARELOOP_API_URL", "http://localhost:8000/api")
DEFAULT_USERNAME = os.environ.get("CARELOOP_USERNAME", "dr_smith")
DEFAULT_PASSWORD = os.environ.get("CARELOOP_PASSWORD", "password")

CLOSED_STATUSES = {"done", "verified_closed"}


class CareLoopApiError(Exception):
    """Raised when the CareLoop API returns an error or unreachable response."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _client() -> httpx.AsyncClient:
    """Fresh client per call: simple, no shared event-loop state."""
    return httpx.AsyncClient(base_url=DEFAULT_API_URL, timeout=30.0)


async def _request(method: str, path: str, token: str | None = None, **kwargs) -> httpx.Response:
    async with _client() as c:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            resp = await c.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as e:
            raise CareLoopApiError(f"CareLoop API unreachable at {DEFAULT_API_URL}: {e}") from e
    if resp.status_code >= 400:
        detail = resp.json().get("detail", resp.text) if "json" in resp.headers.get("content-type", "") else resp.text
        raise CareLoopApiError(f"CareLoop API {resp.status_code} on {method} {path}: {detail}", resp.status_code)
    return resp


async def _login() -> str:
    resp = await _request("POST", "/auth/login", json={
        "username": DEFAULT_USERNAME,
        "password": DEFAULT_PASSWORD,
    })
    token = resp.json().get("token")
    if not token:
        raise CareLoopApiError("Login succeeded but no token was returned.")
    return token


# --------------------------------------------------------------------------- reads

async def list_patients(token: str) -> list[dict]:
    """All patients: id and name (GET /patients)."""
    resp = await _request("GET", "/patients", token=token)
    return [{"id": p["id"], "name": p["name"]} for p in resp.json()]


async def list_cards(
    token: str,
    patient_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Cards, newest first, optionally filtered client-side (GET /cards)."""
    resp = await _request("GET", "/cards", token=token)
    cards = sorted(resp.json(), key=lambda c: c["created_at"], reverse=True)
    if patient_id is not None:
        cards = [c for c in cards if c.get("patient_id") == patient_id]
    if status is not None:
        cards = [c for c in cards if c.get("status") == status]
    return [
        {
            "id": c["id"],
            "patient_id": c.get("patient_id"),
            "type": c["type"],
            "description": c["description"],
            "status": c["status"],
            "risk_reason": c.get("risk_reason"),
            "due_at": c.get("due_at"),
            "created_at": c["created_at"],
        }
        for c in cards[:limit]
    ]


async def get_card(token: str, card_id: int) -> dict | None:
    """One card plus upstream dependency links (GET /cards filtered by id)."""
    resp = await _request("GET", "/cards", token=token)
    match = next((c for c in resp.json() if c["id"] == card_id), None)
    if match is None:
        return None

    deps_resp = await _request("GET", f"/cards/{card_id}/dependencies", token=token)
    deps = deps_resp.json().get("dependencies", [])
    upstream = [
        {
            "upstream_card_id": d.get("upstream_card_id") or d.get("upstream", {}).get("id"),
            "reason": d.get("reason"),
        }
        for d in deps
    ]
    return {
        "id": match["id"],
        "patient_id": match.get("patient_id"),
        "type": match["type"],
        "description": match["description"],
        "description_plain": match.get("description_plain"),
        "status": match["status"],
        "risk_reason": match.get("risk_reason"),
        "due_at": match.get("due_at"),
        "created_at": match["created_at"],
        "depends_on": upstream,
    }


async def list_notes(token: str, patient_id: int | None = None, limit: int = 20) -> list[dict]:
    """Not supported by the current CareLoop API; the API exposes note
    *processing* (POST /notes/process) but no note listing. Returns an empty
    list rather than guessing at an endpoint that does not exist."""
    return []


# --------------------------------------------------------------------------- writes

async def close_card(token: str, card_id: int, evidence: str) -> dict:
    """Evidence-verified close via PATCH /cards/{id} status=verified_closed.

    The API clears risk_reason and re-checks dependents (propagate_risk_updates)
    on closed statuses, so the risk propagation invariant still holds.
    Evidence has no API field; it is echoed in the result as the audit record.
    """
    resp = await _request("GET", "/cards", token=token)
    match = next((c for c in resp.json() if c["id"] == card_id), None)
    if match is None:
        return {"ok": False, "error": f"Card {card_id} not found."}
    if match["status"] in CLOSED_STATUSES:
        return {
            "ok": False,
            "error": f"Card {card_id} is already closed (status: {match['status']}).",
            "card_id": card_id,
            "status": match["status"],
        }

    await _request("PATCH", f"/cards/{card_id}", token=token, json={"status": "verified_closed"})
    return {
        "ok": True,
        "card_id": card_id,
        "status": "verified_closed",
        "evidence": evidence.strip(),
        "closed_at": datetime.now().isoformat(timespec="seconds"),
    }


async def flag_card_risk(token: str, card_id: int, reason: str) -> dict:
    """Mark a card at_risk via PATCH /cards/{id} status=at_risk.

    API limitation: PATCH has no reason field, so `reason` is echoed back in
    the result for the caller's audit trail instead of being persisted.
    """
    resp = await _request("GET", "/cards", token=token)
    match = next((c for c in resp.json() if c["id"] == card_id), None)
    if match is None:
        return {"ok": False, "error": f"Card {card_id} not found."}
    if match["status"] in CLOSED_STATUSES:
        return {
            "ok": False,
            "error": f"Card {card_id} is closed (status: {match['status']}); cannot flag at risk.",
            "card_id": card_id,
        }

    await _request("PATCH", f"/cards/{card_id}", token=token, json={"status": "at_risk"})
    return {
        "ok": True,
        "card_id": card_id,
        "status": "at_risk",
        "risk_reason": None,
        "reason": reason.strip(),
        "note": "API PATCH /cards/{id} has no risk_reason field; reason not persisted.",
    }
