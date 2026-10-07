# Architecture

Four subsystems, one shared Postgres, and no component that a reviewer has to take
on faith.

## The shape of it

| Layer | What it is | Where it lives |
| --- | --- | --- |
| **React app** | What people actually see and use: patient and doctor/admin views over the same records, role-filtered | `Frontend/` (React 19 + Vite) |
| **API layer** | The rulebook every request passes through: auth, notes, cards, dependencies, care gaps | `Backend/app/main.py` (FastAPI) |
| **Note agent** | The only writer of cards. Reads a note, decides what is actionable, calls `save_card` / `close_card` | `Backend/app/agents/note_agent.py` |
| **Postgres** | One source of truth. Dependencies are just rows linking one card to another — no separate graph database | `docker-compose.yml` |
| **MCP server** | A pure REST client of our own API, so an agent gets exactly the permissions a clinician has | `mcp/server.py` |
| **UrgencyWatcher** | A sidecar that polls a watch directory and files triage results into its own schema | `UrgencyWatcher/watcher.py` |

## Data flow

```
browser ──/api/*──► Vite (dev proxy) ──► FastAPI :8000 ──► Postgres :5432
                                            │
                                            ├─► Gemini          (note extraction, care-gap check)
                                            ├─► MCP server :8100 (six careloop_* tools, REST only)
                                            └─► UrgencyWatcher   (10 s poll, own schema, no UI yet)
```

The React app talks only to Vite, which proxies `/api/*` to FastAPI. The note
agent is the only writer of cards. Gemini is the only model. The MCP server holds
no database credentials at all.

## Where the loop is closed

`close_card(card_id, evidence)` requires the phrase that proves the step happened.
Once a blocker closes, `propagate_risk_updates` re-evaluates everything that was
waiting on it, so the graph heals without anyone remembering to follow up.

## Honest limits

- No EHR or FHIR integration: a human pastes the note.
- One shared demo password (PBKDF2-SHA256, 100k iterations) and no per-user MCP tokens.
- Care-gap coverage uses a second model call; there is no eval harness behind it.
- Triage results exist in the database only — no UI surfaces them yet.
