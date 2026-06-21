# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- List view for the Notebooks page — a tile/list toggle in the header lets you switch between the visual card grid and a compact row layout (name, description, source/note counts, last updated) for easier scanning of large collections. The choice is remembered across reloads and translated across all 14 locales (#885)
- Documented the `ESPERANTO_TTS_TIMEOUT` environment variable (default `300`s) in the environment reference; raise it for slow or self-hosted TTS providers so long podcast segments don't fail with a timeout (#937)
- `SECURITY.md` with a coordinated-disclosure policy: how to privately report a vulnerability via GitHub's private vulnerability reporting, supported versions, and response expectations (#943)
- LaTeX math rendering (KaTeX) now also applies to source content, source insights, Ask answers, transformation output, and the note editor preview — previously only chat had it (#269)

### Changed
- `docker-compose.yml` now sources the SurrealDB credentials from `SURREAL_USER` / `SURREAL_PASSWORD` (applied to both the database server and the app), defaulting to `root:root` so the zero-config quick start is unchanged. Set them in a `.env` file to use your own credentials before exposing the instance; `.env.example` and the compose file note this (#946)

### Fixed
- OpenRouter (and other providers') "Discover models" dialog no longer cuts off the submit button: the dialog now uses a fixed header/footer with a scrollable body (`grid-rows-[auto_1fr_auto]`) instead of scrolling the whole content, so the "Add" button stays visible regardless of how many models are listed (#816)
- Chat references using the short `[insight:<id>]` form (emitted by some models) are now rendered as clickable citations like `[source_insight:<id>]` and `[note:<id>]` already were; `insight` is treated as an alias for `source_insight`, so clicking it opens the insight (#490)
- CRUD endpoints now return `404` (not `500`) for a non-existent resource. `ObjectModel.get()` raises `NotFoundError` rather than returning a falsy value, so the broad `except Exception` in each handler was masking it as a server error. Added an explicit `NotFoundError → 404` arm to the notebook (update / delete / delete-preview / add-source / remove-source), note (get / update / delete / list / create), model (delete), credential (update / delete) and embed handlers (#862)
- Token counting no longer raises `ValueError: disallowed special token '<|endoftext|>'` when source/context content contains special-token sequences; `token_count()` now encodes with `disallowed_special=()` so such substrings are treated as ordinary text (#667)
- Single-container image no longer hangs at "API not ready yet" on a brand-new instance. `supervisord.single.conf` ran the API and worker with `uv run` (without `--no-sync`), so at startup `uv` tried to sync dev dependencies it couldn't resolve against the `--no-dev` build. Both processes now use `uv run --no-sync`, matching the multi-container `supervisord.conf` (#609)
- Note editor now expands to fill the dialog instead of being capped at `500px`; removed the `max-h-[500px]` constraint that overrode the `flex-1` parent and cramped editing on tall windows (#932)

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
