# Contributing

## Development environment

- Backend: `backend/README.md` — FastAPI, Python 3.14, dependencies in `backend/requirements.txt`.
- Frontend: Vue 3 + Vite, `cd frontend && npm install && npm run dev`.
- The fastest way to bring everything up at once is `docker compose up --build` from the repo
  root (see the root `README.md`).

The repository has **no** automated tests, linter, or formatter — verify changes manually by
running the app and walking through the main flow (see the "Verification" section in the task
description if you're working from a plan, or just try chat + file upload + web search by hand).

## Commits

Uses [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `refactor:`,
`docs:`, `chore:`, etc. One commit per logical unit of work.

## Pull requests

- Describe what changed and why (not just "what" — that's usually visible from the diff).
- If you change environment variables or docker-compose — update `.env.example` and
  `README.md`/`CLAUDE.md` accordingly, so the docs don't drift from the code.
- Small, focused PRs are preferred over large mixed ones.

## Language

Code, comments, and the LLM system prompt are in English. The frontend UI is bilingual
(English/Russian) via `frontend/src/i18n/`; when adding a user-facing string, add a key to both
`locales/en.js` and `locales/ru.js` rather than hardcoding text in a component.
