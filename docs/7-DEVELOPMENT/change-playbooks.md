# Change Playbooks

Step-by-step guides for common types of changes in the Open Notebook codebase. Each playbook lists the files to touch **in order**, what to do at each step, and what to test.

> **For AI agents:** Read the relevant playbook BEFORE implementing. Follow the sequence — skipping steps causes incomplete changes that break other layers.

---

## How to Use This Document

1. Identify what type of change your issue requires
2. Follow the playbook step by step
3. If a change spans multiple types (e.g., new field + new endpoint), combine the relevant playbooks
4. When in doubt, read existing examples in the codebase — look at the most recent similar change via `git log`

---

## Playbook: Add a Field to an Existing Model

**Example:** "Add `language` field to Source"

| Step | File(s) | What to Do |
|------|---------|------------|
| 1 | `open_notebook/domain/<model>.py` | Add field with type hint and default value. Follow existing patterns in the class. |
| 2 | `open_notebook/database/migrations/N.surrealql` | Create migration. Use next number in sequence. `DEFINE FIELD` for new fields, `UPDATE` for backfilling existing records. Register it in `AsyncMigrationManager` (`async_migrate.py`) — migrations are not auto-discovered. |
| 3 | `api/models.py` | Add field to `*Create`, `*Update` (Optional), and `*Response` schemas. |
| 4 | `frontend/src/lib/types/api.ts` | Add field to the corresponding TypeScript interface (`*Response`, `Create*Request`, `Update*Request`). |
| 5 | Frontend component (if user-facing) | Display or edit the field in the relevant component. |
| 6 | `frontend/src/lib/locales/*/` | Add i18n strings if the field has a user-visible label. All 7 locales. |
| 7 | Tests | Add/update tests covering the new field — at minimum, API test for create/read. |

**Verify:** Restart API (migration auto-runs), check logs for migration success, test via `/docs`.

---

## Playbook: New API Endpoint

**Example:** "Add endpoint to export notebook as PDF"

| Step | File(s) | What to Do |
|------|---------|------------|
| 1 | `api/models.py` | Define request/response Pydantic schemas. Naming: `<Feature>Request`, `<Feature>Response`. |
| 2 | `api/routers/<resource>.py` | Add endpoint to existing router, OR create new router file if it's a new resource. Follow the pattern: validate → call service → return response. |
| 3 | `api/<resource>_service.py` | Business logic goes here, not in the router. Create new service file if needed. |
| 4 | `api/main.py` | If new router file: register with `app.include_router()`. |
| 5 | `frontend/src/lib/types/api.ts` | Add TypeScript types matching the Pydantic schemas. |
| 6 | `frontend/src/lib/api/<resource>.ts` | Add method to the API module. Follow existing pattern (axios call, return `response.data`). |
| 7 | `frontend/src/lib/hooks/use-<resource>.ts` | Add React Query hook. `useQuery` for GET, `useMutation` for POST/PUT/DELETE. Include cache invalidation and toast. |
| 8 | Frontend component/page | Wire up the hook in the UI. |
| 9 | Tests | API test (status codes, validation, error cases). |

**Naming conventions:**
- Routers: `@router.get("/resources/{id}")` (plural, lowercase, kebab for multi-word)
- Services: functions are `async`, named descriptively (`process_source`, `generate_podcast`)
- Hooks: `useResources()` for list, `useResource(id)` for single, `useCreateResource()` for mutation

---

## Playbook: New LangGraph Workflow

**Example:** "Add a summarization workflow"

| Step | File(s) | What to Do |
|------|---------|------------|
| 1 | `prompts/<workflow_name>/*.jinja` | Create Jinja2 prompt templates. Use `Prompter` from ai-prompter. |
| 2 | `open_notebook/graphs/<workflow_name>.py` | Define `StateDict` (TypedDict), node functions, build graph with `StateGraph`. Use `provision_langchain_model()` for model selection. Wrap LLM calls with `classify_error()`. |
| 3 | `api/<resource>_service.py` | Invoke graph: `await graph.ainvoke(state, config)`. |
| 4 | `api/routers/<resource>.py` | Expose endpoint to trigger the workflow. |
| 5 | `commands/<workflow>_commands.py` | If the workflow should run async: create command with `CommandInput`/`CommandOutput`. Register in command service. |
| 6 | Frontend integration | API module → hook → component. |
| 7 | Tests | Test graph nodes individually with mocked LLM responses. |

**Key patterns:**
- Nodes are sync functions (LangGraph requirement) but can call async code via ThreadPoolExecutor
- Use `classify_error()` to convert raw exceptions to typed `OpenNotebookError` subclasses
- Use `provision_langchain_model()` for model selection — never hardcode a provider
- State is a TypedDict, NOT a Pydantic model

---

## Playbook: Bug Fix (Single Layer)

**Example:** "order_by parameter not working on sources endpoint"

| Step | What to Do |
|------|------------|
| 1 | **Identify the layer.** Read the issue and determine: frontend, API router, service, domain model, database, or graph. |
| 2 | **Read the relevant AGENTS.md** (root, `open_notebook/`, or `frontend/`) and the matching page in `docs/7-DEVELOPMENT/`. They document the rules and gotchas. |
| 3 | **Reproduce.** Use the API docs (`/docs`), browser, or a test to confirm the bug. |
| 4 | **Fix.** Make the minimal change needed. Don't refactor surrounding code. |
| 5 | **Add a test** that reproduces the bug and verifies the fix. |
| 6 | **Run existing tests** to verify no regression: `uv run pytest tests/` |

---

## Playbook: Bug Fix (Cross-Layer)

**Example:** "Creating a source via URL doesn't show in notebook"

| Step | What to Do |
|------|------------|
| 1 | **Trace the data flow.** Start from where the user sees the problem (frontend) and trace backward: component → hook → API call → router → service → domain → database. |
| 2 | **Identify where the chain breaks.** Use API docs to test the backend independently of the frontend. Use SurrealDB queries to check if data was persisted. |
| 3 | **Fix at the right layer.** Don't patch the symptom in the frontend if the bug is in the service. |
| 4 | **Verify the full chain** after fixing. |
| 5 | **Add tests** at the layer where the bug was. |

---

## Playbook: Database Migration

**Example:** "Add index on source.notebook_id for query performance"

| Step | File(s) | What to Do |
|------|---------|------------|
| 1 | `open_notebook/database/migrations/N.surrealql` (+ `N_down.surrealql`) | Write SurrealQL. Use next number in sequence. Check existing migrations for patterns. |
| 2 | `open_notebook/database/async_migrate.py` | Register the new files in `AsyncMigrationManager.__init__` — migrations are hard-coded, not auto-discovered. |
| 3 | Domain model (if schema change) | Update field definitions to match. |
| 4 | API schemas (if new/changed fields) | Update Pydantic models. |
| 5 | **Verify:** Restart API and check logs | Migrations auto-run on startup. Look for errors in Loguru output. |

**Important:**
- Migrations are numbered and run in order
- They're tracked in the `_sbl_migrations` table — won't re-run
- One migration per PR that needs one, numbered in merge order; never consolidate after a migration lands on main (dev images apply it immediately) — see [ADR-006](decisions/ADR-006-migration-granularity.md)
- For destructive changes (DROP FIELD), consider data preservation
- Test with existing data, not just empty database

---

## Playbook: Frontend-Only Change

**Example:** "Improve notebook list loading state"

| Step | File(s) | What to Do |
|------|---------|------------|
| 1 | Identify component | Components are in `frontend/src/app/` (pages) or `frontend/src/components/` (shared). |
| 2 | Make changes | Follow existing patterns: functional components, hooks for state, Tailwind for styling. |
| 3 | i18n strings | If adding user-visible text, add to ALL locale files under `frontend/src/lib/locales/`. |
| 4 | Test in browser | Check responsive layout, dark mode (if applicable), loading states, empty states, error states. |

**Key patterns:**
- `'use client'` directive at top of components using hooks
- State: `useState` for local, Zustand for global, TanStack Query for server
- Styling: Tailwind utility classes, Shadcn/ui components from `components/ui/`
- Types: Define in `lib/types/api.ts`, import everywhere

---

## Playbook: New Background Command

**Example:** "Add command to rebuild all embeddings for a notebook"

| Step | File(s) | What to Do |
|------|---------|------------|
| 1 | `commands/<name>_commands.py` | Define `CommandInput` and `CommandOutput` Pydantic classes. Write the command function. |
| 2 | Register command | Add to the command service so it can be submitted via `CommandService.submit_command_job()`. |
| 3 | API endpoint | Add endpoint that submits the command and returns the command ID. |
| 4 | Frontend (polling) | Use `/commands/{command_id}` endpoint to poll for status. Show progress to user. |

**Pattern:**
- Commands are fire-and-forget: submit returns immediately with a command ID
- Retry config: `max_attempts`, `stop_on` exceptions (ValueError = no retry)
- Exponential backoff with jitter for transient failures

---

## Playbook: i18n / Translation Update

**Example:** "Add translations for new settings page"

| Step | File(s) | What to Do |
|------|---------|------------|
| 1 | `frontend/src/lib/locales/en-US/index.ts` | Add English strings first. Group by feature. |
| 2 | All other locale files | Add the same keys to: `pt-BR`, `zh-CN`, `zh-TW`, `ja-JP`, `ru-RU`, `bn-IN`. Use English as placeholder if translation unavailable. |
| 3 | Component | Use `const { t } = useTranslation()` and access via `t('section.key')`. |

**7 locales total.** Don't forget any.

### Adding a whole new language

| Step | File(s) | What to Do |
|------|---------|------------|
| 1 | `frontend/src/lib/locales/<code>/index.ts` | Copy the structure from `en-US/index.ts` and translate all strings. |
| 2 | `frontend/src/lib/locales/index.ts` | Register the locale: import it, add to `resources`, add to the `languages` array (`{ code, label }`). |
| 3 | `frontend/src/lib/utils/date-locale.ts` | Import the matching `date-fns/locale` and add it to `LOCALE_MAP`. |
| 4 | **Test** | Switch languages via the UI language toggle; missing keys fall back to en-US. |

---

## Quick Reference: File Locations by Layer

| Layer | Location | Schema/Types | Tests |
|-------|----------|-------------|-------|
| Domain models | `open_notebook/domain/` | Pydantic fields | `tests/` |
| Database | `open_notebook/database/repository.py` | SurrealQL | `tests/` |
| Migrations | `open_notebook/database/migrations/*.surrealql` | SurrealQL | Auto-run on startup |
| AI/LLM | `open_notebook/ai/` | Esperanto types | `tests/` |
| Graphs | `open_notebook/graphs/` | TypedDict state | `tests/` |
| Prompts | `prompts/**/*.jinja` | Jinja2 context | — |
| Commands | `commands/` | CommandInput/Output | `tests/` |
| API routers | `api/routers/` | `api/models.py` | `tests/` |
| API services | `api/*_service.py` | — | `tests/` |
| Frontend types | `frontend/src/lib/types/` | TypeScript interfaces | — |
| Frontend API | `frontend/src/lib/api/` | — | — |
| Frontend hooks | `frontend/src/lib/hooks/` | — | `frontend/src/test/` |
| Frontend components | `frontend/src/components/` | Props interfaces | `frontend/src/test/` |
| Frontend pages | `frontend/src/app/` | — | — |
| i18n | `frontend/src/lib/locales/` | — | — |
