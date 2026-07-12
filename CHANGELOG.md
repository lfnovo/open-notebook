# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Podcast episode audio paths are now stored relative to the podcasts folder (`episodes/<uuid>/audio/<name>.mp3`) instead of as absolute filesystem paths, validated at write time so the database can never hold an absolute or root-escaping value, and resolved + containment-checked through a single shared helper instead of per-endpoint guards. Migration 21 converts existing rows written under the known roots (plain `file:///` URIs, `/app/data/podcasts/`, `/data/podcasts/`, `./data/podcasts/`, `data/podcasts/`); previously generated episodes now survive a `DATA_FOLDER` relocation. Rows under any other root (e.g. a source checkout at a custom absolute path) or in exotic legacy forms (percent-encoded or host-qualified `file://` URIs) are left untouched and treated as legacy-invalid — the same 403/audio-unavailable handling out-of-root rows already had; regenerate the episode to restore playback. Podcast jobs whose audio combination fails (podcast-creator reports an in-band `ERROR:` value) now fail with the real ffmpeg/clip error instead of reporting success for an episode with no playable audio (#1030)
- The source detail view (dialog and full page) now fetches through the shared `useSource` React Query hook instead of a hand-rolled fetch, matching the insight/note dialogs: caching and the never-retry-404 policy come from React Query, title edits and deletes go through the shared mutation hooks (so source lists refresh and a deleted source can't be served from the cache), and the `key={sourceId}` remount workaround on the parents was removed — the component resets its own per-source UI state (#1106)
- The settings frontend now fetches the provider list from `GET /api/providers` (cached for the session) instead of keeping its own hardcoded provider tables, so adding a provider to the backend registry needs zero frontend edits: unknown modalities render with a fallback icon, the backend registry owns the display order, and the regex-based frontend/backend sync test was removed along with the duplicated tables in `frontend/src/lib/providers.tsx` (#1082)

### Removed
- The legacy provider/model string fields on podcast profiles (`outline_provider`, `outline_model`, `transcript_provider`, `transcript_model` on episode profiles; `tts_provider`, `tts_model` on speaker profiles) are gone from the database, the API and the UI — the app has ignored them since the Model registry references landed in v1.11. Migration 22 first best-effort maps any profile whose `outline_llm`/`transcript_llm`/`voice_model` reference is still empty to an existing model record (matching provider + name + type; no auto-creation, since a migration must not touch credentials), then drops the six columns; the startup data migration that used to retry this mapping on every boot (`open_notebook/podcasts/migration.py`) was deleted. Accepted trade-off: profiles whose mapping never converged (e.g. the provider credential was never configured) lose the legacy strings and stay unresolved — they were already non-functional and the UI already flags them as needing model selection, so you just re-pick the models in the profile form once (#1107)

### Fixed
- Renaming a speaker profile no longer breaks the episode profiles that use it: `episode_profile.speaker_config` now stores a `record<speaker_profile>` reference instead of the profile name (migration 20 converts existing rows; references whose speaker profile no longer exists at migration time become null, and any reference that later stops resolving is treated as "needs setup" — the UI asks you to pick a speaker again). The `POST /api/podcasts/generate` contract is unchanged — it still accepts the speaker profile by name and resolves it at the API boundary (#630)
- Clicking a chat/Ask citation that points at a deleted source, insight, or note now shows a shared, friendly "this content no longer exists" state in all three dialogs (instead of a raw error, a blank dialog, or an empty editable note editor), 404 lookups are no longer retried, and non-404 failures show a distinct "unable to load" message (#455)
- Source insights now get `created`/`updated` timestamps stamped at creation (migration 19 mirrors the defaults used by the other tables), and the insights API returns `null` — instead of the literal string `"None"` — for legacy insights that predate the migration (#1045)
- `uv sync` alone now provides the full dev toolchain: the legacy `[project.optional-dependencies].dev` list was merged into `[dependency-groups].dev` (mypy included — the documented `uv run python -m mypy .` previously failed on a fresh clone), Jupyter-only packages moved to a separate `notebooks` group, and the CI typecheck job no longer needs `--extra dev` (#1101)
- Optional model defaults (transformation, tools, large context, TTS, STT) can now be cleared: `PUT /api/models/defaults` honors explicit `null` (field absent still means "keep"; chat and embedding defaults reject `null`), and the default-model selects offer a "None" / "Use fallback (chat default)" option for the optional defaults (#1091)
- `docker-compose.yml` now uses the YAML list (exec) form for the SurrealDB `command`, so `SURREAL_USER` / `SURREAL_PASSWORD` values containing spaces are passed as single arguments instead of being split; the mirrored snippets in the installation docs and README (which had drifted — no credential interpolation, SurrealDB port published on all interfaces) are back in sync with the shipped file (#1093)
- zh-CN and zh-TW podcast toast descriptions (speaker/episode profile created/updated/deleted/duplicated) now include the profile name via the `{{name}}` placeholder, matching the other 12 locales (#1084)
- Docker images now force the Next.js frontend to bind to `0.0.0.0` in the supervisord command itself, so container runtimes that inject `HOSTNAME` (e.g. Podman pods, where it resolves to `127.0.1.1`) can no longer make the UI unreachable. The `HOSTNAME` variable is no longer honored as a frontend bind override — set the new `FRONTEND_BIND_HOST` variable instead (#994)

## [1.12.0] - 2026-07-12

### Fixed
- Setup snippets no longer teach publishing SurrealDB on `0.0.0.0` — the compose and `docker run` examples across the README, quick starts, installation, configuration and development docs, and the `examples/docker-compose-*.yml` files now bind port 8000 to `127.0.0.1` (matching the shipped `docker-compose.yml`), with docs pointing to `docker-compose.override.yml.example` for opt-in remote access behind a firewall or SSH tunnel; the override example itself gained the `!override` tag it needs to actually replace the base port binding instead of colliding with it (#1034)

### Added
- Docs: cubic platform mechanics recorded as comments in `cubic.yaml` (agent limits, config precedence, memory/learning) and a "Merging PR Batches" playbook added to the maintainer guide (squash policy, CHANGELOG conflict resolution, fork rebases, competing-PR checks) (#1086)
- New `GET /api/providers` endpoint returning provider metadata from the registry (name, display name, modalities, docs URL, whether it is configured via environment variables), so clients can enumerate supported providers instead of hardcoding them (#1075)
- Release confidence process, documented and executable: `.github/RELEASE_PROCESS.md` now covers the risk-based test matrix (buckets A/B/C), the Docker image gate, the fix-loop re-test policy and the communication/credits/retro structure, backed by a new decision record (ADR-005) and versioned tooling under `scripts/release-test/` — `make release-test TAG= OLD_TAG=` runs fresh-install + upgrade scenarios against real images, and `make release-stack TAG= [DUMP=]` boots a browsable, isolated release-candidate stack (optionally with a copy of dev data) for manual verification (#1052)
- CI now gates every PR on `ruff check` (backend lint), `npm run lint` (frontend ESLint) and `npm run build` (frontend production build), in addition to the existing test suites (#1068)
- CI now also gates every PR on `mypy` (backend typecheck): the repo-wide baseline went from 197 errors to 0 (enabling the pydantic mypy plugin resolved most of them; the rest got real annotations), so new type errors are blocked from here on. The `ignore_errors` burn-down also started: `open_notebook.graphs.transformation`, `open_notebook.graphs.ask` and `api.routers.models` are now type-checked (plus two stale entries for deleted modules removed); only `open_notebook.domain.notebook` remains exempt pending the surreal-basics migration (#1076)

### Changed
- cubic AI review now skips `CHANGELOG.md`, `uv.lock` and `frontend/package-lock.json` (no reviewable logic; preserves the monthly reviewed-line quota) (#1080)
- Context building consolidated into a single implementation (`open_notebook/utils/context_builder.py`): the copy-pasted source/note assembly loops behind `POST /api/chat/context` and the removed notebook-context endpoint, plus the 495-line generalized `ContextBuilder` class (whose only caller was the source-chat graph), are now two focused functions — `build_notebook_context()` (backs `POST /api/chat/context`, unchanged request/response shapes and config semantics) and `build_source_context()` (backs the source-chat graph, same context shape and 50k-token budget). Pinned by new characterization tests — no behavior change for the surviving paths (#1079)
- **Removed** `POST /api/notebooks/{notebook_id}/context`: it duplicated `POST /api/chat/context` (same assembly logic, slightly different response envelope) and had zero callers — frontend, docs and tests only use `/api/chat/context`. If you called it programmatically, switch to `POST /api/chat/context` (body: `{notebook_id, context_config}`; response fields: `context.sources`/`context.notes`, `token_count`, `char_count`) (#1079)
- Backend provider metadata now lives in a single registry (`open_notebook/ai/provider_registry.py`): env var config, modalities, connection-test models, OpenAI-compatible discovery URLs and docs links are defined once per provider, and `PROVIDER_ENV_CONFIG`, `PROVIDER_MODALITIES`, `TEST_MODELS` and `OPENAI_COMPAT_PROVIDERS` are derived from it. Adding a provider drops from ~6 hand-synced dicts to the registry plus two manual copies (the `SupportedProvider` Literal and the frontend provider table), both enforced by tests (#1075)
- Frontend convention cleanup (no user-facing change): hook files unified to kebab-case (`useNotebookChat.ts`/`useSourceChat.ts` → `use-notebook-chat.ts`/`use-source-chat.ts`), `src/components/source/` merged into `src/components/sources/`, the localStorage auth-token parsing ritual extracted into a single `getAuthToken()` helper (`src/lib/auth-token.ts`), and non-streaming raw `fetch` calls routed through `apiClient` (podcast audio download, auth-status check). SSE/streaming paths and the login/checkAuth credential probes deliberately keep raw `fetch` (#1077)
- Pruned unused langchain packages: removed `langchain-community` and `langchain-deepseek` from the dependencies (nothing imports them — DeepSeek and xAI route through esperanto's OpenAI-compatible path, which uses `langchain-openai`). The remaining `langchain-*` provider packages are documented as runtime requirements of esperanto's dynamic `to_langchain()` and the whole langchain/langgraph family now carries explicit upper bounds; `langchain-core` and `langchain-text-splitters` (both directly imported but previously only transitive) are now declared explicitly (#1073)
- The two Docker images (regular and single-container) are now built from a single multi-stage `Dockerfile` with shared stages — regular is the default (`runtime`) target, single-container is `--target single` — so deploy fixes (tiktoken pre-cache, env defaults, npm retry logic) no longer have to be applied twice. `Dockerfile.single` and `supervisord.single.conf` were removed; the single image appends a small `supervisord.surrealdb.conf` to the shared `supervisord.conf` at build time. Published image names and tags are unchanged (#1066)
- Model discovery is now table-driven: the eight providers with OpenAI-compatible `/models` endpoints (OpenAI, Groq, Mistral, DeepSeek, xAI, OpenRouter, DashScope, MiniMax) share one generic discovery function configured by `OPENAI_COMPAT_PROVIDERS`, replacing eight near-identical copies (provider-specific quirks like Mistral's capability flags and OpenRouter's descriptions are preserved as hooks) (#1070)
- Internal refactor: extracted the session/source verification, record-ID normalization, LangGraph message extraction and shared response models duplicated across the chat and source-chat routers into `api/routers/_chat_shared.py`, pinned by new characterization tests — no behavior change (#1072)
- Internal refactor of the sources API router: extracted a shared `SourceResponse` builder (was hand-rolled 5×), a single upload-cleanup helper (was pasted 6×), split the 293-line create-source endpoint into validation + sync/async path functions, and unified the duplicated paginated list query. No behavior change; all security checks (atomic filename claim, path-traversal containment, SSRF/LFI guards) preserved verbatim (#1069)
- Re-enabled the ruff rules for unused imports (`F401`), unused local variables (`F841`) and bare `except:` (`E722`) that were ignored to silence legacy Streamlit-era noise, and cleaned up the remaining fallout (10 unused imports, 2 unused test variables; no bare excepts remained) (#1062)
- Internal refactor with no user-facing change: split the 1,441-line API Keys settings page into focused components under `frontend/src/components/settings/` and moved the provider config tables to `frontend/src/lib/providers.tsx`, deduplicating the default-model select in the process (#1065)
- Chat, source chat, Ask and transformation prompts now steer models to write math as `$$...$$` (display) / `$...$` (inline) so formulas render via KaTeX, reserving fenced `latex` code blocks for when the user explicitly asks for the LaTeX source (#1051)
- Frontend locale files are now type-checked at compile time: every non-en-US locale declares `satisfies TranslationShape` (derived from the en-US object), so a missing or extra i18n key fails `tsc` in the editor instead of only the runtime parity test. Also removed two unused frontend dependencies (`next-themes`, `@monaco-editor/react`) and fixed `frontend/AGENTS.md` drift (14 locales, not 7; dark mode is the hand-rolled zustand theme-store, not next-themes) (#1061)

### Fixed
- Eight podcast toast descriptions (speaker/episode profile created/updated/deleted/duplicated) showed the literal `{name}` placeholder instead of the profile name: the locale strings used single braces (which i18next ignores) and the `t()` call sites passed no values. Placeholders normalized to `{{name}}` across all locales and the actual name is now passed in from the mutation response/variables (#1077)
- Typed domain errors now return their documented HTTP status codes instead of a generic 500: the API routers used to wrap endpoint bodies in a broad `except Exception` that swallowed the `open_notebook.exceptions` hierarchy before the global handlers could map it (`NotFoundError`→404, `InvalidInputError`→400, `ConfigurationError`→422, `RateLimitError`→429, `NetworkError`/`ExternalServiceError`→502). All 18 affected routers now re-raise `HTTPException` and `OpenNotebookError` and only convert genuinely unexpected exceptions into sanitized 500s. Most visible changes: a missing/unconfigured model (`ConfigurationError`) now returns 422 with an actionable message instead of 500; getting or deleting a source-chat session whose session isn't related to the source returns 404 (was a 500 wrapping the inner 404); fetching a missing credential returns 404 (was 500) (#1078)
- Frontend translations now use i18next interpolation (`t('key', { count })`) instead of manual `.replace('{count}', ...)` string surgery across ~75 call sites — locale placeholders changed from `{name}` to `{{name}}` in all 14 locales. This restores proper pluralization (e.g. "used by N episodes" now goes through i18next plural forms) and lets translators reorder placeholders freely (#1074)
- Podcast generation dialog: the token/char counter no longer fires a request storm on rapid checkbox toggling (debounced, with a stale-response guard so a slow response can't overwrite a fresher count) and the dialog now closes as soon as the episode-list refetch completes instead of after a fixed 500ms timer; the 983-line component was also split (content selection panel and selection helpers extracted, duplicated context-config logic deduplicated) with no behavior changes (#1067)
- Anthropic models are now discovered live from `GET https://api.anthropic.com/v1/models` (paginated) instead of a hardcoded claude-3-era list — the code comment claiming "Anthropic doesn't have a model listing API" was wrong. A refreshed static list (current Claude 4.x/5 aliases) remains as a fallback when the API call fails, and the credential-based discovery path (`discover_with_config`) uses the same live-with-fallback logic (#1070)
- Deduplicated the embedding commands (`commands/embedding_commands.py`, ~100 lines less): `embed_note`/`embed_insight`/`embed_source` now share one load→embed→write core with a single error-handling epilogue, the rebuild command uses one submission-loop helper for all three kinds, and the thrice-copied `full_model_dump()` moved to `open_notebook/utils/model_utils.py`. Pure refactor — same outputs, logs and retry behavior (#1071)

### Removed
- Dead Streamlit-era service layer (~2,000 lines): `api/client.py` (a synchronous HTTP client that called the app's own API) and 13 `api/*_service.py` wrappers that consumed the app's own HTTP API — none were imported by any router, command or test. Also removed the toy `process_text`/`analyze_data` demo commands (`commands/example_commands.py`) from the background worker (#1054)
- Pre-1.6 embedding job compatibility shims (the `embed_single_item`, `embed_chunk` and `vectorize_source` command handlers) — they existed only so jobs queued by a pre-1.6 version could drain after an upgrade, and any worker restarted on 1.6+ has no such jobs. **Upgrade note:** if you are upgrading from a version older than 1.6 with embedding jobs still queued, drain the queue on a 1.x release before upgrading past this change. Also removed dead tooling config from `pyproject.toml`: the `[tool.mypy]` block (the real config is `mypy.ini`) and Streamlit-era ruff per-file-ignores for files that no longer exist (#1056)
- Committed QA screenshots (12 files) and a stray debug `history.txt` were removed from the repo root, with `.gitignore` rules added so they can't come back (#1053)

### Fixed
- Podcast generation now honors the `speaker_profile` parameter of `POST /api/podcasts/generate` — previously it was silently ignored and the speaker was always re-derived from the episode profile's `speaker_config`, which failed when that pointed at a renamed/deleted speaker profile even if the caller supplied a valid one (#1044)

## [1.11.0] - 2026-07-11

### Added
- `VISION.md` — the product's source of truth in two layers: durable identity (what Open Notebook is and is not, core principles) and current posture (the phase we're in, directional constraints, and the horizon clusters under consideration)
- Decision records at `docs/7-DEVELOPMENT/decisions/` — short, immutable ADRs/PDRs answering "why is it like this?", seeded with 4 retroactive ADRs (SurrealDB, delegation to external libraries, Streamlit→Next.js, background workers) and 2 PDRs (single-user first, provider-agnostic core)
- `AGENTS.md` files (root, `open_notebook/`, `frontend/`) with the normative rules for coding agents and humans — commands, hard rules, and gotchas not derivable from the code; `CLAUDE.md` files are now one-line pointers to them
- Five new engineering docs pages under `docs/7-DEVELOPMENT/`: credentials, content processing, podcasts, prompts, and frontend architecture
- Contribution guidelines for AI-assisted and agent-generated PRs in the contributing guide — the operator owns the PR, issue-first still applies, tests must have actually run
- CI check for broken relative links in markdown (`scripts/check_md_links.py` + `docs-links` workflow on PRs touching `*.md`)
- `cubic.yaml` — AI review settings as code: PR-contract instructions, three custom review agents (vision & principles alignment backed by `VISION.md`, known mechanical caveats, security & testability) and automatic ultrareviews for auth/credential/encryption/migration changes
- Documented the flow-driven release process in `.github/RELEASE_PROCESS.md`, including the `ready` to `main` to stable release path, dev/stable image labels, and maintainer verification checklist (#938)
- List view for the Notebooks page — a tile/list toggle in the header lets you switch between the visual card grid and a compact row layout (name, description, source/note counts, last updated) for easier scanning of large collections. The choice is remembered across reloads and translated across all 14 locales (#885)
- Documented the `ESPERANTO_TTS_TIMEOUT` environment variable (default `300`s) in the environment reference; raise it for slow or self-hosted TTS providers so long podcast segments don't fail with a timeout (#937)
- `SECURITY.md` with a coordinated-disclosure policy: how to privately report a vulnerability via GitHub's private vulnerability reporting, supported versions, and response expectations (#943)
- LaTeX math rendering (KaTeX) now also applies to source content, source insights, Ask answers, transformation output, and the note editor preview — previously only chat had it (#269)
- Syntax highlighting for fenced code blocks in chat responses, source content, insights and Ask/Search answers — light/dark aware, with 25 common languages bundled (others render as plain text) (#783)
- "Recently Viewed" section on the Notebooks page — a collapsible grid of the last 12 notebooks and sources you opened, newest first, hidden when there's no view history. Backed by a new `last_viewed_at` timestamp stamped on read and a `GET /api/recently-viewed` endpoint (translated across all 14 locales) (#850)
- Per-transformation model selection — each transformation can now be assigned its own language model from the transformation editor, overriding the global transformation default for that transformation only. Runs without an explicit model keep using the system default as before (#776)
- "Refresh content" action on web-link sources — re-fetches the URL and re-embeds the source so its content stays current, available from the source card menu once processing has completed (translated across all 14 locales) (#259)
- Sources table can now be sorted by every column — type, title, insights count, embedded status, created and updated (a new "Updated" column was added) — via clickable column headers backed by new `GET /api/sources` sort fields (translated across all locales) (#895)
- EasyPanel deployment template under `examples/easypanel/` — provisions the app plus a dedicated SurrealDB service with auto-generated database/encryption secrets — plus an EasyPanel section in the single-container install guide (#189)
- Test coverage measurement in CI: backend via `pytest-cov` (terminal + XML reports), frontend via `@vitest/coverage-v8` and a new `test:coverage` script (#942)

### Changed
- Developer documentation restructured: 17 knowledge-heavy `CLAUDE.md` files consolidated into the 3 `AGENTS.md` + docs pages above; `README.dev.md` became a pointer after its unique content moved into `development-setup.md` (make-workflow matrix), `.github/RELEASE_PROCESS.md` (Docker publishing) and the change playbooks (add-a-language); the maintainer guide now carries the curated label taxonomy (state funnel, `area:` labels, consolidation rules)
- Fixed stale developer docs while migrating: real migration path/format (`open_notebook/database/migrations/N.surrealql` + `AsyncMigrationManager` registration), provider count (17), locale list (7), and 9 README links that pointed at documentation pages that never existed
- The API's listen interface in the Docker images is now configurable via a new `API_HOST` environment variable instead of a hardcoded `--host 0.0.0.0`. The default is unchanged (`0.0.0.0`); set `API_HOST=::` to serve IPv6/dual-stack environments (#985)
- `docker-compose.yml` now sources the SurrealDB credentials from `SURREAL_USER` / `SURREAL_PASSWORD` (applied to both the database server and the app), defaulting to `root:root` so the zero-config quick start is unchanged. Set them in a `.env` file to use your own credentials before exposing the instance; `.env.example` and the compose file note this (#946)
- Docs no longer claim a hardcoded default API password (`open-notebook-change-me`) exists; the actual behavior is that auth is disabled entirely when `OPEN_NOTEBOOK_PASSWORD` is unset. Also removed the dead `check_api_password` helper that had been superseded by the auth middleware (#1026)

### Fixed
- Testing a valid Google/Vertex credential no longer fails after Google retires a Gemini model. The connection test used a hard-coded model id that Google shuts down on a schedule (`gemini-2.0-flash`), so a valid key surfaced as a broken connection (#970). The Google/Vertex test now uses Google's floating `gemini-flash-latest` alias, and the provider connection test was reframed so only a rejected key, missing permissions, or an unreachable endpoint count as failures — a missing/retired/rate-limited model still reports the credentials as valid. Deprecated `gemini-1.5`/`gemini-2.0` model references were also removed from the connection-test model lists and documentation
- API startup no longer crashes when SurrealDB isn't ready yet (e.g. docker-compose race on host reboot: `Temporary failure in name resolution`). The lifespan now polls a lightweight readiness probe with bounded exponential backoff (~50s budget, 5s per-probe timeout) before running migrations; migration errors themselves still fail fast (#708)
- Markdown typography styles (`prose` classes) are active again: the Tailwind v4 migration left the old `tailwind.config.ts` (which loaded `@tailwindcss/typography`) silently ignored, so rendered markdown lost its typographic styling. The plugin and class-based dark mode are now configured in `globals.css`, and markdown rendering is centralized in a shared `MarkdownRenderer` component (#783)
- Podcast generation no longer truncates on dense, long-form content (`LengthFinishReasonError` / `OUTPUT_PARSING_FAILURE`): episode profiles now support an optional `max_tokens` that is passed through to podcast_creator's outline/transcript generation, overriding its defaults — settable via the episode profile API (UI follow-up in #991) (#639)
- API no longer freezes for all requests while a chat waits on the LLM. Both the notebook chat (`execute_chat`) and source chat handlers ran LangGraph's synchronous `invoke()` directly on the event loop; they now run it via `asyncio.to_thread()` (matching the existing `get_state` calls), so other requests stay responsive — and the source-chat SSE can flush its early events instead of stalling until the model finishes (#704)
- Windows native install guide no longer points users at a `start-open-notebook.bat` that doesn't exist in the repo; the Quick Start now documents starting the four services manually with `uv run`, plus an optional sample launcher you can save yourself (#846)
- OpenRouter (and other providers') "Discover models" dialog no longer cuts off the submit button: the dialog now uses a fixed header/footer with a scrollable body (`grid-rows-[auto_1fr_auto]`) instead of scrolling the whole content, so the "Add" button stays visible regardless of how many models are listed (#816)
- Chat references using the short `[insight:<id>]` form (emitted by some models) are now rendered as clickable citations like `[source_insight:<id>]` and `[note:<id>]` already were; `insight` is treated as an alias for `source_insight`, so clicking it opens the insight (#490)
- CRUD endpoints now return `404` (not `500`) for a non-existent resource. `ObjectModel.get()` raises `NotFoundError` rather than returning a falsy value, so the broad `except Exception` in each handler was masking it as a server error. Added an explicit `NotFoundError → 404` arm to the notebook (update / delete / delete-preview / add-source / remove-source), note (get / update / delete / list / create), model (delete), credential (update / delete) and embed handlers (#862)
- Token counting no longer raises `ValueError: disallowed special token '<|endoftext|>'` when source/context content contains special-token sequences; `token_count()` now encodes with `disallowed_special=()` so such substrings are treated as ordinary text (#667)
- Single-container image no longer hangs at "API not ready yet" on a brand-new instance. `supervisord.single.conf` ran the API and worker with `uv run` (without `--no-sync`), so at startup `uv` tried to sync dev dependencies it couldn't resolve against the `--no-dev` build. Both processes now use `uv run --no-sync`, matching the multi-container `supervisord.conf` (#609)
- Note editor now expands to fill the dialog instead of being capped at `500px`; removed the `max-h-[500px]` constraint that overrode the `flex-1` parent and cramped editing on tall windows (#932)
- Ask and source-chat responses now stream progressively instead of hanging at "Processing..." until the full answer is ready. The API's streaming endpoints now declare `text/event-stream` (with no-buffering headers), and dedicated Next.js route handlers pass the SSE body through as a stream — Next.js `rewrites()` buffers SSE responses to completion (#770)
- Chat, notebook-context and podcast generation now build their context with a single batched insight query instead of one query per source (14 → 3 queries on a 12-source notebook), via the new `SourceInsight.get_for_sources()` (#1008)
- File uploads no longer block the event loop: `save_uploaded_file()` now writes via `asyncio.to_thread()`, keeping the API responsive during large uploads (#1009)
- URL validation no longer blocks the event loop on DNS resolution: `validate_url()` is now async and resolves hostnames via `asyncio.to_thread()`, so a slow DNS lookup on the model-provisioning path can't stall concurrent requests (#1011)
- Creating a credential with an unknown provider name now fails with a clear `422` at the API boundary instead of an opaque error deep in the domain layer; `provider` is validated against the 17 supported providers, and a test keeps the frontend/backend provider lists in sync (#1016)
- Podcast episode listing now batch-fetches job statuses in one query instead of one per episode, speeding up notebooks with many episodes; podcast audio-file paths are additionally verified to stay within the podcasts folder before streaming/deleting (#1018)
- Transformations no longer report success while silently losing their insight when the embedding job fails to queue: `Source.add_insight()` now raises on submission failure (handled by job-level retry), note auto-embedding degrades gracefully instead of turning a note save into a 500, and the explicit note-embed endpoint surfaces queue failures as errors (#1019)
- Clearing a credential field in the edit dialog (Ollama/OpenAI-compatible `base_url`, Vertex `project`/`location`/`credentials_path`) now actually clears it. Two mirror-image bugs made it impossible: the frontend dropped emptied fields from the PUT body (`undefined` keys are stripped by `JSON.stringify`), and the API ignored explicit `null`s (`is not None` guards) — so the old value survived while the UI reported success. The frontend now sends explicit `null` and the API keys partial updates on field presence (`model_fields_set`) (#1046)

### Security
- Resolved dependency audit findings: added npm `overrides` for vulnerable transitive frontend packages (`ws`, `brace-expansion`, `ajv`, `@eslint/plugin-kit`, `postcss`) — `npm audit` now reports 0 vulnerabilities — refreshed `uv.lock` (`langsmith`, `pydantic-settings`, `pip`), and hardened external `window.open(..., '_blank')` calls with `noopener,noreferrer` (#962)
- SurrealQL injection via record ids in `repo_relate()`/`repo_upsert()`/`repo_update()`: a crafted `notebook_id` on the save-insight-as-note flow could execute arbitrary SurrealQL. Record identifiers are now bound as query parameters, and the target notebook's existence is validated before relating (#1002)
- The API password is now compared with `secrets.compare_digest()` instead of `!=`, closing a timing side-channel on authentication (#1003)
- User-authored transformation prompts are no longer compiled as Jinja2 template source (a DoS vector via template loops); they are passed as plain variables into fixed developer-authored templates, so Jinja syntax inside a prompt renders as inert text. Output is unchanged for legitimate prompts (#1004)
- SSRF protection on source-URL ingestion: adding a web-link source now runs the same `validate_url()` guard already used for credential URLs, rejecting internal/private/cloud-metadata addresses (#1005)
- Provider-credential URLs are re-validated immediately before every outbound request (connection tests, model discovery and inference) instead of only at save time, closing a DNS-rebinding window; AWS's IPv6 metadata address was added to the blocklist (#1006)
- The note/transformation markdown preview now sanitizes raw HTML via `rehype-sanitize`: `<iframe>`/`<script>`/`<style>` tags and `javascript:` URLs are stripped while math, syntax highlighting and GFM still render — closing an HTML-injection path via AI-generated note content (#1007)
- Vertex credential-test errors no longer reveal whether a `credentials_path` file is missing, invalid JSON or wrong-shape JSON (a filesystem oracle); all three cases now return one generic message (#1012)
- CORS no longer combines the wildcard origin with `allow_credentials=True` (which made Starlette reflect any Origin verbatim for credentialed requests); credentials are now only allowed when `CORS_ORIGINS` is explicitly configured (#1013)
- Request bodies are now capped before auth and routing by a new `MaxBodySizeMiddleware` — default 100 MB, configurable via the new `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` environment variable; chunked uploads are caught by a streaming byte-count (#1014)
- Source upload hardening: unique filenames are claimed atomically (closing a TOCTOU race between the exists-check and the write), path-containment checks require a trailing separator so sibling directories can't pass, and the `notebooks`/`transformations` arrays on source creation are capped at 50 items (#1015)
- API 500 responses from the sources and podcast endpoints no longer echo internal exception text (which could leak DB hostnames or connection details); responses use fixed generic messages and details remain in server logs (#1017)
- `Credential.get_all()` no longer builds its ORDER BY clause from a raw f-string; ordering fields now go through the base-class allowlist validation (not reachable from the current API surface — defense in depth) (#1021)
- The frontend runtime-config endpoint validates `Host` and `X-Forwarded-Proto` before using them to build the browser-facing API URL, preventing a spoofed Host header from redirecting browser API traffic (including the bearer token) to an attacker-controlled origin; malformed values fall back to localhost (#1024)
- `docker-compose.yml` now binds SurrealDB's published port to `127.0.0.1` instead of all interfaces, so the database (root:root by default) is no longer reachable from other machines out of the box; a new `docker-compose.override.yml.example` shows how to re-expose it deliberately (#1025)
- Forced **Pillow to 12.3.0**, resolving 6 open Dependabot advisories (3 high: PSD out-of-bounds writes, FITS GZIP decompression bomb; 3 moderate: PDF trailer DoS, font integer overflow, heap buffer overflow). The only blocker was moviepy's `pillow<12` cap (pulled in via podcast-creator) — moviepy only touches PIL in its video modules, which the audio-only podcast pipeline never imports, so a documented `[tool.uv] override-dependencies` entry forces the safe version until podcast-creator ships without moviepy (#1041)

## [1.10.0] - 2026-06-17

### Security
- Bumped **Starlette to 1.2.1** and **FastAPI to 0.136.3** to address **CVE-2026-48710** ("BadHost"), a denial-of-service in Starlette's host header handling (#859)

### Added
- LaTeX math rendering in chat — inline (`$...$`) and display (`$$...$$`) expressions are now rendered with KaTeX (#606)
- `NEXT_PUBLIC_API_TIMEOUT_MS` environment variable to configure the frontend API request timeout (default `600000` = 10 minutes; set `0` to disable). Lets slow/long-running chat models finish without editing source (#880)
- Bulk chat-context actions in a notebook, via a "Context" menu in the Sources and Notes column headers — translated across all 14 locales (#223):
  - Sources: "Include all (insights only)" (sources without insights are left out rather than forced to full), "Include all (full content)", and "Exclude all from context"
  - Notes: "Include all in context" / "Exclude all from context"
- **Turkish (tr-TR) localization** — the UI is now fully translated into Turkish (#871)

### Changed
- Failed source cards now show a prominent "Retry processing" button directly on the card instead of only inside the 3-dot dropdown; clicking it no longer also opens the source (the click was missing `stopPropagation`) (#726)
- Docker base image updated to **Debian trixie** and **Node.js 22.x** (#914)

### Fixed
- Podcast generation now uses the notebook's real content. `Notebook.get_context()` was missing, so generation ran against empty context; it now assembles source and note content as expected (#864)
- `PUT` profile handlers now use `model_dump(exclude_unset=True)`, so partial updates no longer overwrite unspecified fields with defaults (#860)
- OpenRouter embedding models are now correctly recognized via their embedding modality (#842)
- Search and Ask results now use page-level scrolling instead of being confined to a cramped, height-capped (`60vh`) bottom container, so the full result set is readable (#882)
- `POST /sources/{id}/retry` no longer returns `400 "Source is not associated with any notebooks"` for every source; it now queries the `reference` graph edge by its `in`/`out` columns instead of a non-existent `source` column (#861)
- `POST /sources/{id}/retry` no longer returns a `500` ("too many values to unpack") after successfully queuing the retry job; the command ID was being double-prefixed (`command:command:…`) before being saved to the source. Retrying a failed source now succeeds and updates the source's command reference
- `GET /sources/{id}` for a missing or deleted source now returns `404` instead of `500`; the handler caught `NotFoundError` in its generic `except` and mapped it to a server error
- Sources that fail to ingest (e.g. an unreachable or invalid URL) are now marked `failed` instead of silently saved as `completed` with the extraction error as their body. This means the "Retry processing" button (#726) actually appears for the most common failure mode; previously the job returned a failure payload but the command still completed, so the source never reached a retryable state (#726)
- Text search no longer returns a 500 when SurrealDB's `search::highlight` hits a "position overflow" on large or multi-byte document chunks; it now falls back to vector search and returns results (#648)
- `POST /api/search` now rejects a non-positive `limit` with a `422` instead of passing `LIMIT -1`/`LIMIT 0` to SurrealDB (which caused a 500 or a silently empty result set) (#863)
- Ollama `num_ctx` credential override is now persisted. The `credential` table gained a flexible `config` object (migration 15) and provider-specific tuning options are stored there instead of being dropped by the SCHEMAFULL table; future per-credential options can be added without a schema migration (#875)
- Worker no longer crashes on queued jobs from older versions; legacy embedding command aliases (`embed_single_item`, `embed_chunk`, `vectorize_source`) are registered and delegate to the current commands so stale queues drain cleanly (#695, #876)

### Performance
- Notebook source list no longer re-renders every `SourceCard` on unrelated state changes (layout toggles, context selection), and completed sources no longer each open a status-polling query. Both scaled with the number of sources and caused UI lag on large notebooks (#503)

## [1.9.0] - 2026-06-02

### Added
- **New audio providers**, surfacing the capabilities added in Esperanto 2.21–2.22:
  - **Mistral Voxtral** speech-to-text (`voxtral-*-latest`) and text-to-speech (`voxtral-mini-tts`), reusing the existing Mistral credential (#827)
  - **Deepgram** text-to-speech (Aura voice catalog) as a new provider (`DEEPGRAM_API_KEY`) (#827)
  - **xAI** text-to-speech (#827)
  - **Google** speech-to-text & text-to-speech, **Vertex** text-to-speech, and **ElevenLabs** speech-to-text (Scribe), completing the audio provider matrix (#828)
- Optional per-credential **`num_ctx`** (context window) override for Ollama models, configurable in Settings → API Keys and translated across all 13 locales (#825)
- `OPEN_NOTEBOOK_EMBEDDING_BATCH_SIZE` environment variable to override the embedding batch size; default remains `50`. Helps with CPU-only local embedding and stricter OpenAI-compatible endpoints (#735)
- `CORS_ORIGINS` environment variable to configure the API's allowed origins (comma-separated). Default remains `*` for backward compatibility; the API now logs a startup warning prompting users to set it for production deployments. Exception responses honor the configured origins when explicitly set (#585, #597, #730)
- `OPEN_NOTEBOOK_MIN_CHUNK_SIZE` environment variable (default: 5 tokens) to filter out degenerate tiny chunks before embedding. Set to `0` to disable.

### Changed
- Bumped **Esperanto 2.20.0 → 2.22.0**. Beyond the new audio providers above, this inherits several upstream fixes and behavior changes (see below).

### Inherited from Esperanto 2.21–2.22
- **Fixed:** OpenRouter LLM and embedding requests now send a proper JSON body (previously sent a malformed form-encoded payload).
- **Fixed:** OpenAI-compatible endpoints (e.g. llama.cpp) that return null embeddings now raise a clear, descriptive error instead of an opaque `TypeError`.
- **Fixed:** Streaming tool calls now return proper `ToolCall` objects across Anthropic, Google, Vertex, and Ollama.
- **Fixed:** `base_url` trailing slashes are normalized across providers, preventing double-slash URLs (and 301 redirects) for Ollama and other self-hosted endpoints.
- **Fixed:** Ollama "thinking" models (e.g. Qwen) now merge their reasoning content correctly.
- **Fixed:** Model discovery honors a custom `base_url` (LiteLLM/vLLM/OpenAI-compatible proxies).
- **Behavior change:** the Ollama default context window (`num_ctx`) is now **8192** (was 128000) to avoid out-of-memory errors on consumer GPUs. Raise it per-credential via the new `num_ctx` field if your hardware allows.
- **Behavior change:** the Google embedding default model is now `gemini-embedding-001` (the previous default, `text-embedding-004`, was removed from Google's API). If you used Google embeddings with the old default, re-create the model and re-embed your content (embedding dimensions changed).
- **Fixed:** Google TTS default model updated to a currently-working preview model.

### Fixed
- URL source embedding no longer crashes with `TypeError: float() argument must be a string or a real number, not 'NoneType'` when header-based splitters emit single-character fragments from complex HTML pages (e.g. Wikipedia, Project Gutenberg). Such chunks are now filtered before being sent to the embedding provider (#764)
- Language toggle now uses `t('common.german')` instead of a hardcoded "Deutsch" label, matching the pattern used by every other language entry (follow-up to #794)
- Speech-to-text model connection tests now transcribe a short bundled speech clip instead of silence, so a passing test returns real text instead of a blank transcription (#838)

## [1.8.5] - 2026-04-14

### Changed
- Embedding chunking is now token-based instead of character-based, improving chunk sizing consistency for CJK and mixed-language content (#542, #749)
- `OPEN_NOTEBOOK_CHUNK_SIZE` and `OPEN_NOTEBOOK_CHUNK_OVERLAP` semantics changed from characters to tokens; default reduced from 1200 characters to 400 tokens to stay safely below the 512-token ceiling of BERT-family embedders (e.g. mxbai-embed-large) after accounting for tokenizer mismatch and splitter overshoot. Existing stored embeddings are unaffected; only new ingestions use the new chunking.

### Fixed
- Credentials endpoint no longer crashes (500) when encryption key doesn't match stored credentials (#740)
- Broken credentials are now shown with a decryption warning and can still be deleted
- DELETE endpoint for broken credentials supports model migration (`migrate_to` parameter)

## [1.8.4] - 2026-04-09

### Security
- Fix Remote Code Execution (RCE) via Jinja2 Server-Side Template Injection in transformations (CVSS 9.2 Critical)
- Fix arbitrary file write via path traversal in file upload (CVSS 7.0 High)
- Fix arbitrary file read via Local File Inclusion in source creation (CVSS 8.2 High)

### Dependencies
- Bump ai-prompter to >=0.4.0 (uses Jinja2 SandboxedEnvironment to prevent SSTI)

## [1.8.3] - 2026-04-07

### Security
- Fix SurrealDB injection via unsanitized `order_by` query parameter in `GET /api/notebooks` (CVSS 8.7 High)
- Add allowlist validation for sorting parameters in notebooks endpoint
- Replace f-string query interpolation with parameterized `$variable` binding in source chat and migration queries
- Add defensive validation in `get_all()` base method to prevent injection via `order_by` parameter

## [1.8.2] - 2026-04-06

### Added
- DashScope (Qwen) and MiniMax provider support via Esperanto v2.20.0 (#725)
- Source list auto-refresh after adding a new source via URL, file upload, or text (#721)

### Fixed
- Source asset persistence — failed sources now persist their asset (URL/file path), making them identifiable and retryable (#722)
- Source title preservation — user-set custom titles are no longer overwritten after background processing (#722)
- Credential cascade delete — deleting a credential now removes linked models instead of returning a 409 error (#722)
- Podcast directory names — uses UUID for episode directories, fixing filesystem errors with special characters (#666)
- Tiktoken offline handling — API no longer crashes in air-gapped environments (#622)
- SurrealDB healthcheck — removed incompatible healthcheck from Docker Compose (#656)
- Esperanto embedding fixes — base_url/api_key config issues across multiple embedding providers (#664, #665)

### Docs
- Deprecated single-container Docker image in favor of Docker Compose (#723)

### Dependencies
- Bump esperanto to >=2.20.0

## [1.8.1] - 2026-03-10

### Added
- i18n support for Bengali (bn-IN) (#643)
- Podcast language support via podcast-creator 0.12.0 (#645)
- Upgrade default Azure API version for model testing and fetching (#638)

### Fixed
- Tiktoken network errors in offline/air-gapped Docker deployments — pre-downloads encoding at build time (#264, #622)
- SurrealDB getting stuck (#656)

### Dependencies
- Bump esperanto to 2.19.5 (#657)
- Bump langgraph from 1.0.6 to 1.0.10rc1 (#658)
- Bump authlib from 1.6.6 to 1.6.7 (#649)
- Bump lxml-html-clean from 0.4.3 to 0.4.4 (#646)
- Bump rollup from 4.55.1 to 4.59.0 (#635)
- Bump minimatch in frontend (#634)
- Bump tar from 7.5.9 to 7.5.11 (#650, #659)

## [1.7.4] - 2026-02-18

### Fixed
- Embedding large documents (3MB+) fails with 413 Payload Too Large (#594)
- `generate_embeddings()` now batches texts in groups of 50 with per-batch retry, preventing provider payload limits from being exceeded
- 413 errors now classified with user-friendly message in error classifier
- Misleading "Created 0 embedded chunks" log in `process_source_command` — embedding is fire-and-forget, so the count was always 0; now logs "embedding submitted" instead

## [1.7.3] - 2026-02-17

### Added
- Retry button for failed podcast episodes in the UI (#211, #218)
- Error details displayed on failed podcast episodes (#185, #355)
- `POST /podcasts/episodes/{id}/retry` API endpoint for re-submitting failed episodes
- `error_message` field in podcast episode API responses

### Fixed
- Podcast generation failures now correctly marked as "failed" instead of "completed" (#300, #335)
- Disabled automatic retries for podcast generation to prevent duplicate episode records (#302)

### Dependencies
- Bump podcast-creator to >= 0.11.2
- Bump esperanto to >= 2.19.4

## [1.7.2] - 2026-02-16

### Added
- Error classification utility that maps LLM provider errors to user-friendly messages (#506)
- Global exception handlers in FastAPI for all custom exception types with proper HTTP status codes
- `getApiErrorMessage()` frontend helper that falls back to backend messages when no i18n mapping exists

### Fixed
- LLM errors (invalid API key, wrong model, rate limits) now show descriptive messages instead of "An unexpected error occurred" (#590)
- SSE streaming error events in source chat and ask hooks were swallowed by inner JSON parse catch blocks
- Transformation execution errors were caught and re-wrapped as generic 500s instead of using proper status codes
- Fail fast when source content extraction returns empty instead of retrying (#589)
- Chat input and message overflow with long unbroken strings (#588)
- Word-wrap overflow in source cards, note editor, inline edit, note titles, and dialog content (#588)
- Translation proxy shadowing `name` keys (#588)
- OpenAI-compatible provider name handling via Esperanto update (#583)

### Changed
- `ValueError` replaced with `ConfigurationError` in model provisioning for proper error classification
- `ConfigurationError` added to command retry `stop_on` lists to avoid retrying permanent config failures

### Dependencies
- Bump esperanto to 2.19.3 (#583)
- Bump podcast-creator to 0.9.1

## [1.7.1] - 2026-02-14

### Added
- French (fr-FR) language support (#581)
- CI test workflow and improved i18n validation (#580)
- Expose embed `command_id` in note API responses (#545)

### Fixed
- ElevenLabs TTS credential passthrough via Esperanto update (#578)
- Handle empty/whitespace source content without retry loop (#576)
- Increase transformation `max_tokens` and update Esperanto dep (#568)
- Turn the embedding field into optional (#557)

### Docs
- Fix docker container names in local setup guides (#577)

### Dependencies
- Bump langchain-core from 1.2.7 to 1.2.11 (#564)
- Bump cryptography from 46.0.3 to 46.0.5 (#563)

## [1.7.0] - 2026-02-10

### Added
- **Credential-Based Provider Management** (#477)
  - New Settings → API Keys page for managing AI provider credentials via the UI
  - Support for 14 providers: OpenAI, Anthropic, Google, Groq, Mistral, DeepSeek, xAI, OpenRouter, Voyage AI, ElevenLabs, Ollama, Azure OpenAI, OpenAI-Compatible, and Vertex AI
  - Secure storage of API keys in SurrealDB with field-level encryption (Fernet AES-128-CBC + HMAC-SHA256)
  - One-click connection testing, model discovery, and model registration per credential
  - Migration tool to import existing environment variable keys into the credential system
  - Azure OpenAI support with service-specific endpoints (LLM, Embedding, STT, TTS)
  - OpenAI-Compatible support with per-service URL configurations
  - Vertex AI support with project, location, and credentials path
  - Environment variable API keys deprecated in favor of Settings UI

- **Security Enhancements**
  - Docker secrets support via `_FILE` suffix pattern (e.g., `OPEN_NOTEBOOK_PASSWORD_FILE`)
  - Default encryption key derived from "0p3n-N0t3b0ok" for easy setup (change in production!)
  - Default password "open-notebook-change-me" for out-of-box experience (change in production!)
  - URL validation for SSRF protection - blocks private IPs and localhost (except for Ollama which runs locally)
  - Security warnings logged when using default credentials

- HTML clipboard detection for text sources (#426)
  - When pasting content, automatically detects HTML format (e.g., from Word, web pages)
  - Shows info message when HTML is detected, informing user it will be converted to Markdown
  - Preserves formatting that would be lost with plain text paste
  - Bump content-core to 0.11.0 for HTML to Markdown conversion support

- **Improved Getting Started Experience**
  - Simplified docker-compose.yml in repository root (single official file)
  - Added examples/ folder with ready-made configurations:
    - `docker-compose-ollama.yml` - Local AI with Ollama
    - `docker-compose-speaches.yml` - Local TTS/STT with Speaches
    - `docker-compose-full-local.yml` - 100% local setup (Ollama + Speaches)
  - Inline quick start in README (no need to navigate to docs)
  - Cross-references between docker-compose examples and documentation
  - .env.example template with all configuration options

### Fixed
- Azure form race condition: all configuration now saved in single atomic request
- Migration API "error error" display: added proper MigrationResult model with message field
- Connection tester for Ollama providers: improved error handling and URL validation
- SqliteSaver async compatibility issues in chat system (#509, #525, #538)
- Re-embedding failures with empty content (#513, #515)
- Deletion cascade for notes and sources (#77)
- YouTube content availability issues (#494)
- Large document embedding errors (#489)

### Security
- API keys are encrypted at rest using Fernet symmetric encryption
- Keys are never returned to the frontend, only configuration status
- SSRF protection prevents internal network access via URL validation

### Docs
- Complete documentation update for credential-based system across 25 files
- All quick-start, installation, and configuration guides now use Settings UI workflow
- Environment variable API key instructions moved to deprecated/legacy sections
- Fixed broken links in installation docs
- Added comprehensive examples/ folder with documented docker-compose configurations
- Updated local-tts.md and local-stt.md with links to ready-made examples

### Internationalization
- Added Russian (ru-RU) language support (#524)
- Added Italian (it-IT) language support (#508)

## [1.6.2] - 2026-01-24

### Fixed
- Connection error with llama.cpp and OpenAI-compatible providers (#465)
  - Bump Esperanto to 2.17.2 which fixes LangChain connection errors caused by garbage collection

## [1.6.1] - 2026-01-22

### Fixed
- "Failed to send message" error with unhelpful logs when chat model is not configured (#358)
  - Added detailed error logging with model selection context and full traceback
  - Improved error messages to guide users to Settings → Models
  - Added warnings when default models are not configured

### Docs
- Ollama troubleshooting: Added "Model Name Configuration" section emphasizing exact model names from `ollama list`
- Added troubleshooting entry for "Failed to send message" error with step-by-step solutions
- Updated AI Chat Issues documentation with model configuration guidance


## [1.6.0] - 2026-01-21

### Added
- Content-type aware text chunking with automatic HTML, Markdown, and plain text detection (#350, #142)
- Unified embedding generation with mean pooling for large content that exceeds model context limits
- Dedicated embedding commands: `embed_note`, `embed_insight`, `embed_source`
- New utility modules: `chunking.py` and `embedding.py` in `open_notebook/utils/`
- Japanese (ja-JP) language support (#450)

### Changed
- Embedding is now fire-and-forget: domain models submit embedding commands asynchronously after save
- `rebuild_embeddings_command` now delegates to individual embed_* commands instead of inline processing
- Chunk size reduced to 1500 characters for better compatibility with Ollama embedding models
- Bump Esperanto to 2.16 for increased Ollama context window support

### Removed
- Legacy embedding commands: `embed_single_item_command`, `embed_chunk_command`, `vectorize_source_command`
- `needs_embedding()` and `get_embedding_content()` methods from domain models
- `split_text()` function from text_utils (replaced by `chunk_text()` in chunking module)

### Fixed
- Embedding failures when content exceeds model context limits (#350, #142)
- Empty note titles when saving from chat (clean thinking tags from prompt graph output)
- Orphaned embedding/insight records when deleting sources (cascade delete)
- Search results crash with null parent_id (defensive frontend check)
- Database migration 10 cleans up existing orphaned records

## [1.5.2] - 2026-01-15

### Performance
- Improved source listing speed by 20-30x (#436, closes #351)
  - Added database indexes on `source` field for `source_insight` and `source_embedding` tables
  - Use SurrealDB `FETCH` clause for command status instead of N async calls

## [1.5.1] - 2026-01-15

### Fixed
- Podcast dialog infinite loop error caused by excessive translation Proxy accesses in loops
- Podcast dialog UI freezing when typing episode name or additional instructions
- Removed incorrect translation keys for user-defined episode profiles (user content should not be translated)

## [1.5.0] - 2026-01-15

### Added
- Internationalization (i18n) support with Chinese (Simplified and Traditional) translations (#371, closes #344, #349, #360)
- Frontend test infrastructure with Vitest (#371)
- Language toggle component for switching UI language (#371)
- Date localization using date-fns locales (#371)
- Error message translation system (#371)

### Fixed
- Accessibility improvements: added missing `id`, `name`, and `autoComplete` attributes to form inputs (#371)
- Added `DialogDescription` to dialogs for Radix UI accessibility compliance (#371)
- Fixed "Collapsible is changing from uncontrolled to controlled" warning in SettingsForm (#371)
- Fixed lint command for Next.js 16 compatibility (`eslint` instead of `next lint`)

### Changed
- Dockerfile optimizations: better layer caching, `--no-install-recommends` for smaller images (#371)
- Dockerfile.single refactored into 3 separate build stages for better caching (#371)

## [1.4.0] - 2026-01-14

### Added
- CTA button to empty state notebook list for better onboarding (#408)
- Offline deployment support for Docker containers (#414)

### Fixed
- Large file uploads (>10MB) by upgrading to Next.js 16 (#423)
- Orphaned uploaded files when sources are removed (#421)
- Broken documentation links to ai-providers.md (#419)
- ZIP support indication removed from UI (#418)
- Duplicate Claude Code workflow runs on PRs (#417)
- Claude Code review workflow now runs on PRs from forks (#416)

### Changed
- Upgraded Next.js from 15.4.10 to 16.1.1 (#423)
- Upgraded React from 19.1.0 to 19.2.3 (#423)
- Renamed `middleware.ts` to `proxy.ts` for Next.js 16 compatibility (#423)

### Dependencies
- next: 15.4.10 → 16.1.1
- react: 19.1.0 → 19.2.3
- react-dom: 19.1.0 → 19.2.3

## [1.2.4] - 2025-12-14

### Added
- Infinite scroll for notebook sources - no more 50 source limit (#325)
- Markdown table rendering in chat responses, search results, and insights (#325)

### Fixed
- Timeout errors with Ollama and local LLMs - increased to 10 minutes (#325)
- "Unable to Connect to API Server" on Docker startup - frontend now waits for API health check (#325, #315)
- SSL issues with langchain (#274)
- Query key consistency for source mutations to properly refresh infinite scroll (#325)
- Docker compose start-all flow (#323)

### Changed
- Timeout configuration now uses granular httpx.Timeout (short connect, long read) (#325)

### Dependencies
- Updated next.js to 15.4.10
- Updated httpx to >=0.27.0 for SSL fix
