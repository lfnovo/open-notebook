# Backend Rules (api/ + open_notebook/ + commands/ + prompts/)

Normative rules for working on the Python backend. Architecture and design rationale live in [docs/7-DEVELOPMENT/](../docs/7-DEVELOPMENT/index.md) — this file is only what you must know before changing code. Project-wide rules are in the root [AGENTS.md](../AGENTS.md).

## Commands

- Run API: `make api` (runs `run_api.py`: uvicorn with reload on 127.0.0.1:5055; Swagger at http://localhost:5055/docs)
- Background jobs need the worker: `make worker-start` (`surreal-commands-worker --import-modules commands`)
- Tests: `uv run pytest tests/`
- Lint/format/typecheck: `uv run ruff check . --fix`, `uv run ruff format .` and `uv run python -m mypy .` (CI runs `ruff format --check`)

## API layer (`api/`)

- Routers (`api/routers/`) call domain models and `repo_*` functions directly. Logic goes in an `api/*_service.py` module only when it's shared or orchestrates jobs (`command_service`, `credentials_service`, `podcast_service`). New routers are registered in `api/main.py` with `prefix="/api"`.
- Provider metadata (env vars, modalities, test models, discovery URLs, docs links) lives in the registry: `open_notebook/ai/provider_registry.py` `PROVIDERS`. `TEST_MODELS`, `PROVIDER_ENV_CONFIG`, `PROVIDER_MODALITIES` and `OPENAI_COMPAT_PROVIDERS` are derived from it, and `GET /api/providers` exposes it. Adding a provider takes the registry entry **plus four hand-maintained copies**: the `SupportedProvider` Literal (`api/models.py`), `PROVIDER_CONFIG` (`open_notebook/ai/key_provider.py`), `env_var_map` in `get_provider_availability()` (`api/routers/models.py`) and `PROVIDER_DISCOVERY_FUNCTIONS` (`open_notebook/ai/model_discovery.py`). Tests catch a missing Literal or discovery entry, not the other two. Follow the [Add an AI provider](../docs/7-DEVELOPMENT/change-playbooks.md#playbook-add-an-ai-provider) playbook. The frontend consumes `GET /api/providers` at runtime (`useProviders()`), so a simple API-key provider needs no frontend edit; the registry declaration order is the display order.
- NEVER return API key values from any endpoint — metadata only.
- Every user-supplied URL field must go through `validate_url()` (`open_notebook/utils/url_validation.py`, async) for SSRF protection. Private IPs/localhost are intentionally allowed (self-hosted Ollama, LM Studio).
- Errors: raise typed exceptions from `open_notebook.exceptions` — global handlers map them to HTTP status codes (`NotFoundError`→404, `InvalidInputError`→400, `AuthenticationError`→401, `UnsupportedTypeException`→415, `RateLimitError`→429, `ConfigurationError`→422, `NetworkError`/`ExternalServiceError`→502, other `OpenNotebookError`→500). Don't raise bare `HTTPException` for domain errors. A router's catch-all `except Exception` (sanitized 500) must come after `except OpenNotebookError: raise` so typed errors reach the handlers (`tests/test_typed_exceptions_reach_handlers.py`).
- Requests over `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` (default 100) are rejected by `MaxBodySizeMiddleware` before auth/routing.
- CORS is open by default (`CORS_ORIGINS`); `allow_credentials` flips to `True` only when origins are explicit. No rate limiting built in.

## AI / model provisioning (`open_notebook/ai/`)

- All LLM calls in graph nodes go through `provision_langchain_model()` — never instantiate provider clients directly. It auto-upgrades to `large_context_model` above 105,000 tokens (hard-coded threshold).
- Missing/unconfigured model → raise `ConfigurationError` (not `ValueError`) so the API returns 422.
- Credential-linked models are preferred; `provision_provider_keys()` is the env-var fallback and **mutates `os.environ`** — be aware in tests.
- `DefaultModels.get_instance()` intentionally bypasses the singleton cache (fresh DB fetch each call).

## Graphs (`open_notebook/graphs/`)

- Nodes are `async def` (`ask.py`, `source.py`, `transformation.py`, `prompt.py`). Only the SqliteSaver-checkpointed graphs (`chat.py`, `source_chat.py`) use sync nodes with the `asyncio.new_event_loop()` / ThreadPool workaround, because the checkpointer is sync — fragile; don't copy it into new graphs.
- Every node wraps LLM calls with `classify_error()`:
  ```python
  except Exception as e:
      exc_class, message = classify_error(e)
      raise exc_class(message) from e
  ```
- Strip extended-thinking output with `clean_thinking_content()` before using model responses.
- Chat checkpoints (SqliteSaver) live at `./data/sqlite-db/checkpoints.sqlite` — `LANGGRAPH_CHECKPOINT_FILE` in `open_notebook/config.py` is a constant, not an env var.

## Domain (`open_notebook/domain/`)

- `Source.save()` does **NOT** auto-embed — call `source.vectorize()` explicitly (fire-and-forget, returns a command id). `Note.save()` DOES auto-submit `embed_note`.
- `ObjectModel.get()` is polymorphic via ID prefix — the subclass must be imported first or resolution fails. It raises `NotFoundError` **only** for a missing record and `DatabaseOperationError` for any other DB failure ([ADR-013](../docs/7-DEVELOPMENT/decisions/ADR-013-objectmodel-get-error-contract.md)) — so jobs can treat not-found as permanent and DB errors as retryable.
- `RecordModel` subclasses are singletons — call `clear_instance()` in tests.
- Relationship strings passed to `relate()` must match the schema (`reference`, `artifact`, `refers_to`).

## Database (`open_notebook/database/`)

- New migration = new file `open_notebook/database/migrations/N.surrealql` (+ `N_down.surrealql`) **and** an edit to `AsyncMigrationManager` — migrations are hard-coded, not auto-discovered. They run automatically on API startup.
- No connection pooling — each `repo_*` call opens/closes a connection.
- Transaction-conflict `RuntimeError`s are retriable and logged at DEBUG (don't "fix" the missing stack trace).
- Bind values as `$params`, never f-string user input into SurrealQL ([security.md](../docs/7-DEVELOPMENT/security.md#database-queries-surrealql-injection)); see the [SurrealQL docs](https://surrealdb.com/docs/surrealql) for syntax.

## Background commands (`commands/`)

- Commands are `@command("<name>", app="open_notebook", retry={...})` functions and must be imported from `commands/__init__.py` (the worker loads `--import-modules commands`).
- Retry config uses a blocklist: exceptions in `stop_on` (`ValueError`, `ConfigurationError`, `NotFoundError`, … — check the command's list) fail the job permanently (no retry, job marked `failed`); any other exception auto-retries. Note the embed commands catch `ValueError` internally and return `success=False` (see the comment in `commands/embedding_commands.py`).
- Submission is fire-and-forget via `submit_command()`; commands must be idempotent-ish under retry.
- Podcast generation uses `max_attempts: 1` on purpose (prevents duplicate episodes); retry is the explicit `POST /api/podcasts/episodes/{id}/retry` endpoint.

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
| `CORS_ORIGINS` | Restrict before production |

## Deep dives

[architecture](../docs/7-DEVELOPMENT/architecture.md) · [code standards](../docs/7-DEVELOPMENT/code-standards.md) · [credentials](../docs/7-DEVELOPMENT/credentials.md) · [content processing](../docs/7-DEVELOPMENT/content-processing.md) · [podcasts](../docs/7-DEVELOPMENT/podcasts.md) · [prompts](../docs/7-DEVELOPMENT/prompts.md) · [change playbooks](../docs/7-DEVELOPMENT/change-playbooks.md) · [testing](../docs/7-DEVELOPMENT/testing.md)
