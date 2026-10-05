# Testing

How the test suites are laid out, how to run them, and the patterns to copy when you add a test.

## Running the tests

```bash
# Backend (repo root)
uv run pytest tests/                                   # what CI runs (plus coverage flags)
uv run pytest tests/test_sources_api.py                # one file
uv run pytest tests/test_sources_api.py -k retry       # tests matching a name
uv run pytest tests/ --cov=open_notebook --cov=api     # with coverage

# Frontend (inside frontend/)
npm run test              # vitest run, once
npm run test:watch        # watch mode
npm run test:coverage     # what CI runs
```

The backend suite needs **no running SurrealDB, worker or AI provider**. CI runs it with nothing but `uv sync`. SurrealDB access, models and HTTP requests are mocked; a few tests use in-memory substitutes instead (for example an in-memory `SqliteSaver` in `tests/test_empty_model_reply.py`).

## Backend layout (`tests/`)

`tests/` is flat: one `test_<topic>.py` per feature or regression (about 70 files), for example `test_sources_api.py`, `test_credentials_api.py`, `test_ask_graph.py`, `test_crud_404.py`. There are no `unit/` or `integration/` subfolders. Name a new file after what it covers, or add to the existing file for that area.

`tests/conftest.py` has no shared fixtures. It only:

- sets `OPEN_NOTEBOOK_PASSWORD=""` before anything is imported, so the auth middleware is disabled in tests;
- loads the repo's `.env` if it exists;
- puts the repo root on `sys.path`.

pytest-asyncio runs in its default (strict) mode, so async tests need `@pytest.mark.asyncio`.

## Backend patterns

**API tests** use FastAPI's `TestClient` with a per-file fixture, and patch the domain call the router makes:

```python
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.exceptions import NotFoundError


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


@patch("api.routers.notebooks.Notebook.get", new_callable=AsyncMock)
def test_delete_notebook_missing_returns_404(mock_get, client):
    mock_get.side_effect = NotFoundError("not found")
    assert client.delete("/api/notebooks/notebook:gone").status_code == 404
```

(Adapted from `tests/test_crud_404.py`.) Paths include the `/api` prefix. To assert on a 500 instead of having the exception raised into the test, create the client with `TestClient(app, raise_server_exceptions=False)` (see `tests/test_typed_exceptions_reach_handlers.py`).

**Patch where the name is used**, not where it's defined: `api.routers.notebooks.Notebook.get`, `open_notebook.graphs.ask.provision_langchain_model`, and so on. Async functions need `new_callable=AsyncMock` (or an `AsyncMock` as the replacement).

**Graph tests** patch `provision_langchain_model` in the graph module and return a fake model, then call the node function or `await graph.ainvoke(...)` (see `tests/test_ask_graph.py`, `tests/test_graphs.py`).

**Command tests** call the command function directly with its `CommandInput` and patched dependencies (see `tests/test_source_deleted_before_processing.py`, `tests/test_embed_source_partial_cleanup.py`).

**Things that leak between tests:**

- `RecordModel` subclasses (`DefaultModels`, `ContentSettings`, …) are singletons. Call `clear_instance()` in setup/teardown when a test touches one (see `tests/test_domain.py`).
- `provision_provider_keys()` writes to `os.environ`. Use pytest's `monkeypatch.setenv` / `delenv` so environment changes are undone.

**Migrations** can be tested as text, without a database, by reading the `.surrealql` file (see `tests/test_insight_timestamps.py`).

## Frontend layout

Tests are colocated with the code as `*.test.ts` / `*.test.tsx` (for example `src/lib/locales/index.test.ts`, `src/components/common/ConfirmDialog.test.tsx`). `frontend/src/test/` holds only the shared setup (`setup.ts`: jest-dom matchers and mocks for `next/navigation`, `matchMedia` and `@/lib/hooks/use-translation`, whose `t()` returns the key itself, so assert on keys rather than English text).

Vitest runs in `jsdom` with globals enabled and the `@/` alias (`frontend/vitest.config.ts`). Use Testing Library to render components; mock API modules rather than the network.

## What to test

- A bug fix comes with a test that fails without the fix. Name it after the behavior (`test_delete_notebook_missing_returns_404`) and reference the issue in the docstring.
- API changes: status codes, validation errors and the error mapping, not only the happy path.
- Don't test third-party libraries (Esperanto, content-core, LangGraph) or make real provider calls.
