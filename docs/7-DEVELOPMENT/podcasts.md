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

## Prompt templates shadow podcast-creator's

`prompts/podcast/{outline,transcript}.jinja` are **not** just this app's copies of the library's prompts — they replace them. podcast-creator resolves templates as inline config → `prompts_dir` config → `Path.cwd()/prompts/podcast/<name>.jinja` → its own package resources, and this app configures only profiles, so the working directory wins and the bundled prompts are never read.

Consequences to keep in mind when touching these files:

- Library prompt improvements are invisible here. The `{{ language }}` block was lost exactly this way, which made `EpisodeProfile.language` silently do nothing (#1238). `tests/test_podcast_prompt_templates.py` fails when a variable the bundled template uses is missing from the app's copy.
- The variables available are whatever `podcast_creator.nodes` passes: the transcript template gets `speaker_names`, the outline template does **not**.
- Never show the model a fill-in skeleton it can return verbatim. Placeholders (`...`, `[like this]`, `<like this>`) are banned explicitly — a copied `"speaker": "..."` used to abort the whole episode on podcast-creator's speaker-name validation, discarding the segments already generated. The two examples differ: the **transcript** one carries the episode's real speaker names (serialized with `tojson`, so a name containing a quote can't break the example) plus fully written sample dialogue, while the **outline** one has fixed sample segment values — `speaker_names` isn't passed to that template and it has no dialogue. Both are labelled as two-entry excerpts and restate the required `turns` / `num_segments` count, so a copy is valid output without reading as a complete answer. **A sample can only be hard-coded English, so none is rendered at all when the episode profile sets a `language`** — the structure is stated in prose there, and the schema still reaches the model through `format_instructions`.

## Job lifecycle and the retry policy

Generation runs as a `generate_podcast_command` job on the surreal-commands worker:

- The command resolves model configs and credentials for **all** profiles before invoking podcast-creator, and validates that `outline_llm`, `transcript_llm` and `voice_model` are set.
- **`max_attempts: 1` — no automatic retries.** A mid-generation retry would create duplicate episode records (records are created during execution). Failed episodes are marked `failed` with an error message; retry is explicitly user-initiated via `POST /podcasts/episodes/{id}/retry`.
- Status tracking: `get_job_status()` / `get_job_detail()` query surreal-commands and return `"unknown"` on failure rather than raising. Listing endpoints use the batched `get_job_details_for_commands()` so N episodes cost one status query, not N.
- TTS failures fall back to silent audio rather than failing the episode.
