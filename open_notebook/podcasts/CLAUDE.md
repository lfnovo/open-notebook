# Podcasts Module

Domain models for podcast generation featuring speaker and episode profile management with job tracking.

## Purpose

Encapsulates podcast metadata and configuration: speaker profiles (voice/personality config), episode profiles (generation settings), and podcast episodes (with job status tracking via surreal-commands).

## Architecture Overview

Two-tier profile system using the **model registry** for AI model references:
- **SpeakerProfile**: `voice_model` (record<model> reference) + 1-4 speaker configurations (name, voice_id, backstory, personality). Per-speaker `voice_model` overrides supported.
- **EpisodeProfile**: `outline_llm`/`transcript_llm` (record<model> references) for LLM selection, `language` field (BCP 47 locale code), segment count, briefing template.
- **PodcastEpisode**: Generated episode record linking profiles, content, and async job.

All inherit from `ObjectModel` (SurrealDB base class with table_name and save/load).

## Component Catalog

### models.py

#### `_resolve_model_config(model_id)` (module-level helper)
- Loads a Model record by ID, resolves its credential, returns `(provider, model_name, config_dict)` tuple.
- Used by `resolve_outline_config()`, `resolve_transcript_config()`, `resolve_tts_config()`, and per-speaker TTS overrides in `podcast_commands.py`.
- Falls back to `provision_provider_keys()` if no credential is linked.

#### SpeakerProfile
- `voice_model`: Optional `record<model>` reference for TTS (replaces legacy `tts_provider`/`tts_model` strings).
- Legacy fields `tts_provider`/`tts_model` kept as optional for migration compatibility.
- `nullable_fields` ClassVar lists fields that may be null in the database.
- Validates 1-4 speakers with required fields: name, voice_id, backstory, personality.
- Per-speaker `voice_model` override: individual speakers can reference a different TTS model.
- `_prepare_save_data()` converts `voice_model` (and per-speaker overrides) to RecordID before save.
- `resolve_tts_config()` resolves `voice_model` via `_resolve_model_config()`. Raises ValueError if not set.
- `get_by_name()` async query by profile name.

#### EpisodeProfile
- `outline_llm`/`transcript_llm`: Optional `record<model>` references (replace legacy `outline_provider`/`outline_model`/`transcript_provider`/`transcript_model` strings).
- `language`: Optional BCP 47 locale code for podcast language (e.g. `pt-BR`, `en-US`).
- Legacy fields kept as optional for migration compatibility.
- `nullable_fields` ClassVar lists fields that may be null in the database.
- `num_segments` validated between 3 and 20.
- References `speaker_config` by name.
- `_prepare_save_data()` converts `outline_llm`/`transcript_llm` to RecordID before save.
- `resolve_outline_config()` / `resolve_transcript_config()` resolve model references via `_resolve_model_config()`. Raise ValueError if not set.
- `get_by_name()` async query.

#### PodcastEpisode
- Stores episode_profile and speaker_profile as dicts (snapshots of config at generation time).
- Optional audio_file path, transcript/outline dicts.
- **Job tracking**: command field links to surreal-commands RecordID.
- `get_job_status()` fetches async job status via surreal-commands library.
- `get_job_detail()` returns both status and error_message from the job (used for retry validation and UI error display).
- `_prepare_save_data()` ensures command field is always RecordID format for database.

### migration.py

Data migration for podcast profiles: maps legacy provider/model strings to Model registry record IDs. Runs on API startup after SQL migrations (called from `api/main.py` lifespan).

- `_find_model_record()`: Finds an existing Model record matching provider + name + type.
- `_find_or_create_model()`: Finds existing Model record or auto-creates one linked to a provider credential.
- `migrate_podcast_profiles()`: Migrates all episode and speaker profiles. Idempotent -- skips profiles where new fields are already populated. Logs counts of migrated/skipped/failed profiles.

## Common Patterns

- **Model registry references**: Profile fields reference `record<model>` IDs instead of raw provider/model strings. Credentials are resolved at runtime via `_resolve_model_config()`.
- **Profile snapshots**: episode_profile and speaker_profile stored as dicts on PodcastEpisode to freeze config at generation time.
- **Field validation**: Pydantic validators enforce constraints (segment count, speaker count, required fields).
- **Async database access**: `get_by_name()` queries via repo_query.
- **Job tracking**: command field delegates to surreal-commands; get_job_status() returns "unknown" on failure.
- **Record ID handling**: `_prepare_save_data()` converts model ID strings to RecordID before save; `ensure_record_id()` handles both string and RecordID inputs.
- **nullable_fields ClassVar**: Declares fields that may be null/absent in the database, allowing ObjectModel to handle them during deserialization.

## Key Dependencies

- `pydantic`: Field validators, ObjectModel inheritance
- `surrealdb`: RecordID type for job and model references
- `open_notebook.database.repository`: repo_query, ensure_record_id
- `open_notebook.domain.base`: ObjectModel base class
- `open_notebook.ai.models`: Model class (for `_resolve_model_config`)
- `open_notebook.ai.key_provider`: provision_provider_keys (fallback)
- `open_notebook.domain.credential`: Credential (for migration)
- `surreal_commands` (optional): get_command_status() for job status

## Important Quirks & Gotchas

- **Legacy fields preserved**: `tts_provider`/`tts_model` on SpeakerProfile and `outline_provider`/`outline_model`/`transcript_provider`/`transcript_model` on EpisodeProfile are kept as optional nullable fields for backward compatibility with the data migration. The app ignores them at runtime.
- **Snapshot approach**: Episode/speaker profiles stored as dicts (not references), so profile updates don't retroactively affect past episodes.
- **Job status resilience**: get_job_status() catches all exceptions and returns "unknown" (no error propagation).
- **No automatic retries**: Podcast generation commands use `retry={"max_attempts": 1}` to prevent duplicate episode records on failure; retry is user-initiated via `POST /podcasts/episodes/{id}/retry`.
- **validate_speakers executes late**: Validators run at instantiation; bulk inserts may not trigger full validation.
- **RecordID coercion**: `_prepare_save_data()` converts model ID strings to RecordID; command field parsed during deserialization.
- **No cascade delete**: Removing a profile doesn't cascade to episodes using it.
- **Migration is idempotent**: `migrate_podcast_profiles()` skips profiles that already have new fields populated. Safe to run multiple times.
- **Migration auto-creates models**: If a legacy provider/model string has no matching Model record but a credential exists for that provider, the migration auto-creates a Model record linked to the credential.

## How to Extend

1. **Add new speaker field**: Add to required_fields list in validate_speakers()
2. **Add episode config field**: Validate in EpisodeProfile, update briefing generation code; add to nullable_fields if optional
3. **Add job metadata**: Extend PodcastEpisode with new fields (e.g., progress tracking)
4. **Change job provider**: Replace surreal-commands with alternative job queue library; update get_job_status()
5. **Add new model reference field**: Add field, add to nullable_fields, add RecordID conversion in `_prepare_save_data()`, add resolve method using `_resolve_model_config()`
