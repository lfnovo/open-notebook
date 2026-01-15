# Podcasts Module

Domain models for podcast generation featuring speaker and episode profile management with job tracking.

## Purpose

Encapsulates podcast metadata and configuration: speaker profiles (voice/personality config), episode profiles (generation settings), and podcast episodes (with job status tracking via surreal-commands).

## Architecture Overview

Two-tier profile system:
- **SpeakerProfile**: TTS provider/model + 1-4 speaker configurations (name, voice_id, backstory, personality)
- **EpisodeProfile**: Generation settings (outline/transcript models, segment count, briefing template)
- **PodcastEpisode**: Generated episode record linking profiles, content, and async job

All inherit from `ObjectModel` (SurrealDB base class with table_name and save/load).

## Component Catalog

### SpeakerProfile
- Validates 1-4 speakers with required fields: name, voice_id, backstory, personality
- Stores TTS provider/model (e.g., "elevenlabs", "openai")
- `get_by_name()` async query by profile name
- Raises ValueError on invalid speaker counts or missing fields

### EpisodeProfile
- Configures outline/transcript generation: provider, model, num_segments (3-20 validated)
- References speaker_config by name
- Stores default_briefing template for episode generation
- `get_by_name()` async query

### PodcastEpisode
- Stores episode_profile and speaker_profile as dicts (snapshots of config at generation time)
- Optional audio_file path, transcript/outline dicts
- **Job tracking**: command field links to surreal-commands RecordID
- `get_job_status()` fetches async job status via surreal-commands library
- `_prepare_save_data()` ensures command field is always RecordID format for database

## Common Patterns

- **Profile snapshots**: episode_profile and speaker_profile stored as dicts to freeze config at generation time
- **Field validation**: Pydantic validators enforce constraints (segment count, speaker count, required fields)
- **Async database access**: `get_by_name()` queries via repo_query
- **Job tracking**: command field delegates to surreal-commands; get_job_status() returns "unknown" on failure
- **Record ID handling**: ensure_record_id() converts string to RecordID before save

## Key Dependencies

- `pydantic`: Field validators, ObjectModel inheritance
- `surrealdb`: RecordID type for job references
- `open_notebook.database.repository`: repo_query, ensure_record_id
- `open_notebook.domain.base`: ObjectModel base class
- `surreal_commands` (optional): get_command_status() for job status

## Important Quirks & Gotchas

- **Snapshot approach**: Episode/speaker profiles stored as dicts (not references), so profile updates don't retroactively affect past episodes
- **Job status resilience**: get_job_status() catches all exceptions and returns "unknown" (no error propagation)
- **validate_speakers executes late**: Validators run at instantiation; bulk inserts may not trigger full validation
- **RecordID coercion**: ensure_record_id() handles both string and RecordID inputs; command field parsed during deserialization
- **No cascade delete**: Removing a profile doesn't cascade to episodes using it

## How to Extend

1. **Add new speaker field**: Add to required_fields list in validate_speakers()
2. **Add episode config field**: Validate in EpisodeProfile, update briefing generation code
3. **Add job metadata**: Extend PodcastEpisode with new fields (e.g., progress tracking)
4. **Change job provider**: Replace surreal-commands with alternative job queue library; update get_job_status()
