# Smoke journey

The product journey the `smoke-e2e` skill executes against a running instance: notebook →
sources → chat → ask → transformation → note → podcast → search → cleanup, then the UI.

## Conventions
- Base URL for API calls: `<api_url>/api`; JSON unless a step says multipart.
- Ids look like `notebook:xxxx`, `source:xxxx`, `chat_session:xxxx`.
- Source creation is **multipart/form-data**; booleans are the strings `"true"`/`"false"`;
  `notebooks` is a JSON-array string. `embed=true` is required for embeddings to be created.
- Async work (processing, embeddings, insights, podcasts) needs the worker running
  (`make worker-start`); without it every poll times out.

## Fresh database setup
Skip when the instance already has credentials, models and defaults. A fresh database has
none, and the seeded podcast profiles have no models, so Health and the podcast steps
cannot pass without this. Order matters: models link to a credential.

- Credentials: with provider API keys in the API's environment (and
  `OPEN_NOTEBOOK_ENCRYPTION_KEY` set), POST `/api/credentials/migrate-from-env` → 200;
  `migrated` lists the providers. GET `/api/credentials` gives their ids.
- Models: POST `/api/models` `{"name": "<model>", "provider": "<provider>", "type": "<type>",
  "credential": "<credential_id>"}` once per model the journey needs: a `language` model,
  an `embedding` model and, for the podcast steps, a `text_to_speech` model. Save each `id`.
- Defaults: PUT `/api/models/defaults` with at least `default_chat_model`,
  `default_transformation_model`, `default_embedding_model` and `default_tools_model` set
  to those ids (POST `/api/models/auto-assign` fills empty slots automatically, but may pick
  a different model than the one you registered).
- Podcast profile models: GET `/api/episode-profiles` and `/api/speaker-profiles`, pick one of
  each, then PUT `/api/episode-profiles/<id>` with `outline_llm` and `transcript_llm` set to
  the language model, and PUT `/api/speaker-profiles/<id>` with `voice_model` set to the
  text-to-speech model. Both PUTs validate the full body, so send the profile as returned
  by the GET with only those fields changed. The speaker profile's voices must exist for
  the TTS provider: the seeded profiles use OpenAI voice names.

## Health
- GET `<api_url>/docs` → 200
- GET `<frontend_url>` → 200
- GET `<api_url>/api/credentials` → at least one credential
- GET `<api_url>/api/models/defaults` → `default_chat_model` and a default embedding model set
save: default_chat_model

## Phase 1: API

### Step: create notebook
request: POST /api/notebooks {"name": "Smoke Test Notebook", "description": "Automated smoke test — safe to delete"}
expect: 200; body.id present
save: notebook_id

### Step: add URL source
request: POST /api/sources (multipart) type=link, notebooks=["<notebook_id>"], url=https://en.wikipedia.org/wiki/Turing_test, async_processing=true, embed=true
expect: 200; body.id present
save: url_source_id

### Step: add text source
request: POST /api/sources (multipart) type=text, notebooks=["<notebook_id>"], title="AI Overview - Smoke Test", content="Artificial intelligence (AI) is the simulation of human intelligence processes by computer systems. These processes include learning, reasoning, and self-correction. AI applications include expert systems, natural language processing, speech recognition, and machine vision.", async_processing=true, embed=true
expect: 200; body.id present
save: text_source_id

### Step: add PDF source
request: POST /api/sources (multipart) type=upload, notebooks=["<notebook_id>"], file=@tests/fixtures/smoke-test.pdf, async_processing=true, embed=true
expect: 200; body.id present (the fixture is a one-page text PDF, so extraction needs no OCR)
save: pdf_source_id

### Step: wait for processing
request: GET /api/sources/<url_source_id>/status, /api/sources/<text_source_id>/status and /api/sources/<pdf_source_id>/status
expect: status == completed for each (failed → FAIL with the error)
timeout: 5m

### Step: verify content and embeddings
request: GET /api/sources/<text_source_id>
expect: full_text non-empty; embedded == true; embedded_chunks > 0 (if embedded is false: POST /api/embed {"item_id": "<text_source_id>", "item_type": "source", "async_processing": false}, wait 15s, re-check)

### Step: chat session
request: POST /api/chat/sessions {"notebook_id": "<notebook_id>"}
expect: 200; body.id present
save: session_id

### Step: chat context
request: POST /api/chat/context {"notebook_id": "<notebook_id>", "context_config": {}}
expect: 200; body.context has sources and notes arrays
save: context

### Step: chat message
request: POST /api/chat/execute {"session_id": "<session_id>", "message": "What are the main topics covered in the sources?", "context": <context>}
expect: 200; body.messages contains a message of type ai referencing the sources' content
timeout: 3m

### Step: ask
request: POST /api/search/ask/simple {"question": "What is the Turing test and how does it relate to AI?", "strategy_model": "<default_chat_model>", "answer_model": "<default_chat_model>", "final_answer_model": "<default_chat_model>"}
expect: 200; body.answer non-empty; body.question echoes the question (scoping to notebooks landed in #1331 — check the request model before adding a notebook field)
timeout: 3m

### Step: list transformations
request: GET /api/transformations
expect: 200; a transformation such as "Dense Summary" present
save: transformation_id

### Step: run transformation
request: POST /api/sources/<text_source_id>/insights {"transformation_id": "<transformation_id>"}
expect: 202 (the insight is generated by the worker); then GET /api/sources/<text_source_id>/insights returns at least one insight
save: insight_id
timeout: 3m

### Step: save insight as note
request: POST /api/insights/<insight_id>/save-as-note {"notebook_id": "<notebook_id>"}
expect: 200; note with non-empty content
save: note_id

### Step: podcast profiles
request: GET /api/episode-profiles and GET /api/speaker-profiles
expect: 200; at least one of each, and the chosen episode profile has `outline_llm` and
`transcript_llm` and the speaker profile has `voice_model` (on a fresh database, set them in
"Fresh database setup"); with a model missing, the podcast cannot be generated (#1400)
save: episode_profile_name, speaker_profile_name

### Step: generate podcast
request: POST /api/podcasts/generate {"notebook_id": "<notebook_id>", "episode_profile": "<episode_profile_name>", "speaker_profile": "<speaker_profile_name>", "episode_name": "Smoke Test Episode"}
expect: 200; body.job_id present (profiles are referenced by NAME, not id)
save: job_id

### Step: wait for podcast
request: GET /api/podcasts/jobs/<job_id>
expect: status == completed; result.episode_id present (the top-level episode_id may be empty)
save: episode_id
timeout: 10m

### Step: podcast audio
request: GET /api/podcasts/episodes/<episode_id>/audio
expect: 200

### Step: semantic search
request: POST /api/search {"query": "artificial intelligence", "type": "vector"}
expect: 200; body.results non-empty; at least one result from this notebook's sources (the field is `type`, not `search_type`)

### Step: delete preview
request: GET /api/notebooks/<notebook_id>/delete-preview
expect: 200

### Step: delete notebook
request: DELETE /api/notebooks/<notebook_id>?delete_exclusive_sources=true
expect: 200; GET /api/notebooks/<notebook_id> → 404; GET /api/sources/<text_source_id> → 404

### Step: delete episode
request: DELETE /api/podcasts/episodes/<episode_id>
expect: 200 (skip when no episode was created)

## Phase 2: UI
Create a fresh notebook "UI Smoke Test" with one text source via the API first (same
payloads as above), wait for processing, then:
- `<frontend_url>/notebooks` lists "UI Smoke Test"
- open "UI Smoke Test" from the list: the sources panel shows the source; console has no errors
- the source detail (open it from the list) shows the extracted content
- the chat panel sends a message (Ctrl+Enter, or Cmd+Enter on macOS) and renders an AI reply
- `<frontend_url>/search?mode=search` (or the Search tab) returns results for "Turing test"
- `<frontend_url>/podcasts` lists the smoke episode when one was generated
- after deleting the UI notebook via the API, `<frontend_url>/notebooks` no longer lists it
- SSR pages may take up to 30s on a cold dev server

## Cleanup
- DELETE `/api/notebooks/<ui_notebook_id>?delete_exclusive_sources=true` → 200
- every notebook, source, note and episode created by the journey is gone (`GET` → 404)
- nothing named "Smoke Test" remains in `/api/notebooks` or `/api/podcasts/episodes`

## Quirks
- Processing can take minutes after heavy operations; the dev server slows down.
- The frontend may run on an alternate port (`PORT=3001 npm run dev`) when 3000 belongs to
  another project — pass the real `frontend_url`.
- A dev venv may have `docling`/`crawl4ai` installed out-of-band, so `GET /api/capabilities`
  does not reflect the lean image; judge opt-in gating on the RC stack, not here.
- Unknown JSON fields are silently ignored by Pydantic: a wrong field name turns a vector
  search into a text search without an error.
- Use `localhost`, not `127.0.0.1`, in `frontend_url` with the dev server. Next blocks
  cross-origin dev resources, so from `127.0.0.1` the client never hydrates and every page
  renders blank. To use another host, add it to `NEXT_ALLOWED_DEV_ORIGINS`
  (comma-separated hostnames, no protocol or port).
- Chat sends with Ctrl+Enter (Cmd+Enter on macOS); plain Enter adds a newline.
- `/search` opens on the **Ask** tab. Select the Search tab, or open `/search?mode=search`,
  for the "returns results" check.
- Open a notebook from the list rather than building `/notebooks/<id>`: the route expects
  the full `notebook:` id, URL-encoded.

## Extended checks
Optional. They exercise paths the core journey does not, and are worth running before a
release:
- A podcast with a language model that lacks `json_schema` support (DeepSeek, for example),
  which exercises podcast-creator's JSON fallback.
- An episode profile with a non-English `language`: the transcript follows it.
- An ODT upload: processed to `completed` with non-empty `full_text`.
- A URL source on an unreachable host: fails on the first attempt with a clear error, not
  after retries.
