# Code Standards

How code in this repo is written. The hard rules for each area are in the AGENTS files ([backend](../../open_notebook/AGENTS.md), [frontend](../../frontend/AGENTS.md)); this page explains the conventions behind them and must not contradict them. Security rules (query parameters, templates, file paths) are in [security.md](security.md) and are mandatory.

## Python

### Tooling

| Tool | Config | Run |
|---|---|---|
| ruff (lint) | `pyproject.toml`: rules `E`, `F`, `I` (import order) | `uv run ruff check .` (`--fix` to apply fixes) |
| ruff (format) | line length 88 | `uv run ruff format .` (CI runs `--check`) |
| mypy | `mypy.ini`, with a burn-down list of modules still exempt | `uv run python -m mypy .` |

CI fails on any of the three. Don't add modules to the mypy exemption list; remove them when you fix one.

### Style

- Type hints on function signatures. Pydantic v2 for data: `BaseModel`, `Field`, `field_validator` (not the v1 `@validator`).
- Log with `loguru` (`from loguru import logger`). Never log secrets or API key values.
- Docstrings explain intent and non-obvious behavior; skip them where the name says it all. When code works around a bug or an issue, reference the issue number.
- Keep changes scoped: don't reformat or refactor code you aren't otherwise changing.

### Async

Everything that touches the database, a model or the network is `async` and awaited:

- Database: `repo_query`, `repo_create`, `repo_update`, `repo_relate`, … in `open_notebook/database/repository.py`, or domain methods (`await Notebook.get(id)`, `await source.save()`).
- Outgoing HTTP: `httpx.AsyncClient`. User-supplied URLs go through `validate_url()` first.
- Models: `provision_langchain_model()` for graph nodes, `model_manager` for embedding and speech models.

Don't call blocking I/O from async code; wrap unavoidable sync calls in `asyncio.to_thread`. The only sanctioned sync-to-async bridge is the one in the checkpointed chat graphs (see [change-playbooks.md](change-playbooks.md#playbook-new-langgraph-workflow)).

### Database access

- Pass values as bind parameters (`$id`), never by f-string interpolation ([security.md](security.md#database-queries-surrealql-injection)). Convert IDs with `ensure_record_id()`.
- Record IDs are `table:id` strings (`source:abc123`). `ObjectModel.get()` picks the subclass from the table prefix.
- Relationships are graph edges, not foreign-key columns: `reference` (source → notebook), `artifact` (note → notebook), `refers_to` (chat session → notebook or source). Query them as `SELECT in AS source FROM reference WHERE out = $id`.
- There is no connection pool. Each `repo_*` call opens and closes a connection (`db_connection()`).

### Errors in the domain and graphs

Raise typed exceptions from `open_notebook/exceptions.py`, never bare `Exception` or `ValueError` for conditions the API or a job should understand:

| Situation | Raise |
|---|---|
| Record doesn't exist | `NotFoundError` |
| Bad user input | `InvalidInputError` |
| Model or provider not configured | `ConfigurationError` |
| Database failure | `DatabaseOperationError` |
| Provider failure | whatever `classify_error()` returns (see below) |

`ObjectModel.get()` raises `NotFoundError` **only** when the record is missing, and `DatabaseOperationError` for any other database failure, such as a transaction conflict ([ADR-013](decisions/ADR-013-objectmodel-get-error-contract.md)). The API maps those to 404 and 500, and background jobs treat `NotFoundError` as permanent and the database error as retryable.

Graph nodes wrap model calls so provider errors become typed, user-readable exceptions:

```python
try:
    ...
except Exception as e:
    exc_class, message = classify_error(e)
    raise exc_class(message) from e
```

### Errors in the API

Global handlers in `api/main.py` map the exception types to status codes (`NotFoundError`→404, `InvalidInputError`→400, `AuthenticationError`→401, `UnsupportedTypeException`→415, `ConfigurationError`→422, `RateLimitError`→429, `NetworkError`/`ExternalServiceError`→502, any other `OpenNotebookError`→500). So in a router:

- **Let typed exceptions propagate.** Don't catch a domain error just to re-raise it as `HTTPException`.
- Raise `HTTPException` only for HTTP-level conditions the router itself checks (a malformed form field, an unsupported query parameter).
- Most routers end with a catch-all that turns unexpected errors into a sanitized 500. It must come **after** the arms that re-raise typed and HTTP errors, or it swallows them:

```python
try:
    ...
except HTTPException:
    raise
except OpenNotebookError:
    raise                      # reaches the global handler with its real status
except Exception as e:
    logger.exception(f"Error updating notebook: {e}")
    raise HTTPException(status_code=500, detail="Error updating notebook")
```

`tests/test_typed_exceptions_reach_handlers.py` and `tests/test_error_message_sanitization.py` enforce both halves. Older routers still have `except NotFoundError: raise HTTPException(404, ...)` arms; they're equivalent, and new code doesn't need them.

### Background commands

A command signals a permanent failure by raising an exception listed in its `retry["stop_on"]`; anything else is retried. See the [command playbook](change-playbooks.md#playbook-new-background-command).

## TypeScript / frontend

- `npm run lint` (ESLint over `src/`) and `npm run build` (which type-checks) must pass; CI runs both plus `npm run test`.
- The rules that matter most, all in [frontend/AGENTS.md](../../frontend/AGENTS.md): every UI string through `t()` in every locale; colors through design tokens, never raw Tailwind palette classes; every request through `apiClient`; server state through TanStack Query hooks in `src/lib/hooks/`.
- Show errors with `getApiErrorMessage()` and a toast; the backend's messages are already user-facing.

## Review checklist

- [ ] CI checks pass locally ([contributing.md](contributing.md#before-you-open-a-pr))
- [ ] Tests cover the change, including the failure path
- [ ] Typed exceptions, not `HTTPException`, for domain errors
- [ ] No f-string interpolation of user input into SurrealQL; user URLs go through `validate_url()`
- [ ] No API key values in responses or logs
- [ ] New UI strings in every locale; no raw palette classes
- [ ] Migration registered in `AsyncMigrationManager`, with a down file
- [ ] CHANGELOG entry under `[Unreleased]`; docs updated
