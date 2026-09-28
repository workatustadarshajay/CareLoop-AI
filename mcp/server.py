"""CareLoop MCP server.

Exposes CareLoop care-plan data and actions as MCP tools so an AI portal, an
agent framework, or a hospital's existing app can integrate with CareLoop over
the Model Context Protocol (Streamable HTTP transport).

The service is standalone (own process, own port — like UrgencyWatcher) but part
of the same project: it talks to the CareLoop REST API over HTTP (httpx), so
every write goes through the API's own rules and dependency/risk invariants —
no direct database access.

Run:
    cd mcp && uv run uvicorn server:app --port 8100
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

import careloop_client as client

# Server name follows the {service}_mcp convention from the MCP builder guide.
mcp = FastMCP("careloop_mcp")


class CareLoopToolInput(BaseModel):
    """Base config shared by every tool input model."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ListPatientsInput(CareLoopToolInput):
    """Input model for careloop_list_patients."""


class ListCardsInput(CareLoopToolInput):
    """Input model for careloop_list_cards."""

    patient_id: int | None = Field(
        default=None,
        description="Restrict results to this patient id (e.g. 1). Omit for all patients.",
        ge=1,
    )
    status: str | None = Field(
        default=None,
        description=(
            "Filter by card status: open, done, at_risk, blocked, or verified_closed. "
            "Omit for every status."
        ),
    )
    limit: int = Field(
        default=50,
        description="Maximum number of cards to return (1-200).",
        ge=1,
        le=200,
    )


class CardIdInput(CareLoopToolInput):
    """Input model for single-card tools."""

    card_id: int = Field(..., description="CareLoop card id (e.g. 12).", ge=1)


class CloseCardInput(CardIdInput):
    """Input model for careloop_close_card."""

    evidence: str = Field(
        ...,
        description=(
            "Phrase proving the step happened, e.g. 'MRI completed on Monday'. "
            "Stored with the closure as the verification record."
        ),
        min_length=3,
        max_length=500,
    )


class FlagRiskInput(CareLoopToolInput):
    """Input model for careloop_flag_card_risk."""

    card_id: int = Field(..., description="CareLoop card id to flag (e.g. 13).", ge=1)
    reason: str = Field(
        ...,
        description="Why the card is at risk, e.g. 'Upstream MRI missed at an outside facility'.",
        min_length=3,
        max_length=500,
    )


class ListNotesInput(CareLoopToolInput):
    """Input model for careloop_list_notes."""

    patient_id: int | None = Field(
        default=None,
        description="Restrict results to this patient id. Omit for all patients.",
        ge=1,
    )
    limit: int = Field(default=20, description="Maximum notes to return (1-100).", ge=1, le=100)


def _out(data: object) -> str:
    """Consistent JSON output for every tool."""
    return json.dumps(data, indent=2, default=str)


async def _call(fn, **kwargs) -> str:
    """Log in to the CareLoop API, run one client call, format consistently."""
    try:
        token = await client._login()
        return _out(await fn(token, **kwargs))
    except client.CareLoopApiError as e:
        return _out({"ok": False, "error": f"CareLoop API error: {e}"})
    except Exception as e:  # noqa: BLE001 - surfaced to the MCP client either way
        return _out({"ok": False, "error": f"CareLoop MCP error: {type(e).__name__}: {e}"})


# --------------------------------------------------------------------------- tools


@mcp.tool(
    name="careloop_list_patients",
    annotations={
        "title": "List CareLoop patients",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def careloop_list_patients(params: ListPatientsInput) -> str:
    """List every CareLoop patient (id and name).

    Use this first when you need to map a patient name from another system to a
    CareLoop patient id for the other careloop_* tools.

    Args:
        params (ListPatientsInput): No parameters; present for schema consistency.

    Returns:
        str: JSON list of {"id": int, "name": str}.
    """
    return await _call(client.list_patients)


@mcp.tool(
    name="careloop_list_cards",
    annotations={
        "title": "List CareLoop cards",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def careloop_list_cards(params: ListCardsInput) -> str:
    """List care-plan cards (commitments) with status, risk, and due dates.

    Cards are the unit of follow-through in CareLoop: one card per commitment
    from a doctor's note (medication, test, referral, next visit, general task).
    Newest first.

    Args:
        params (ListCardsInput): Validated input containing:
            - patient_id (int | None): restrict to one patient
            - status (str | None): open, done, at_risk, blocked, or verified_closed
            - limit (int): 1-200, default 50

    Returns:
        str: JSON list of cards:
        {
            "id": int, "patient_id": int | None, "type": str,
            "description": str, "status": str, "risk_reason": str | None,
            "due_at": str | None, "created_at": str
        }
    """
    return await _call(
        client.list_cards,
        patient_id=params.patient_id,
        status=params.status,
        limit=params.limit,
    )


@mcp.tool(
    name="careloop_get_card",
    annotations={
        "title": "Get one CareLoop card",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def careloop_get_card(params: CardIdInput) -> str:
    """Get one card with its dependency links and risk reason.

    Args:
        params (CardIdInput): Validated input containing:
            - card_id (int): the CareLoop card id

    Returns:
        str: JSON card object (same fields as careloop_list_cards plus
        "description_plain" and "depends_on": [{"upstream_card_id": int,
        "reason": str | None}]), or {"ok": false, "error": str} if not found.
    """
    return await _call(client.get_card, card_id=params.card_id)


@mcp.tool(
    name="careloop_close_card",
    annotations={
        "title": "Close a CareLoop card with evidence",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def careloop_close_card(params: CloseCardInput) -> str:
    """Close a card as verified done because external evidence exists.

    This is the loop-closing move: the card becomes verified_closed and every
    card that depends on it is re-checked (risk clears when upstream is done),
    exactly like the in-app flow. Evidence is mandatory and stored.

    Args:
        params (CloseCardInput): Validated input containing:
            - card_id (int): the CareLoop card id
            - evidence (str): phrase proving completion (e.g. "MRI completed on Monday")

    Returns:
        str: JSON {"ok": true, "card_id": int, "status": "verified_closed",
        "evidence": str, "closed_at": str}, or {"ok": false, "error": str}
        (not found, or already closed).
    """
    return await _call(client.close_card, card_id=params.card_id, evidence=params.evidence)


@mcp.tool(
    name="careloop_flag_card_risk",
    annotations={
        "title": "Flag a CareLoop card at risk",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def careloop_flag_card_risk(params: FlagRiskInput) -> str:
    """Flag a card at risk with a reason (signals from an external system).

    Args:
        params (FlagRiskInput): Validated input containing:
            - card_id (int): the CareLoop card id
            - reason (str): why it is at risk (shown to care coordinators)

    Returns:
        str: JSON {"ok": true, "card_id": int, "status": "at_risk",
        "risk_reason": str}, or {"ok": false, "error": str}.
    """
    return await _call(client.flag_card_risk, card_id=params.card_id, reason=params.reason)


@mcp.tool(
    name="careloop_list_notes",
    annotations={
        "title": "List CareLoop notes",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def careloop_list_notes(params: ListNotesInput) -> str:
    """List recent doctor notes (the source documents cards are created from).

    Args:
        params (ListNotesInput): Validated input containing:
            - patient_id (int | None): restrict to one patient
            - limit (int): 1-100, default 20

    Returns:
        str: JSON list of {"id": int, "patient_id": int | None, "text": str,
        "created_at": str}.
    """
    return await _call(client.list_notes, patient_id=params.patient_id, limit=params.limit)


# --------------------------------------------------------------------------- ASGI app
# uvicorn target: `uvicorn server:app --port 8100` — MCP at /mcp, health at /health.
# custom_route keeps /health inside the same Starlette app whose lifespan runs
# the Streamable HTTP session manager (wrapping the app in another Starlette
# instance drops that lifespan and breaks /mcp with "Task group is not
# initialized").


@mcp.custom_route("/health", methods=["GET"])
async def health(request) -> JSONResponse:
    """Liveness probe for the service (used by the admin setup guide)."""
    return JSONResponse(
        {
            "service": "careloop-mcp",
            "version": "0.1.0",
            "transport": "streamable-http",
            "endpoint": "/mcp",
            "tools": 6,
        }
    )


app = mcp.streamable_http_app()

if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8100)
