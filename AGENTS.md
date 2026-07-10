# Open Notebook — Agent Rules

Open Notebook is an open-source, privacy-focused alternative to Google's Notebook LM: an
AI-powered research assistant with multi-provider AI support, fully self-hostable.

This file holds the project-wide rules every coding session needs. Component rules:
[open_notebook/AGENTS.md](open_notebook/AGENTS.md) (backend — also covers `api/`, `commands/`,
`prompts/`) and [frontend/AGENTS.md](frontend/AGENTS.md). Knowledge lives in the docs (see
[Where to look](#where-to-look)) — read it on demand instead of guessing.

## Stack, ports, startup order

Three tiers: Next.js frontend (3000) → FastAPI (5055) → SurrealDB (8000).

Start in this order — each tier depends on the one below:

1. `make database` — SurrealDB (API fails without it)
2. `make api` — FastAPI; **schema migrations run automatically on startup** (check logs)
3. `make worker-start` — surreal-commands worker. **Required**: podcasts, embeddings and source
   processing are async jobs that silently queue forever without it
4. `make frontend` — UI (depends on the API for all data)

Or all at once: `make start-all` (status: `make status`, stop: `make stop-all`).

## Commands

- Tests: `uv run pytest tests/`
- Python lint/typecheck: `ruff check . --fix` · `uv run python -m mypy .`
- Frontend (inside `frontend/`): `npm run lint` · `npm run test` · `npm run build`
- Docker release: `make docker-release` (see `.github/RELEASE_PROCESS.md`)

## Hard rules

- **Async-first**: every DB query, graph invocation and AI call is `await`-ed. No sync DB access.
- **Never commit secrets.** Credentials are encrypted at rest and require
  `OPEN_NOTEBOOK_ENCRYPTION_KEY` to be set.
- CORS is wide-open and auth is a simple password middleware — **dev defaults, not production
  hardening**. Don't build features that assume otherwise.
- Product direction questions (does this feature fit?) → [VISION.md](VISION.md). Past decisions
  ("why is it like this?") → [docs/7-DEVELOPMENT/decisions/](docs/7-DEVELOPMENT/decisions/).
  Structural decisions made while coding should produce a new decision record there.

## Where to look

| Need | Location |
|---|---|
| Architecture (3 tiers, workflows, data model) | [docs/7-DEVELOPMENT/architecture.md](docs/7-DEVELOPMENT/architecture.md) |
| Step-by-step recipes (add endpoint, migration, i18n…) | [docs/7-DEVELOPMENT/change-playbooks.md](docs/7-DEVELOPMENT/change-playbooks.md) |
| Dev environment setup | [docs/7-DEVELOPMENT/development-setup.md](docs/7-DEVELOPMENT/development-setup.md) |
| Code standards & testing | [docs/7-DEVELOPMENT/code-standards.md](docs/7-DEVELOPMENT/code-standards.md) · [testing.md](docs/7-DEVELOPMENT/testing.md) |
| Product identity & current posture | [VISION.md](VISION.md) |
| Decision log (ADRs/PDRs) | [docs/7-DEVELOPMENT/decisions/](docs/7-DEVELOPMENT/decisions/) |
| Contribution process (issue-first, PRs) | [docs/7-DEVELOPMENT/contributing.md](docs/7-DEVELOPMENT/contributing.md) |
| User/operator docs (install, configure, troubleshoot) | [docs/](docs/index.md) |
