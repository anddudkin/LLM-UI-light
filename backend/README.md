# backend

FastAPI application: streaming chat endpoints, model tool-calling (web search, internal
company-data lookup), document upload and processing, email-based SSO login, history stored in a
SQL database (SQLite by default, switchable to Postgres).

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

## Missing pieces in a fresh checkout

`info_hr.docx` — loaded at startup (`document_to_txt("info_hr.docx")`) and backs the
`company_data_search` tool. It's not included in the repository (it's internal data specific to
one company). `document_to_txt()` doesn't raise on a missing file — it just returns an
error-description string, and the model will relay that string on every `company_data_search`
call. Put your own `.docx` describing your company under this name, or remove the
`company_data_search` tool from `tools.py`/`main.py` if you don't need it.

## Tests

The repository has no tests, linter, or formatter.
