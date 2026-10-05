# Change Playbooks

Step-by-step guides for common changes. Each playbook lists the files to touch in order and what to test. The rules behind them are in the AGENTS files ([root](../../AGENTS.md), [backend](../../open_notebook/AGENTS.md), [frontend](../../frontend/AGENTS.md)).

> **For AI agents:** read the matching playbook before implementing. If a change spans several types (a new field and a new endpoint), combine them. When in doubt, find the most recent similar change with `git log` and copy its shape.

Every playbook ends the same way: tests, a CHANGELOG entry under `[Unreleased]`, and the checks CI runs (see [contributing.md](contributing.md#before-you-open-a-pr)).

---

## Playbook: Add a Field to an Existing Model

**Example:** "Add `language` to episode profiles"

| Step | File(s) | What to do |
|------|---------|------------|
| 1 | `open_notebook/domain/<model>.py` (or `open_notebook/podcasts/models.py`, `open_notebook/ai/models.py`) | Add the field with a type hint and default. |
| 2 | `open_notebook/database/migrations/N.surrealql` + `N_down.surrealql` | Only for `SCHEMAFULL` tables: `DEFINE FIELD`, plus an `UPDATE` to backfill if needed. Follow the [Database Migration](#playbook-database-migration) playbook. |
| 3 | `api/models.py` | Add the field to the request (`*Create`, `*Update` as `Optional`) and `*Response` schemas. |
| 4 | `api/routers/<resource>.py` | Pass the field through where the router builds the domain object or the response. |
| 5 | `frontend/src/lib/types/*.ts` | Add it to the matching TypeScript interface (`api.ts`, `podcasts.ts`, `models.ts`, …). |
| 6 | Frontend component | Display or edit it. Every new label goes through `t()` and into **every** locale (see [i18n](#playbook-i18n--translation-update)). |
| 7 | `tests/` | At least an API test for create and read. |

---

## Playbook: New API Endpoint

**Example:** "Add an endpoint to export a notebook"

| Step | File(s) | What to do |
|------|---------|------------|
| 1 | `api/models.py` | Request/response Pydantic schemas (`<Feature>Request`, `<Feature>Response`). |
| 2 | `api/routers/<resource>.py` | Add the endpoint to the existing router, or create a router for a new resource. Most routers call domain models (`open_notebook/domain/`) and `repo_*` functions directly. Put logic in an `api/*_service.py` module only when several routers share it or it orchestrates jobs (as `command_service.py`, `credentials_service.py` and `podcast_service.py` do). |
| 3 | `api/main.py` | New router only: `app.include_router(<module>.router, prefix="/api", tags=[...])`. |
| 4 | `frontend/src/lib/types/` and `frontend/src/lib/api/<resource>.ts` | Types and a method on the API module (calls `apiClient`, returns `response.data`). |
| 5 | `frontend/src/lib/hooks/use-<resource>.ts` | TanStack Query hook: `useQuery` for reads, `useMutation` with cache invalidation and a toast for writes. |
| 6 | Frontend component/page | Wire up the hook. |
| 7 | `tests/` | Status codes, validation and error cases with `TestClient` (see [testing.md](testing.md)). |

**Errors:** raise typed exceptions from `open_notebook.exceptions` and let the global handlers in `api/main.py` map them to status codes. A router's catch-all `except Exception` must come after `except OpenNotebookError: raise` (and `except HTTPException: raise`) so typed errors still reach those handlers. See [code-standards.md](code-standards.md#errors-in-the-api).

**Naming:** paths are plural and lowercase, kebab-case for several words (`/episode-profiles`, `/sources/{source_id}/status`). Hooks are `useResources()`, `useResource(id)`, `useCreateResource()`.

---

## Playbook: Add an AI Provider

**Example:** SiliconFlow and Z.ai (PR #1443), MiniMax text-to-speech (PR #1444)

Open Notebook never calls provider SDKs directly; every model is created through [Esperanto](https://github.com/lfnovo/esperanto). So step 0 is: **Esperanto must already support the provider**, under the same provider name. If support arrived in a newer Esperanto release, bump `esperanto` in `pyproject.toml` and run `uv lock`.

The provider registry is the source of truth. Most backend tables and the frontend read from it, but a few copies are still maintained by hand. This is the full list for a provider with a single API key (the common case):

| Step | File | What to do |
|------|------|------------|
| 1 | `open_notebook/ai/provider_registry.py` | Add a `ProviderSpec` to `_PROVIDER_SPECS`. Its position is the display order in the UI. Set `name` (Esperanto's provider name), `display_name`, `modalities`, `required_env=("X_API_KEY",)`, `test_model` (the cheapest model, used by the connection test), `docs_url` (where users get a key), and `openai_compat_discovery_url` if the provider has an OpenAI-style `GET /models`. If the provider has regional endpoints, also declare `optional_env=("X_BASE_URL",)` ([ADR-012](decisions/ADR-012-provider-endpoint-overrides.md)): env migration and model discovery then honor the override. |
| 2 | `api/models.py` | Add the name to the `SupportedProvider` Literal. (Python typing can't build it from the registry at runtime.) |
| 3 | `open_notebook/ai/key_provider.py` | Add `"<name>": {"env_var": "X_API_KEY"}` to `PROVIDER_CONFIG`. Without it, models that fall back to environment keys (no linked credential) can't be provisioned. |
| 4 | `api/routers/models.py` | Add `"<name>": "X_API_KEY"` to `env_var_map` in `get_provider_availability()`. Without it, `GET /api/models/providers` reports an env-only setup as unavailable. |
| 5 | `open_notebook/ai/model_discovery.py` | For an OpenAI-compatible listing: `discover_<name>_models = _make_openai_compat_discoverer("<name>")` and an entry in `PROVIDER_DISCOVERY_FUNCTIONS`. A provider with no env-based discovery maps to `None` (as `azure` and `vertex` do). If the `/models` listing mixes in embedding or audio models, add a `<NAME>_MODEL_TYPES` table and register it in `classify_model_type()` (SiliconFlow). If the listing leaves out audio models, seed them in `PROVIDER_AUDIO_SEEDS` (MiniMax TTS). |
| 6 | `api/routers/models.py` (optional) | Add the provider to `PROVIDER_PRIORITY` and `MODEL_PREFERENCES` if **Auto-assign Defaults** should pick its models. |
| 7 | `tests/test_credential_provider_validation.py`, `tests/test_model_discovery.py` | Add the name to `KNOWN_GOOD_PROVIDERS`, to the expected discovery-URL dict and to the expected `PROVIDER_DISCOVERY_FUNCTIONS` set. These tests fail until steps 1, 2 and 5 agree. For a `*_BASE_URL` override, add migration and discovery cases to `tests/test_credentials_api.py`. |
| 8 | Docs | A section in `docs/5-CONFIGURATION/ai-providers.md`, the env vars in `docs/5-CONFIGURATION/environment-reference.md`, the provider tables in `docs/4-AI-PROVIDERS/index.md`, the provider list in `README.md`, and an `### Added` CHANGELOG entry. |

You don't need to touch:

- `connection_tester.TEST_MODELS`, `credentials_service.PROVIDER_ENV_CONFIG` / `PROVIDER_MODALITIES` and `model_discovery.OPENAI_COMPAT_PROVIDERS`. They are derived from the registry.
- The frontend. It loads providers from `GET /api/providers` at runtime (`useProviders()`), and the credential form shows the API key and Base URL fields for any simple provider.

Providers that need several config fields (like `azure`, `vertex`, `openai_compatible`) also need a `_provision_<name>()` function in `key_provider.py`, a bespoke check in `get_provider_availability()`, credential-based discovery in `api/credentials_service.py`, and form fields in `frontend/src/components/settings/CredentialFormDialog.tsx`. Read how the closest existing provider does it before starting.

**Verify:** `uv run pytest tests/test_credential_provider_validation.py tests/test_model_discovery.py tests/test_credentials_api.py`. Then, in the app: **Manage → Models**, add a configuration for the provider, run **Test Connection**, then **Sync Models**.

---

## Playbook: New LangGraph Workflow

**Example:** "Add a summarization workflow"

| Step | File(s) | What to do |
|------|---------|------------|
| 1 | `prompts/<workflow>/*.jinja` | Prompt templates, rendered with `Prompter` (see [prompts.md](prompts.md)). |
| 2 | `open_notebook/graphs/<workflow>.py` | A `TypedDict` state, node functions and a `StateGraph`. Get models with `provision_langchain_model()`, wrap LLM calls with `classify_error()`, and strip thinking output with `clean_thinking_content()`. |
| 3 | Caller | Short, interactive work: call `await graph.ainvoke(state, config=...)` from a router (as `search.py` does for Ask). Long-running work: invoke it from a background command (as `process_source` does for the source graph). |
| 4 | Frontend | API module → hook → component. |
| 5 | `tests/` | Test nodes with a mocked model (`patch` `provision_langchain_model`). |

**Nodes are `async def`** (`ask.py`, `source.py`, `transformation.py`, `prompt.py`). Only the two checkpointed chat graphs (`chat.py`, `source_chat.py`) use sync nodes with an `asyncio.new_event_loop()` workaround, because their `SqliteSaver` checkpointer is synchronous. Don't copy that pattern into a graph without a checkpointer.

---

## Playbook: New Background Command

**Example:** "Rebuild all embeddings"

| Step | File(s) | What to do |
|------|---------|------------|
| 1 | `commands/<area>_commands.py` | Define `CommandInput` / `CommandOutput` subclasses and an `async` function decorated with `@command("<name>", app="open_notebook", retry={...})`. |
| 2 | `commands/__init__.py` | Import the command. The worker starts with `--import-modules commands`, so a command that isn't imported there is never registered. |
| 3 | API | Submit it: `await CommandService.submit_command_job("open_notebook", "<name>", input.model_dump())`. This returns a job id immediately. |
| 4 | Frontend | Poll `GET /api/commands/jobs/{job_id}` for status. Sources also have `GET /api/sources/{source_id}/status`. |
| 5 | `tests/` | Call the command function directly with mocked dependencies. |

**Retry:** `retry` takes `max_attempts`, `wait_strategy` (`exponential_jitter`), `wait_min`, `wait_max` and `stop_on`, a list of exception types that fail the job immediately. Retries happen for any exception not in `stop_on`. Existing commands put `ValueError`, `ConfigurationError`, `NotFoundError` and similar permanent errors in `stop_on`. Make the command safe to run twice. Restart the worker after changing a command.

---

## Playbook: Database Migration

| Step | File(s) | What to do |
|------|---------|------------|
| 1 | `open_notebook/database/migrations/N.surrealql` + `N_down.surrealql` | SurrealQL for the change and its rollback. `N` is the next number. Copy patterns from recent migrations. |
| 2 | `open_notebook/database/async_migrate.py` | Add both files to the lists in `AsyncMigrationManager.__init__`. Migrations are listed by hand, not discovered. |
| 3 | Domain model and `api/models.py` | Match the new fields. |
| 4 | Verify | Restart the API. Migrations run on startup; the log shows `Running migration N` and `Migrations completed successfully. Database is now at version N`. |

- Applied versions are recorded in the `_sbl_migrations` table and never re-run.
- One migration per PR that needs one, numbered in merge order. Never consolidate migrations after one lands on `main`: dev images apply it immediately ([ADR-006](decisions/ADR-006-migration-granularity.md)).
- Test against a database with existing data, not only an empty one.

---

## Playbook: Bug Fix

| Step | What to do |
|------|------------|
| 1 | **Find the layer.** Trace from where the user sees the problem: component → hook → API module → router → domain/graph/command → database. Use `/docs` (Swagger) to call the backend without the frontend. |
| 2 | **Read the rules** for that layer: the matching AGENTS file and page in `docs/7-DEVELOPMENT/`. |
| 3 | **Reproduce it with a test** that fails. |
| 4 | **Fix it at the layer where it breaks**, with the smallest change. Don't patch a backend bug in the frontend, and don't refactor surrounding code. |
| 5 | **Run the whole suite**: `uv run pytest tests/` (and the frontend checks if you touched it). |

---

## Playbook: Frontend-Only Change

| Step | What to do |
|------|------------|
| 1 | Pages are in `frontend/src/app/`, feature components in `frontend/src/components/<feature>/`, primitives in `frontend/src/components/ui/`. |
| 2 | Follow existing patterns: TanStack Query for server state, Zustand stores (`src/lib/stores/`) for client state, design tokens for styling ([ADR-011](decisions/ADR-011-design-token-system.md); no raw Tailwind palette classes). |
| 3 | New user-visible text goes into every locale (next playbook). |
| 4 | Check loading, empty and error states, both themes, and a narrow viewport. Add a colocated `*.test.tsx` for logic worth testing. |

---

## Playbook: i18n / Translation Update

| Step | File(s) | What to do |
|------|---------|------------|
| 1 | `frontend/src/lib/locales/en-US/index.ts` | Add the English strings. en-US is the reference shape. |
| 2 | Every other directory under `frontend/src/lib/locales/` | Add the same keys. Use the English text as a placeholder if you can't translate it. |
| 3 | Component | `const { t } = useTranslation()`, then `t('section.key')`. |

You can't forget a locale silently: each non-en-US locale ends with `satisfies TranslationShape`, so a missing or extra key fails `npm run build` (type check), and `src/lib/locales/index.test.ts` checks parity at runtime.

### Adding a new language

| Step | File(s) | What to do |
|------|---------|------------|
| 1 | `frontend/src/lib/locales/<code>/index.ts` | Copy `en-US/index.ts`, translate it, export it, and end the object with `} satisfies TranslationShape;`. |
| 2 | `frontend/src/lib/locales/index.ts` | Import it, add it to `resources` and to the `languages` array. |
| 3 | `frontend/src/lib/utils/date-locale.ts` | Import the matching `date-fns/locale` and add it to `LOCALE_MAP`. |
| 4 | `frontend/src/components/common/LanguageToggle.tsx` | Add a menu item. The toggle has one hard-coded entry per language and doesn't read the `languages` array. |
| 5 | Test | Switch to the language in the toggle; dates and labels should change. |

---

## Quick Reference: Where Things Live

| Layer | Location | Tests |
|-------|----------|-------|
| Domain models | `open_notebook/domain/`, `open_notebook/ai/models.py`, `open_notebook/podcasts/models.py` | `tests/` |
| Database access | `open_notebook/database/repository.py` (`repo_query`, `repo_create`, …) | `tests/` |
| Migrations | `open_notebook/database/migrations/` + `async_migrate.py` | run on API startup |
| AI provisioning and providers | `open_notebook/ai/` | `tests/` |
| Graphs | `open_notebook/graphs/` | `tests/` |
| Prompts | `prompts/**/*.jinja` | `tests/` (podcast templates) |
| Background commands | `commands/` | `tests/` |
| API routers and schemas | `api/routers/`, `api/models.py` | `tests/` |
| Frontend types / API / hooks | `frontend/src/lib/types/`, `lib/api/`, `lib/hooks/` | colocated `*.test.ts` |
| Frontend components / pages | `frontend/src/components/`, `frontend/src/app/` | colocated `*.test.tsx` |
| i18n | `frontend/src/lib/locales/` | `locales/index.test.ts` |
