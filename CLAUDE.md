# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git workflow
- Create a commit after completing each logical unit of work.
- Do not push to the remote unless asked.
- Use conventional commit messages (feat:, fix:, refactor:).

## Project overview

An LLM chat assistant with a FastAPI backend and a Vue 3 frontend. The backend proxies chat
completions to a self-hosted, OpenAI-compatible LLM server, supports model tool-calling (web
search ships out of the box; adding custom tools is a schema entry in `tools.py` plus a branch in
`tool_handler()` — see "Adding your own tools" in `backend/README.md`), lets users upload documents
for the LLM to reason over, and has an email-based SSO login flow backed by a SQL database (SQLite
by default,
swappable to Postgres). The frontend is a single-page chat UI that talks to the backend over a
separate origin (CORS wildcard-open on the backend, no dev proxy). The UI ships with a small
custom i18n layer (`frontend/src/i18n/`, no external dependency) supporting English and Russian,
defaulting to English, with a toggle in `ConversationSidebar.vue`; the LLM system prompt
(`build_system_prompt()` in `backend/main.py`) defaults to English too, instructing the model to
reply in another language only if asked.

## Project structure

```
backend/
  main.py                 FastAPI app: endpoints, lifespan, chat streaming/tool-call logic
  db.py                   Async SQLAlchemy engine/session, init_db(), get_db() dependency
  models.py               SQLAlchemy models: User, Conversation, Message, UploadedFile
  data_models.py          Pydantic request/response schemas
  tools.py                LLM tool-call schema (`tools`) + web_search() implementation
  document_processing.py  PDF/DOCX/XLSX text extraction (document_to_txt, text_to_docx) — used
                           for chat file uploads
  init_local_storage.py   Per-user local folder creation (add_user_folder)
  cipher.py               Homegrown XOR-keystream cipher used to obfuscate email in SSO redirect
                           (key comes from the required SSO_SECRET_KEY env var)
  requirements.txt, Dockerfile, .python-version, .dockerignore, .gitignore

frontend/
  index.html, vite.config.js, package.json, .env.example
  src/
    main.js, App.vue        App bootstrap; gates the UI behind auth.initAuth()
    router/index.js         Single "/" route -> ChatView
    stores/auth.js          Pinia store: exchanges ?user_info= for a user via /api/login
    stores/chat.js          Pinia store: conversations, messages, NDJSON stream handling
    api/client.js           fetch wrapper (X-User-Email header) + NDJSON stream reader
    utils/markdown.js       renderMarkdown(): markdown-it (+ texmath/KaTeX for math) -> DOMPurify-sanitized HTML
    views/ChatView.vue      Top-level layout: sidebar + message list + input
    components/             ConversationSidebar, MessageList, MessageInput, FileUpload, ToolIndicator
```

## Running the backend

From `backend/`:

```
pip install -r requirements.txt   # or: uv pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8010
```

Docker: `backend/Dockerfile` builds on `python:3.14-slim`, installs deps with `uv`, and runs the
same uvicorn command on port 8010.

There are no tests, linter, or formatter configured in this repo.

### Required environment (`.env` in `backend/`, gitignored, not present in a fresh checkout)

`main.py` reads these via `os.environ[...]` at import time, so the app will not start without them:

- `LOCAL_STORAGE` — base directory for per-user files, chat cache, and chat history.
- `LOCAL_LLM_URL` — base URL of the local OpenAI-compatible LLM server (used for `/v1` chat completions and a custom `/tokenize` endpoint).
- `MODEL_NAME` — model name passed to the LLM server.
- `REDIRECT_URL` — where `/api/sso` redirects after encrypting the user's email (should point at the frontend's origin, e.g. `http://localhost:5173`).
- `SSO_SECRET_KEY` — key used by `cipher.py`'s `SimpleCipher` to encrypt/decrypt the email passed
  through the `/api/sso` → `/api/login` handoff. Required, no default — generate one per deployment
  (`openssl rand -hex 32`); see "Auth" in Architecture below for why this must never be a shared,
  publicly-known value.

Optional:

- `CHAT_RETENTION_DAYS` — if set, enables a background task (`_cleanup_old_conversations_loop()` in
  `main.py`, started in `lifespan()`) that deletes conversations whose `updated_at` is older than
  this many days. Runs once immediately at startup, then once every 24h for the life of the
  process. Unset (the default) disables the task entirely — retention is opt-in, nothing is
  auto-deleted unless this is configured. Deleting a `Conversation` cascades to its `Message`s and
  their `UploadedFile`s (DB-level `ON DELETE CASCADE` on Postgres via migration `0002`, ORM-level
  `cascade="all, delete-orphan"` in `models.py` as the sqlite-compatible fallback — see the
  migrations section below).

- `DATABASE_URL` — read in `db.py` (which calls `load_dotenv()` itself, so it doesn't depend on
  `main.py`'s import order). Defaults to `sqlite+aiosqlite:///./local.db` if unset, so the backend
  runs with zero DB setup. Point it at `postgresql+asyncpg://user:pass@host/db` to switch to
  Postgres — no code changes needed, just avoid Postgres-only column types in `models.py` (e.g. use
  `JSON`, not `JSONB`) to keep it portable.

- `SEARXNG_URL` / `SEARXNG_TIMEOUT` (default `5` seconds) / `SEARCH_PAGE_CHAR_LIMIT` (default
  `1500`) — read in `tools.py`, not `main.py`; see "Web search" below for what they control.
  **Gotcha**: unlike `db.py`, `tools.py` does not call `load_dotenv()` itself, and `main.py` does
  `from tools import *` (which evaluates `tools.py`'s module-level `os.environ.get(...)` calls
  immediately) *before* its own `load_dotenv()` call further down the same import block — so a
  value set only in `backend/.env` (as opposed to a real process/OS environment variable) is
  silently **not** picked up, and `tools.py` logs "SEARXNG_URL не задан" even though `.env` looks
  correct. Doesn't affect the Docker Compose deployment, where these are set as real container
  environment variables rather than loaded from a `.env` file.

## Database migrations (Alembic)

Schema is defined by `backend/models.py` and versioned under `backend/migrations/versions/`
(starting from `0001_initial_schema.py`, which reflects the current `users` / `conversations` /
`messages` / `uploaded_files` tables). `backend/migrations/env.py` is async-aware (uses
`async_engine_from_config` + `connection.run_sync`, matching the app's async engine) and takes its
connection string from `db.DATABASE_URL` — `alembic.ini`'s `sqlalchemy.url` is intentionally left
blank so the URL has one source of truth.

- `alembic upgrade head` — apply pending migrations to whatever `DATABASE_URL` currently points at.
- `alembic revision --autogenerate -m "..."` — generate a new migration after changing `models.py`.

`main.py`'s `lifespan()` runs `alembic upgrade head` programmatically on every startup (via
`_run_migrations()`, calling `alembic.command.upgrade()` on an `AlembicConfig` built from
`backend/alembic.ini` with `script_location` pinned to `backend/migrations` so it doesn't depend on
the process's cwd). This replaced the old `init_db()`/`create_all()` call — Alembic is now the only
thing that creates or changes tables. Since `alembic.command.upgrade()` is a sync call that
internally does its own `asyncio.run()` (see `migrations/env.py`), it's dispatched via
`asyncio.to_thread()` so it doesn't collide with FastAPI's already-running event loop. On a fresh
empty database this creates all tables (same zero-config dev experience as before); once a database
is stamped at the latest revision, it's a fast no-op that doesn't touch existing data. The one
gotcha: an existing database whose tables were created by the old `create_all()` (before this
change) has no `alembic_version` row, so `alembic upgrade head` on it will fail with "table already
exists" — run `alembic stamp head` once on that database to mark it as already at `0001` without
re-running the DDL, then future migrations apply normally on top.

**Delete cascade** (`Conversation` → `Message` → `UploadedFile`): handled at two levels, since
neither alone covers every deletion path.
- ORM level, `models.py`: `Conversation.messages` and `Message.files` relationships carry
  `cascade="all, delete-orphan"`, so `session.delete(conversation)` through SQLAlchemy (app code,
  or an admin tool that deletes via the ORM) cascades in Python regardless of DB backend —
  including sqlite, which doesn't get the DB-level cascade below.
- DB level, migration `0002_cascade_delete_conversations.py`: adds `ON DELETE CASCADE` to the
  `messages.conversation_id` and `uploaded_files.message_id` foreign keys, but **Postgres only** —
  sqlite can't `ALTER` an existing FK constraint without a full table rebuild (Alembic batch mode),
  so the migration is a no-op there (checked via `op.get_bind().dialect.name`) and relies on the
  ORM-level cascade instead. This is what makes a raw `DELETE FROM conversations WHERE ...` (e.g.
  from `psql`/pgAdmin, or a bulk cleanup query that bypasses the ORM) safe against Postgres.

### Missing pieces in a fresh checkout

- Audio transcription (`backend/routers/transcribe.py`) is referenced nowhere currently and is not
  implemented — out of scope for now.

## Running the frontend

From `frontend/`:

```
npm install
npm run dev      # Vite dev server on :5173
```

Copy `.env.example` to `.env` and set `VITE_API_BASE_URL` if the backend isn't at
`http://localhost:8010`. The frontend and backend are always separate origins (no combined static
hosting, no dev proxy) — CORS on the backend is wildcard-open.

## Architecture

**Auth**: no session tokens — this is designed for internal/self-hosted, low-security-bar
deployments (see "Модель безопасности" in the root `README.md`). The company platform (or whatever
trusted layer sits in front) links to `GET /api/sso?email=...`, which encrypts the email with
`cipher.py`'s `SimpleCipher` (homegrown SHA256-keystream XOR, **not** a real crypto scheme, keyed by
the required `SSO_SECRET_KEY` env var) and 303-redirects to `REDIRECT_URL?user_info=<ciphertext>`.
The frontend's `stores/auth.js` picks up `user_info` from the URL, calls `POST /api/login`, which
decrypts it, upserts a `User` row, and returns `{user_id, email}`. From then on the frontend sends
the plain email back as an `X-User-Email` header on every request; `get_current_user` in `main.py`
looks up (or lazily creates) the user by that header — trust, no verification. This means
`/api/sso` must never be exposed directly to untrusted callers: whoever can hit it can log in as
any email. `SSO_SECRET_KEY` has no default specifically so a forked/deployed copy can't be left on
a publicly-known key — but it does not change the fact that `/api/sso` itself performs no
authentication of its own.

For deployments opened directly (no trusted layer in front to hit `/api/sso`), `LoginForm.vue` in
the frontend renders an email+password sign-in/registration form instead, backed by
`POST /api/register` and `POST /api/login/password` in `main.py`. Passwords are hashed with
stdlib `hashlib.pbkdf2_hmac` in `security.py` (`hash_password`/`verify_password`) — no
passlib/bcrypt dependency, matching the project's dependency-light approach — and stored in
`User.password_hash` (nullable, added in migration `0004`; `None` for SSO-only users, which makes
`/api/login/password` reject them rather than call `verify_password()` on a missing hash). Once
either login path succeeds, the rest of the app behaves identically: the frontend still just holds
the plain email and sends it as `X-User-Email` on every request, so password checking only gates
the initial login/registration call, not later requests.

**Persistence** (`db.py` + `models.py`): `User` → `Conversation` → `Message` → `UploadedFile`.
Conversation history is server-authoritative — the frontend never resends the full message array.
Sending a chat message means POSTing just `{conversation_id, message}` (or the multipart
equivalent with files); the backend appends the user `Message`, loads the full history for that
conversation from the DB, and persists the assembled assistant `Message` once streaming finishes.
`Conversation.title` defaults to "Новый чат" and is overwritten once, from a short LLM-generated
title, the first time a conversation gets a reply (see `generate_title()` below).

**LLM client** (`main.py`): a single module-level `llm_client = AsyncOpenAI(...)` is constructed
once at import time (not per-request) with an explicit `LLM_TIMEOUT`
(`httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)`, `max_retries=1`) and a pooled
`httpx.AsyncClient` (`httpx.Limits(max_connections=50, max_keepalive_connections=20)`), so
concurrent chats reuse keep-alive connections instead of each request opening its own. It's closed
in `lifespan()`'s shutdown phase. `check_tokens_chat_history()` / `check_tokens_document()` (the
`/tokenize`-backed pre-checks) catch their own exceptions and fail open (return the untrimmed
history / "not too large") instead of raising, so a temporarily unreachable LLM server surfaces as
one clear error from the actual chat call rather than crashing the endpoint or hanging.

**Chat + tool-calling** (`main.py`):
- `build_system_prompt()` builds the system message fresh on every call (embeds the current date,
  so it stays correct across a long-running process); `build_messages(history)` prepends it to the
  loaded history. Both chat endpoints call `check_tokens_chat_history(build_messages(history))`,
  so the system prompt is included in the `/tokenize` count. If trimming kicks in,
  `check_tokens_chat_history` special-cases a leading system message so it's never the half that
  gets cut.
- `POST /api/v1/chat/completions` — persists the user message, reloads history, trims it if near
  the model's context limit (`check_tokens_chat_history`, which calls the LLM server's
  `/tokenize` endpoint), and streams the reply.
- `POST /api/v1/chat/completions_files` — same, plus saves uploaded files under
  `LOCAL_STORAGE/files_chat_cache` and extracts their text in-process via
  `document_processing.document_to_txt()` (no separate service, no network call — see
  "Document processing" below), appends it into the user's message (`### DOCUMENT START/END ###`
  markers), records an `UploadedFile` row per file, and checks the combined size
  (`check_tokens_document`) before streaming — raises `HTTPException` with 422 ("document too
  large") on failure, so the frontend's generic non-2xx error handling picks it up (an earlier
  version returned trimming/size errors as 206/210, which `fetch`'s `res.ok` treats as success
  since it covers the whole 200-299 range — fixed after that surfaced as a real bug). Per-file
  extraction failures don't fail the request — `document_to_txt()` never raises (it catches its own
  exceptions and returns an English-language error string instead), so a bad file just becomes an
  error message the model sees for that one document instead of aborting the whole upload.
- `generate()` is a recursive async generator that streams *structured events* (dicts, not raw
  text) from the OpenAI-compatible client: `token`, `tool_call_start`, `tool_result`, `error`.
  When the model emits a tool call, it dispatches via `tool_handler` (`web_search` in `tools.py`
  is the only one that ships out of the box — see "Adding your own tools" in `backend/README.md`
  for how to add more), appends the assistant tool-call + tool-result messages, and recurses
  (bounded by `max_depth`, default 5).
  `stream_and_persist()` wraps `generate()`: serializes each event to an NDJSON line (`media_type
  ="application/x-ndjson"`), accumulates the full assistant text + tool events, persists the
  final `Message` row once the stream ends, and appends a trailing `{"type":"done"}` line. On
  connection failure it catches `APIConnectionError`/`APITimeoutError` specifically and yields an
  English-language `error` event instead of a raw exception string. If this was the conversation's
  first message (`title_source_text` passed in), it also calls `generate_title()` — a short
  non-streaming LLM call — updates `Conversation.title`, and yields a `{"type":"title", "title":
  ...}` event before `done`. The frontend's `api/client.js` reads all of this line-by-line to drive
  token-by-token rendering, a tool-use indicator (`ToolIndicator.vue`), and live title updates.
- `GET /api/health` — proxies a health check to `LOCAL_LLM_URL`.

**Web search** (`tools.py`): `web_search()` (called via the `web_search` tool in the `tools`
schema at the top of the file, or forced directly — see "Forced web search" below) queries an
internal SearXNG instance first (`_searxng_text()`, `SEARXNG_URL` env var — set to
`http://searxng:8080` in `docker-compose.yml`, pointing at the `searxng` service added there,
config in `searxng/settings.yml`; request timeout via `SEARXNG_TIMEOUT`, default 5s). It falls
back to the `ddgs` library (`_ddgs_text()`) in two cases: any hard failure (unset `SEARXNG_URL`,
connection error, timeout, bad response — logged as a warning rather than raised), *and* when
SearXNG responds successfully but returns zero results. The second case is common in practice:
SearXNG queries each enabled engine's real public site directly, with no proxy or API layer in
front, and engines like DuckDuckGo/Startpage/Brave routinely CAPTCHA or rate-limit requests once
they flag the server's IP as a datacenter/non-residential address — when that happens to every
enabled engine at once, SearXNG itself doesn't error, it just returns an empty result list, which
is why the empty-results case needs its own fallback check separate from the `except` block.

Each result URL is then fetched concurrently (`process_results()`/`fetch_page()`, bounded by a
semaphore); the response body is read as raw bytes and decoded via `charset_normalizer`
(`_decode_html()`) rather than aiohttp's own `response.text()`, because some sites serve
windows-1251/koi8-r content without a correct `charset` in their headers — aiohttp's strict-UTF-8
decode would raise `UnicodeDecodeError` on those (caught by `fetch_page()`'s `except`, but losing
that page's content in favor of just the search snippet). The decoded HTML is parsed with
BeautifulSoup (strip `script`/`style`/`nav`/`footer`/`header`/`aside`, flatten to text), truncated
to `SEARCH_PAGE_CHAR_LIMIT` characters per page (env var, default 1500), and concatenated into one
string returned to the model. Both the tool's schema `description` and `build_system_prompt()`'s
system message instruct the model to cite sources as markdown links (`[source name](URL)`)
rather than plain site/article names, since assistant messages are rendered through `markdown-it`
on the frontend — a plain-text citation never becomes clickable there.

Known limitation, candidate for a future improvement: the per-page character limit is a blind
`text[:SEARCH_PAGE_CHAR_LIMIT]` — whatever text happens to come first on the page (often
navigation/intro boilerplate) is what the model sees, regardless of whether it's the part relevant
to the query. Options considered but not yet implemented: keyword-overlap or BM25 paragraph
scoring (cheap, dependency-light, but Russian morphology and glued number+unit tokens like `400мм`
make exact-text matching unreliable), embeddings/vector similarity (handles that better but needs
a new ML dependency), and LLM-based extraction — an extra non-streaming call to the already-existing
`llm_client` (same pattern as `generate_title()`) asking the model to pull the query-relevant part
out of each fetched page's raw text. The LLM-extraction option is the leading candidate: it needs
no new dependency and is robust to morphology/synonyms/units since the model handles semantics
directly, at the cost of extra latency/load on the LLM server for each web search.

**Forced web search**: the frontend's "Поиск в интернете" toggle (`MessageInput.vue`) lets the
user guarantee a web search happens for their message, instead of leaving that decision to the
model's own tool-call judgment. `ChatMessageRequest.force_web_search`
(`/api/v1/chat/completions`) and a matching `force_web_search` form field
(`/api/v1/chat/completions_files`) carry this through `stream_and_persist()` into `generate()`.
When set, `generate()` runs the search directly via the same `tool_handler("web_search", query)`
used for organic model-initiated calls — using the raw user message text as the query, *before*
the model's first completion call — yielding the same `tool_call_start`/`tool_result` events an
organic call would (so `ToolIndicator.vue` shows the same "Searching the internet" label either
way, via the `tool.web_search` i18n key), then
appends synthetic assistant/tool messages to `messages` and recurses into the normal flow so the
model still sees the results and can call further tools if it wants. The forced search only fires
once: the recursive call doesn't pass `force_web_search` along, so it can't repeat at deeper
recursion levels.

**Frontend state** (Pinia): `stores/auth.js` owns login/identity; `stores/chat.js` owns
conversations, the active conversation's messages, and in-flight streaming state
(`streamingText`, `toolStatus`, `error`) fed by the `onEvent` callback passed into
`api/client.js`'s `streamChat`/`streamChatWithFiles`. Both calls are wrapped in try/catch so any
stream/fetch failure still resolves to `{ok: false}` and resets `streaming`, instead of leaving the
UI stuck loading. A `"title"` event updates the matching conversation's title in place. Assistant
message content (both finished messages and the live `streamingText`) is rendered through
`utils/markdown.js`'s `renderMarkdown()` (`v-html` in `MessageList.vue`); user messages are always
plain text. `renderMarkdown()` also runs `markdown-it-texmath` (KaTeX engine) so `$...$`, `$$...$$`,
`\(...\)`, and `\[...\]` render as math instead of raw LaTeX; links get `target="_blank"` +
`rel="noopener noreferrer"` forced via a custom `link_open` rule, with `ADD_ATTR: ["target"]` passed
to `DOMPurify.sanitize()` since `target` isn't in its default attribute allowlist.
`chat.newConversation()` is single-flight: if the current conversation is already empty it's reused
instead of creating a duplicate, and concurrent calls (double-clicking "New chat") share one
in-flight creation promise (`_creatingConversation`) — the reuse check matches against the literal
title `"New chat"`, the same default `models.Conversation.title` uses server-side. `MessageInput.vue`
accepts files both via the `FileUpload.vue` picker and by dragging them onto the composer (`@drop`,
tracked with a `dragDepth` counter to avoid flicker from nested drag events). It also has a sticky
"Web search" toggle (`webSearchEnabled`, doesn't reset after sending, labeled via the `chat.webSearch`
i18n key) that's passed as `forceWebSearch` through `chat.sendMessage()`/`chat.sendMessageWithFiles()`
into `api/client.js`'s `streamChat`/`streamChatWithFiles`, which send it to the backend as
`force_web_search` — see "Forced web search" above.

**i18n** (`frontend/src/i18n/`): a small hand-rolled layer, not a library like vue-i18n, in keeping
with the project's dependency-light approach. `locales/en.js` and `locales/ru.js` export flat
dictionaries of nested keys; `index.js` exposes a reactive `locale` ref (Vue `ref`, so it's usable
both from `<script setup>` templates and from plain Pinia store files like `stores/chat.js` and
`stores/auth.js`, not just components), a `t(key, vars)` lookup function (falls back to English if
a key is missing from the active locale, then returns the raw key if missing from both), and
`setLocale()`, which persists the choice to `localStorage` (`app_llm_locale`) and updates
`document.documentElement.lang` / `document.title` via a `watch`. Default locale is English unless
`localStorage` already has a stored choice. `ConversationSidebar.vue` renders the EN/RU toggle
buttons. Locally-generated user-facing strings that used to be hardcoded Russian (e.g. the
`"[Sent N file(s)]"` placeholder shown before a file-upload message is confirmed, in `stores/chat.js`)
now go through `t()` too, so they follow the active locale like everything else — this is distinct
from the *assistant's reply* language, which is controlled independently by the backend's system
prompt (see "Project overview" above), not by the frontend's selected UI locale.

Logging is configured globally in `main.py` to append to `backend/fastapi_backend.log` (tracked in
git).

**Document processing** (`backend/document_processing.py`): `document_to_txt()` auto-routes by file
extension — `.pdf` via `pypdfium2` (text-layer extraction only; a scanned/image PDF with no text
layer returns an English-language string telling the model to inform the user, not raw OCR — there
is no OCR in this codebase, deliberately, to keep the whole app CPU-only and dependency-light),
`.docx` via `python-docx` (paragraph text), `.xlsx` via `openpyxl` (each sheet rendered as a
markdown table). Any other extension, or any exception during extraction, produces an
English-language explanatory string rather than raising — `document_to_txt()` never throws, so a
bad/unsupported file degrades to an error message the model can relay, instead of failing the whole
request. This function backs per-file extraction in `/api/v1/chat/completions_files`. There is
intentionally no separate
document-processing microservice, no OCR, and no GPU/ML dependency (`torch`/`docling`/`easyocr`
were removed) — this trades away scanned-document support for a much lighter, GPU-free deployment
footprint, which fits the project's target audience of small self-hosted setups better than an
optional heavier OCR mode would.
