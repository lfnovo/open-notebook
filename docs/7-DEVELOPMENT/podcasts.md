# Podcast Subsystem

How podcast generation is modeled and executed: the two-tier profile system, the model-registry references, and the deliberate no-auto-retry policy.

## Two-tier profile system (`open_notebook/podcasts/models.py`)

- **SpeakerProfile** — voice configuration: a `voice_model` (`record<model>` reference for TTS) plus 1–4 speakers (name, voice_id, backstory, personality). Individual speakers can override the profile's `voice_model`.
- **EpisodeProfile** — generation settings: `outline_llm` / `transcript_llm` (`record<model>` references), `language` (BCP 47, e.g. `pt-BR`), segment count (3–20), briefing template. It references a SpeakerProfile by name.
- **PodcastEpisode** — a generated episode. Links content, profiles and the async job (`command` field → surreal-commands RecordID).

## Model registry references, not strings

Profile fields reference `Model` records instead of raw provider/model strings. At generation time `_resolve_model_config(model_id)` loads the Model, resolves its linked credential (or falls back to `provision_provider_keys()`), and returns `(provider, model_name, config)` for podcast-creator.

The legacy string fields (`tts_provider`, `outline_provider`, …) that predated the registry were dropped by SQL migration 22 (#1107). The migration best-effort maps any still-unresolved profile to an existing `model` record (provider + name + type) before dropping the columns; profiles with no matching record stay unresolved — the UI already flags them as needing model selection and the user re-picks once. The old startup data migration (`open_notebook/podcasts/migration.py`) is gone.

## Profile snapshots

`PodcastEpisode` stores `episode_profile` and `speaker_profile` as **dicts (snapshots)**, not references. Editing a profile never retroactively changes past episodes — that's intentional. Corollary: deleting a profile does not cascade to episodes.

## Voice pre-flight

Audio is generated last, so a `voice_id` the TTS model doesn't accept fails only after the full transcript has been generated and paid for — and the provider message rarely names the voice (Gemini's 3.x TTS preview answers an unknown voice with `404 Requested entity was not found.`). `SpeakerProfile.validate_voices()` runs before generation and checks each speaker's voice (honoring per-speaker `voice_model` overrides) against esperanto's `available_voices` for the resolved model.

A blank voice always fails (no provider can speak it). Otherwise it fails the run **only** for a voice another provider's catalogue claims — the case of the migration-7 profiles, seeded with OpenAI voices (`nova`, `echo`, `shimmer`, …), against a Gemini voice model. A voice no catalogue knows is logged and allowed through, because those catalogues go stale (esperanto's OpenAI list predates `ash`), and an unavailable catalogue never blocks generation. `VoiceCatalogueCache` memoizes each lookup for the duration of one pass — HTTP-backed providers (ElevenLabs, OpenRouter) otherwise pay a request per speaker, each able to run to the 10s timeout. The key is `(provider, model_name, digest of the credential config)`: speakers override `voice_model` individually, and two `model` records sharing a provider and name can still point at different accounts or endpoints, whose voice libraries differ. Only successful lookups are memoized — a failure and an absent catalogue are indistinguishable here, so caching the first failure would switch validation off for the rest of the profile after one flaky request — and a failing catalogue is retried at most `MAX_CATALOGUE_ATTEMPTS` times per pass, so a dead endpoint can't charge the 10s timeout once per speaker.

## Job lifecycle and the retry policy

Generation runs as a `generate_podcast_command` job on the surreal-commands worker:

- The command resolves model configs and credentials for **all** profiles before invoking podcast-creator, and validates that `outline_llm`, `transcript_llm` and `voice_model` are set.
- **`max_attempts: 1` — no automatic retries.** A mid-generation retry would create duplicate episode records (records are created during execution). Failed episodes are marked `failed` with an error message; retry is explicitly user-initiated via `POST /podcasts/episodes/{id}/retry`.
- Status tracking: `get_job_status()` / `get_job_detail()` query surreal-commands and return `"unknown"` on failure rather than raising. Listing endpoints use the batched `get_job_details_for_commands()` so N episodes cost one status query, not N.
- TTS failures fall back to silent audio rather than failing the episode.
