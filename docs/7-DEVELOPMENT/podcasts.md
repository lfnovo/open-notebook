# Podcast Subsystem

How podcast generation is modeled and executed: the two-tier profile system, the model-registry
references, and the deliberate no-auto-retry policy.

## Two-tier profile system (`open_notebook/podcasts/models.py`)

- **SpeakerProfile** — voice configuration: a `voice_model` (`record<model>` reference for TTS)
  plus 1–4 speakers (name, voice_id, backstory, personality). Individual speakers can override
  the profile's `voice_model`.
- **EpisodeProfile** — generation settings: `outline_llm` / `transcript_llm` (`record<model>`
  references), `language` (BCP 47, e.g. `pt-BR`), segment count (3–20), briefing template. It
  references a SpeakerProfile by name.
- **PodcastEpisode** — a generated episode. Links content, profiles and the async job (`command`
  field → surreal-commands RecordID).

## Model registry references, not strings

Profile fields reference `Model` records instead of raw provider/model strings. At generation
time `_resolve_model_config(model_id)` loads the Model, resolves its linked credential (or falls
back to `provision_provider_keys()`), and returns `(provider, model_name, config)` for
podcast-creator. Legacy string fields (`tts_provider`, `outline_provider`, …) still exist as
nullable columns for migration compatibility but are **ignored at runtime**.

`migration.py` converts legacy profiles on API startup (after SQL migrations): idempotent, skips
already-migrated profiles, and auto-creates a Model record when a legacy string has no match but a
credential exists for that provider.

## Profile snapshots

`PodcastEpisode` stores `episode_profile` and `speaker_profile` as **dicts (snapshots)**, not
references. Editing a profile never retroactively changes past episodes — that's intentional.
Corollary: deleting a profile does not cascade to episodes.

## Job lifecycle and the retry policy

Generation runs as a `generate_podcast_command` job on the surreal-commands worker:

- The command resolves model configs and credentials for **all** profiles before invoking
  podcast-creator, and validates that `outline_llm`, `transcript_llm` and `voice_model` are set.
- **`max_attempts: 1` — no automatic retries.** A mid-generation retry would create duplicate
  episode records (records are created during execution). Failed episodes are marked `failed`
  with an error message; retry is explicitly user-initiated via
  `POST /podcasts/episodes/{id}/retry`.
- Status tracking: `get_job_status()` / `get_job_detail()` query surreal-commands and return
  `"unknown"` on failure rather than raising. Listing endpoints use the batched
  `get_job_details_for_commands()` so N episodes cost one status query, not N.
- TTS failures fall back to silent audio rather than failing the episode.
