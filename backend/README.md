# backend

FastAPI application: streaming chat endpoints, model tool-calling (web search out of the box, easy
to extend with your own tools — see "Adding your own tools" below), document upload and
processing, email-based SSO login, history stored in a SQL database (SQLite by default, switchable
to Postgres).

## Running

```bash
pip install -r requirements.txt   # or: uv pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8010
```

## Required environment variables (`.env` in this directory)

`main.py` and `cipher.py` read these at import time — the app won't start without them:

- `LOCAL_STORAGE` — base directory for user files, chat cache, and history.
- `LOCAL_LLM_URL` — base URL of the self-hosted OpenAI-compatible LLM server.
- `MODEL_NAME` — model name passed to the LLM server.
- `REDIRECT_URL` — where `/api/sso` redirects after encrypting the email (the frontend's
  address, e.g. `http://localhost:5173`).
- `SSO_SECRET_KEY` — key used to encrypt/decrypt the email in the SSO redirect. Generate with:
  `openssl rand -hex 32`. See "Security model" in the root `README.md` — this is not full
  authentication, it's a trust-based scheme for deployment behind your own SSO/VPN.

## Optional variables

- `CHAT_RETENTION_DAYS` — if set, enables background cleanup of conversations older than the
  given number of days (checked once every 24 hours, plus one run immediately at startup).
  Disabled by default — nothing is deleted automatically.
- `DATABASE_URL` — connection string (`db.py` calls `load_dotenv()` independently of `main.py`).
  Defaults to `sqlite+aiosqlite:///./local.db`. For Postgres:
  `postgresql+asyncpg://user:pass@host/db` — no code changes needed, just keep the models in
  `models.py` portable (`JSON`, not `JSONB`, etc.).
- `SEARXNG_URL` / `SEARXNG_TIMEOUT` (default `5` sec) / `SEARCH_PAGE_CHAR_LIMIT` (default
  `1500`) — web search settings, see `tools.py`. If SearXNG is unreachable or returns no
  results, search automatically falls back to the `ddgs` library.

## Migrations (Alembic)

The DB schema is versioned under `migrations/versions/`. On every startup (`lifespan()`),
`main.py` runs `alembic upgrade head` itself — on a fresh database this creates all tables, on an
already-migrated one it's a fast no-op. Manually:

```bash
alembic upgrade head
alembic revision --autogenerate -m "..."
```

## Adding your own tools

Model tool-calling is intentionally minimal — `tools.py` defines the `tools` list (OpenAI-style
function schemas) and `web_search()`, the only tool that ships out of the box. To add your own:

1. Append a new `{"type": "function", "function": {...}}` entry to the `tools` list in
   `tools.py`, with a `name`, a `description` (this is what the model reads to decide when to call
   it — be specific), and a JSON-schema `parameters` block, matching the shape of the existing
   `web_search` entry.
2. Handle that `name` in `tool_handler()` in `main.py` — it's a single `if tool_name == "..."`
   dispatch — and return the string the model should see as the tool's result (fetch from an API,
   query a database, read a file, whatever your tool needs to do).

That's the whole integration surface: no plugin system, no registration step, just a schema entry
plus a branch in `tool_handler()`.

## Tests

The repository has no tests, linter, or formatter.
