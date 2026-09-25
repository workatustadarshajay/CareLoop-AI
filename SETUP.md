# CareLoop AI: Setup and Run Guide

This guide takes you from a fresh checkout to a running app: paste a doctor's note, Gemini splits it into actionable items, each item is saved as a card in Postgres, and all cards appear in the UI.

Commands are for a Linux or macOS shell. Run them from the repository root (`CareLoop-AI/`) unless a step says otherwise.

| Service | What it is | Port | Start command |
| --- | --- | --- | --- |
| Database | PostgreSQL 16 in Docker | 5432 | `docker compose up -d --wait` |
| Backend | FastAPI app served by Uvicorn | 8000 | `uv run --system-certs uvicorn app.main:app --reload --port 8000` |
| Frontend | React app on the Vite dev server | 5173 | `npm run dev` |

Already set up? Go straight to [Start all servers](#4-start-all-servers).

## Contents

1. [How it fits together](#1-how-it-fits-together)
2. [Prerequisites](#2-prerequisites)
3. [First-time setup](#3-first-time-setup)
4. [Start all servers](#4-start-all-servers)
5. [Verify everything works](#5-verify-everything-works)
6. [Use the app](#6-use-the-app)
7. [Working over VS Code Remote-SSH](#7-working-over-vs-code-remote-ssh)
8. [Stop, restart, and reset](#8-stop-restart-and-reset)
9. [Configuration reference](#9-configuration-reference)
10. [API reference](#10-api-reference)
11. [Troubleshooting](#11-troubleshooting)
12. [Useful commands](#12-useful-commands)

## 1. How it fits together

```mermaid
flowchart LR
    Browser["Browser<br/>localhost:5173"] --> Vite["Vite dev server<br/>:5173"]
    Vite -->|"proxies /api/*"| API["FastAPI backend<br/>127.0.0.1:8000"]
    API -->|"asyncpg"| DB[("PostgreSQL :5432<br/>volume careloop-ai_pgdata")]
    API -->|"save_card tool calls"| Gemini["Gemini API<br/>gemini-3.8-flash"]
```

- The browser only talks to the Vite dev server. Vite forwards every `/api/...` request to the backend at `http://127.0.0.1:8000` (configured in `Frontend/vite.config.ts`). The browser never makes a cross-origin request, and only port 5173 has to be reachable from it.
- When you submit a note, the backend saves it to the `notes` table. A Gemini agent then calls the `save_card` tool once per actionable item, and each call inserts a row into `cards`.
- The note and its cards are saved in one transaction. If Gemini or the database fails, nothing from that note is saved.

## 2. Prerequisites

| Tool | Tested with | Check | Notes |
| --- | --- | --- | --- |
| Docker Engine + Compose v2 | Docker 29.1.3, Compose v2.27.1 | `docker compose version` | Use `docker compose` (with a space). The legacy `docker-compose` 1.29.2 doesn't work reliably with current Docker and can leave the database container renamed. |
| uv | 0.12.13 | `uv --version` | Creates the backend virtualenv and installs dependencies. |
| Python | 3.13.14 | `uv python find 3.13` | The backend needs Python 3.13 or newer. The system `python3` can be older; uv finds the right version, or installs it with `uv python install 3.13`. |
| Node.js + npm | Node 24.14.0, npm 11.9.0 | `node --version` | Runs the Vite dev server. |
| Gemini API key | | | Create one in [Google AI Studio](https://aistudio.google.com/apikey). Keys from other providers are rejected, for example Groq keys that start with `gsk_`. |

> **Corporate networks:** `--system-certs` makes uv trust the operating system's certificate store. You need it behind a TLS-inspecting proxy, and it's harmless elsewhere, so every `uv` command in this guide includes it.

## 3. First-time setup

### 3.1 Start PostgreSQL

```bash
docker compose up -d --wait
docker compose ps
```

Expected: the `db` service is `Up ... (healthy)` and publishes `0.0.0.0:5432->5432/tcp`.

The local database uses user `careloop`, password `careloop`, and database `careloop` (see `docker-compose.yml`). Data is stored in the Docker volume `careloop-ai_pgdata` and survives restarts.

### 3.2 Set up the backend

```bash
cd Backend
uv sync --system-certs
cp .env.example .env
```

`uv sync` creates `Backend/.venv` and installs the versions pinned in `uv.lock`.

Edit `Backend/.env` and replace the placeholder key:

```dotenv
DATABASE_URL=postgresql+asyncpg://careloop:careloop@localhost:5432/careloop
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.8-flash
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Create the tables:

```bash
uv run --system-certs alembic upgrade head
uv run --system-certs alembic current
```

The last command should print `0001_create_notes_and_cards (head)`. The migration creates the `notes` and `cards` tables and the `card_type` and `card_status` enum types. Running `upgrade head` again is safe: it does nothing when the database is already up to date.

### 3.3 Set up the frontend

```bash
cd Frontend
npm install
cp .env.example .env
```

`Frontend/.env` contains one line:

```dotenv
VITE_API_URL=/api
```

Keep it as `/api` so requests go through the Vite proxy. If you point it at `http://localhost:8000/api`, you get the CORS/405 error described in [Troubleshooting](#11-troubleshooting).

## 4. Start all servers

Start the services in this order. The backend checks the database connection at startup and exits if Postgres isn't reachable.

**Step 1: database** (repository root, runs in the background)

```bash
docker compose up -d --wait
```

`--wait` returns once the database healthcheck passes.

**Step 2: backend** (new terminal, keep it open)

```bash
cd Backend
uv run --system-certs uvicorn app.main:app --reload --port 8000
```

The backend is ready when the log shows `Application startup complete.`

With an activated virtualenv, this is equivalent:

```bash
cd Backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Step 3: frontend** (another terminal, keep it open)

```bash
cd Frontend
npm run dev
```

The frontend is ready when Vite prints `Local:   http://localhost:5173/`.

**Step 4:** open <http://localhost:5173> in your browser.

> **Tip:** in VS Code, **Terminal → Split Terminal** keeps the backend and frontend logs side by side.

## 5. Verify everything works

Run these checks on the machine where the servers run:

| Check | Command | Expected result |
| --- | --- | --- |
| Database is healthy | `docker compose ps` (repository root) | `db` is `Up ... (healthy)` |
| Schema is current | `uv run --system-certs alembic current` (in `Backend/`) | `0001_create_notes_and_cards (head)` |
| Backend responds | `curl http://127.0.0.1:8000/api/cards` | `[]` or a JSON list of cards |
| Vite proxy works | `curl http://127.0.0.1:5173/api/cards` | The same JSON as the previous check |

End-to-end test with Gemini. This saves a real note, and its cards show up in the UI:

```bash
curl -i -X POST http://127.0.0.1:8000/api/notes/process \
  -H 'Content-Type: application/json' \
  -d '{"text": "Start amoxicillin 500 mg twice daily for 7 days. Get a chest X-ray this week. Follow up in 2 weeks."}'
```

Expected: `HTTP/1.1 201 Created` and a body with `note_id` and the saved `cards`, for example a `medication`, a `test`, and a `next_visit` card.

## 6. Use the app

1. Open <http://localhost:5173>.
2. Paste a doctor's note (up to 12,000 characters) into **Doctor's note**.
3. Click **Process note**. The button reads **Processing...** while Gemini works.
4. A confirmation shows how many cards were saved. **Your cards** lists every card, newest first.

Each card shows:

- a type: `medication`, `test`, `referral`, `next_visit`, or `general_task`
- a short description
- a status (new cards are `open`)
- a creation date

## 7. Working over VS Code Remote-SSH

This applies when the code runs on a remote machine and your browser runs on your own computer:

- `localhost` in your browser means your computer, not the server. VS Code forwards server ports to your computer; the **Ports** panel lists them.
- Only port **5173** needs to be forwarded, and VS Code usually does this automatically when `npm run dev` starts. If port 5173 is already taken on your computer, VS Code picks another local port. Use the local address shown in the **Ports** panel.
- The `/api` proxy runs inside Vite on the server, so your browser never needs to reach the backend directly.
- To use the Swagger UI, forward port 8000, open the local address the **Ports** panel shows for it, and add `/docs`.

## 8. Stop, restart, and reset

| Goal | Command | Notes and cards kept? |
| --- | --- | --- |
| Stop the backend or frontend | `Ctrl+C` in its terminal | Yes |
| Stop the database | `docker compose stop` | Yes |
| Remove the database container | `docker compose down` | Yes, the volume stays |
| Delete all notes and cards | `docker compose down -v` | **No**, this deletes the `careloop-ai_pgdata` volume |

After `docker compose down -v`, run `docker compose up -d --wait`, then `uv run --system-certs alembic upgrade head` in `Backend/`. You now have an empty database.

What needs a restart after a change:

| You changed | What to do |
| --- | --- |
| `Backend/.env` | Restart the backend. It reads its settings once at startup, and `--reload` only watches Python files. |
| Backend Python code | Nothing. `--reload` restarts the backend. |
| `Frontend/.env` or `Frontend/vite.config.ts` | Nothing. Vite restarts itself; reload the browser tab. |
| React code or CSS | Nothing. The page updates automatically. |
| A new Alembic migration | Run `uv run --system-certs alembic upgrade head` in `Backend/`. |

## 9. Configuration reference

### `Backend/.env`

The backend and Alembic both read this file.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DATABASE_URL` | No | `postgresql+asyncpg://careloop:careloop@localhost:5432/careloop` | Postgres connection string. `postgres://` and `postgresql://` URLs are converted to the asyncpg driver automatically. |
| `GEMINI_API_KEY` | To process notes | none | Gemini API key. `GOOGLE_API_KEY` also works; if both are set, `GEMINI_API_KEY` is used. |
| `GEMINI_MODEL` | No | `gemini-3.8-flash` | Model the agent uses. |
| `CORS_ORIGINS` | No | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated browser origins allowed to call the API directly. Not needed when requests go through the Vite proxy. |
| `DATABASE_POOL_SIZE` | No | `5` | SQLAlchemy connection pool size. |
| `DATABASE_MAX_OVERFLOW` | No | `10` | Extra connections allowed beyond the pool size. |

### `Frontend/.env`

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_URL` | `/api` | Base URL the browser uses for API calls. Keep `/api` for local development. |

Git ignores `.env` files. Never commit API keys; add new variables to the matching `.env.example` instead.

## 10. API reference

Backend base URL: `http://127.0.0.1:8000`. Interactive docs: `/docs`.

| Method | Path | Request body | Success | Errors |
| --- | --- | --- | --- | --- |
| `POST` | `/api/notes/process` | `{"text": "..."}`, 1 to 12,000 characters after trimming whitespace | `201`, `{"note_id": 1, "cards": [...]}` | `422` invalid body, `503` no API key configured, `500` Gemini or database error |
| `GET` | `/api/cards` | none | `200`, all cards, newest first | `500` database error |

Card object:

```json
{
  "id": 1,
  "note_id": 1,
  "type": "medication",
  "description": "Start amoxicillin 500 mg twice daily for 7 days",
  "status": "open",
  "created_at": "2026-09-25T15:25:03.618138Z"
}
```

`type` is one of `medication`, `test`, `referral`, `next_visit`, `general_task`. `status` is `open` or `done`.

## 11. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Browser console shows `blocked by CORS policy: No 'Access-Control-Allow-Origin' header`, often with `GET http://localhost:8000/api/cards ... 405 (Method Not Allowed)` | The frontend is calling `http://localhost:8000` directly. Over Remote-SSH, that's port 8000 on your own computer, which may be a different program. | Set `VITE_API_URL=/api` in `Frontend/.env`, then reload the page. |
| UI shows `Request failed with status 500`, and the Vite terminal shows `http proxy error` with `ECONNREFUSED` | The backend isn't running. | Start it ([Start all servers](#4-start-all-servers), step 2). |
| UI shows `Request failed with status 500`, and the backend log shows `API key not valid ... API_KEY_INVALID` | `GEMINI_API_KEY` is still the placeholder, or it's a key from another provider, such as Groq (`gsk_...`). | Put a Google AI Studio key in `Backend/.env`, then restart the backend. |
| UI shows `Set GEMINI_API_KEY or GOOGLE_API_KEY in Backend/.env before processing a note.` | No key is configured. | Add the key, then restart the backend. |
| UI shows `Request failed with status 500` with any other backend error | An unhandled server error. | Read the traceback in the backend terminal. |
| Backend exits with `Application startup failed` (exit code 3) | The backend can't reach Postgres. | Run `docker compose ps`, start the database with `docker compose up -d --wait`, and check `DATABASE_URL`. |
| `alembic upgrade head` fails with `Connect call failed` or `Connection refused` | Postgres isn't running. | Run `docker compose up -d --wait`, then retry. |
| `docker-compose up` fails, or the container is named `<hash>_careloop-ai-db-1` | The legacy `docker-compose` 1.29.2 was used. | Use `docker compose`. To restore the normal container name, run `docker compose down && docker compose up -d --wait`. Your data is kept. |
| `Bind for 0.0.0.0:5432 failed: port is already allocated` | Another Postgres or container is already using port 5432. | Stop it, or map another host port in `docker-compose.yml` (for example `"5433:5432"`) and use that port in `DATABASE_URL`. |
| Backend shows `[Errno 98] ... address already in use` | Another backend is already running on port 8000. | Find it with `ss -ltnp \| grep :8000` and stop it: `Ctrl+C` in its terminal, or `kill <pid>`. |
| Vite shows `Port 5173 is in use, trying another one...` | Another Vite dev server is running. | Stop it, or use the port Vite prints. The proxy still works. |
| uv shows `UnknownIssuer` or other certificate errors | A TLS-inspecting proxy is on the network. | Include `--system-certs` in every `uv` command. |
| uv can't find Python 3.13 | Python 3.13 isn't installed. | Run `uv python install 3.13`, then `uv sync --system-certs`. |
| Changes to `Backend/.env` have no effect | The backend read its settings at startup. | Restart the backend. |

## 12. Useful commands

```bash
# SQL shell (repository root)
docker compose exec db psql -U careloop -d careloop

# List saved cards without opening a shell
docker compose exec -T db psql -U careloop -d careloop -c 'SELECT id, type, status, description FROM cards ORDER BY id;'

# Follow database logs
docker compose logs -f db

# Migration history (in Backend/)
uv run --system-certs alembic history

# Type-check, build, and lint the frontend (in Frontend/)
npm run build
npm run lint
```
