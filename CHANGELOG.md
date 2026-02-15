# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
