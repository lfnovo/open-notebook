# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **API Configuration UI** (#477)
  - New Settings page for configuring AI provider API keys directly in the UI
  - Support for 14 providers: OpenAI, Anthropic, Google, Groq, Mistral, DeepSeek, xAI, OpenRouter, Voyage AI, ElevenLabs, Ollama, Azure OpenAI, OpenAI-Compatible, and Vertex AI
  - Secure storage of API keys in SurrealDB with field-level encryption (Fernet AES-128-CBC + HMAC-SHA256)
  - Dynamic fallback: checks database first, then environment variables
  - Connection testing for each provider with "Test Connection" button
  - Migration tool to transfer existing environment variable keys to database
  - Azure OpenAI support with service-specific endpoints (LLM, Embedding, STT, TTS)
  - OpenAI-Compatible support with service-specific configurations
  - Vertex AI support with project, location, and credentials path

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

### Fixed
- Azure form race condition: all configuration now saved in single atomic request
- Migration API "error error" display: added proper MigrationResult model with message field
- Connection tester for Ollama providers: improved error handling and URL validation

### Security
- API keys are encrypted at rest using Fernet symmetric encryption
- Keys are never returned to the frontend, only configuration status
- SSRF protection prevents internal network access via URL validation

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
