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
expect: 200; body.id present — not-run when the fixture is absent (two sources are sufficient)
save: pdf_source_id

### Step: wait for processing
request: GET /api/sources/<url_source_id>/status and GET /api/sources/<text_source_id>/status
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
expect: 200; then GET /api/sources/<text_source_id>/insights returns at least one insight
save: insight_id
timeout: 3m

### Step: save insight as note
request: POST /api/insights/<insight_id>/save-as-note {"notebook_id": "<notebook_id>"}
expect: 200; note with non-empty content
save: note_id

### Step: podcast profiles
request: GET /api/episode-profiles and GET /api/speaker-profiles
expect: 200; at least one of each — not-run for the podcast steps when none is configured
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
- `<frontend_url>/notebooks/<ui_notebook_id>` shows the source in the sources panel; console has no errors
- the source detail (open it from the list) shows the extracted content
- the chat panel sends a message and renders an AI reply
- `<frontend_url>/search` returns results for "Turing test"
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
