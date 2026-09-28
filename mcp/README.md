# CareLoop MCP server

Exposes CareLoop care-plan data and actions as **MCP tools** (Model Context
Protocol, Streamable HTTP) so an AI portal, an agent framework, or a hospital's
existing app can integrate with CareLoop.

## Architecture

The server is a **pure REST API client** (httpx). It holds no database
connection and imports nothing from `Backend/` — every read and write goes
through the CareLoop API's own endpoints, so its auth, validation, and
dependency/risk invariants always apply.

```
MCP client ──Streamable HTTP──> mcp/server.py (FastMCP, port 8100)
                                    │ httpx + Bearer token
                                    ▼
                              CareLoop API (Backend, /api/...) ──> Postgres
```

### Configuration (env vars)

| Variable            | Default                     | Purpose                          |
| ------------------- | --------------------------- | -------------------------------- |
| `CARELOOP_API_URL`  | `http://localhost:8000/api` | CareLoop API base URL            |
| `CARELOOP_USERNAME` | `dr_smith`                  | Service account username         |
| `CARELOOP_PASSWORD` | `password`                  | Service account password         |

The server logs in once per tool call and sends `Authorization: Bearer <token>`
on every request. Use a dedicated service account in production.

### Tools

| Tool                     | API calls used                                                              |
| ------------------------ | --------------------------------------------------------------------------- |
| `careloop_list_patients` | `GET /patients`                                                              |
| `careloop_list_cards`    | `GET /cards` (patient/status/limit filters applied client-side)              |
| `careloop_get_card`      | `GET /cards` filtered by id + `GET /cards/{id}/dependencies`                 |
| `careloop_close_card`    | `PATCH /cards/{id}` `{"status": "verified_closed"}` — API clears risk and re-checks dependents |
| `careloop_flag_card_risk`| `PATCH /cards/{id}` `{"status": "at_risk"}`                                  |
| `careloop_list_notes`    | *(no note-list endpoint exists yet; returns `[]`)*                           |

### Known API gaps

* The API has no `GET /cards/{id}` route — the tool fetches the card list and
  filters by id.
* `PATCH /cards/{id}` has no `risk_reason` field, so `careloop_flag_card_risk`
  can only set the status; the reason is echoed back in the tool result.
* Closure `evidence` has no API field either; it is included in the tool result
  as the audit record.

## Run

```bash
# 1. Start the CareLoop API (Backend)
cd Backend && uv run uvicorn app.main:app --port 8000

# 2. Point the MCP server at it and start it
cd mcp
CARELOOP_API_URL=http://localhost:8000/api \
CARELOOP_USERNAME=dr_smith CARELOOP_PASSWORD=password \
uv run uvicorn server:app --port 8100
```

- MCP endpoint: `http://localhost:8100/mcp` (Streamable HTTP)
- Health probe: `http://localhost:8100/health`

## Demo client

`demo_client.py` is a dependency-free MCP client (urllib, JSON-RPC 2.0, SSE
parsing) that runs a 7-step demo against the running server:

```bash
uv run python demo_client.py
```
