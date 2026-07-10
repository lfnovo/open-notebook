# Backend Rules (api/ + open_notebook/ + commands/ + prompts/)

Normative rules for working on the Python backend. Architecture and design rationale live in [docs/7-DEVELOPMENT/](../docs/7-DEVELOPMENT/index.md) — this file is only what you must know before changing code. Project-wide rules are in the root [AGENTS.md](../AGENTS.md).

## Commands

- Run API: `uv run uvicorn api.main:app --port 5055` (Swagger at http://localhost:5055/docs)
- Background jobs need the worker: `make worker-start` (`surreal-commands-worker --import-modules commands`)
- Tests: `uv run pytest tests/`
- Lint/typecheck: `ruff check . --fix` and `uv run python -m mypy .`

## API layer (`api/`)

- Structure is routes → services → models. Routers stay thin; business logic goes in `*_service.py`.
- `SupportedProvider` must stay in sync across **four** locations: `api/models.py` (Literal), frontend `ALL_PROVIDERS`, `connection_tester.py` `TEST_MODELS`, and `credentials_service.py` `PROVIDER_ENV_CONFIG`. Adding a provider means touching all four.
- NEVER return API key values from any endpoint — metadata only.
- Every user-supplied URL field must go through `validate_url()` (`open_notebook/utils/url_validation.py`, async) for SSRF protection. Private IPs/localhost are intentionally allowed (self-hosted Ollama, LM Studio).
- Errors: raise typed exceptions from `open_notebook.exceptions` — global handlers map them to HTTP status codes (`NotFoundError`→404, `InvalidInputError`→400, `AuthenticationError`→401, `RateLimitError`→429, `ConfigurationError`→422, `NetworkError`/`ExternalServiceError`→502, `OpenNotebookError`→500). Don't raise bare `HTTPException` for domain errors.
- Requests over `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` (default 100) are rejected by `MaxBodySizeMiddleware` before auth/routing.
- CORS is open by default (`CORS_ORIGINS`); `allow_credentials` flips to `True` only when origins are explicit. No rate limiting built in.

## AI / model provisioning (`open_notebook/ai/`)

- All LLM calls in graph nodes go through `provision_langchain_model()` — never instantiate provider clients directly. It auto-upgrades to `large_context_model` above 105,000 tokens (hard-coded threshold).
- Missing/unconfigured model → raise `ConfigurationError` (not `ValueError`) so the API returns 422.
- Credential-linked models are preferred; `provision_provider_keys()` is the env-var fallback and **mutates `os.environ`** — be aware in tests.
- `DefaultModels.get_instance()` intentionally bypasses the singleton cache (fresh DB fetch each call).

## Graphs (`open_notebook/graphs/`)

- Sync nodes that need async calls use the `asyncio.new_event_loop()` / ThreadPool workaround (see `chat.py`) — fragile, follow the existing pattern exactly.
- Every node wraps LLM calls with `classify_error()`:
  ```python
  except Exception as e:
      exc_class, message = classify_error(e)
      raise exc_class(message) from e
  ```
- Strip extended-thinking output with `clean_thinking_content()` before using model responses.
- Chat checkpoints (SqliteSaver) live at the path in `LANGGRAPH_CHECKPOINT_FILE`.

## Domain (`open_notebook/domain/`)

- `Source.save()` does **NOT** auto-embed — call `source.vectorize()` explicitly (fire-and-forget, returns a command id). `Note.save()` DOES auto-submit `embed_note`.
- `ObjectModel.get()` is polymorphic via ID prefix — the subclass must be imported first or resolution fails.
- `RecordModel` subclasses are singletons — call `clear_instance()` in tests.
- Relationship strings passed to `relate()` must match the schema (`reference`, `artifact`, `refers_to`).

## Database (`open_notebook/database/`)

- New migration = new file `open_notebook/database/migrations/N.surrealql` (+ `N_down.surrealql`) **and** an edit to `AsyncMigrationManager` — migrations are hard-coded, not auto-discovered. They run automatically on API startup.
- No connection pooling — each `repo_*` call opens/closes a connection.
- Transaction-conflict `RuntimeError`s are retriable and logged at DEBUG (don't "fix" the missing stack trace).
- Read the `snl-development:surrealdb-queries` skill notes / SurrealDB docs before writing SurrealQL.

## Background commands (`commands/`)

- Retry config uses a blocklist: `stop_on: [ValueError]` — raise `ValueError` for permanent failures (no retry, job marked `failed`); any other exception auto-retries.
- Submission is fire-and-forget via `submit_command()`; commands must be idempotent-ish under retry.
- Podcast generation uses `max_attempts: 1` on purpose (prevents duplicate episodes); retry is the explicit `POST /podcasts/episodes/{id}/retry` endpoint.

## Prompts (`prompts/`)

- Template path syntax: `Prompter(prompt_template="ask/entry")` → `prompts/ask/entry.jinja` (forward slashes, no extension).
- Data is passed as `data=dict`; dict keys must match template variable names exactly.
- With a `PydanticOutputParser`, Prompter auto-injects `format_instructions` — the template must contain `{{ format_instructions }}` or the parser is silently ignored.
- No template inheritance/composition; templates are flat by design.
- Templates are cached — restart the app after editing.

## Environment knobs to know

| Variable | Meaning |
|---|---|
| `OPEN_NOTEBOOK_ENCRYPTION_KEY` (or `_FILE`) | Required for credential storage; any string, no default |
| `OPEN_NOTEBOOK_CHUNK_SIZE` / `_CHUNK_OVERLAP` | Token-based (default 400 / 15%); restart required |
| `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` | Upload cap (default 100) |
| `LANGGRAPH_CHECKPOINT_FILE` | Chat history SQLite path |
| `CORS_ORIGINS` | Restrict before production |

## Deep dives

[architecture](../docs/7-DEVELOPMENT/architecture.md) · [credentials](../docs/7-DEVELOPMENT/credentials.md) · [content processing](../docs/7-DEVELOPMENT/content-processing.md) · [podcasts](../docs/7-DEVELOPMENT/podcasts.md) · [prompts](../docs/7-DEVELOPMENT/prompts.md) · [change playbooks](../docs/7-DEVELOPMENT/change-playbooks.md) · [testing](../docs/7-DEVELOPMENT/testing.md)
