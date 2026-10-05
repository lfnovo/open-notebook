# Architecture

A map of the codebase: the processes, where each concern lives, and how data flows. It stays short on purpose. Each subsystem has its own page with the details:

- [credentials.md](credentials.md): provider credentials, encryption, the provider registry, model provisioning
- [content-processing.md](content-processing.md): chunking, embedding, context building
- [podcasts.md](podcasts.md): episode and speaker profiles, podcast jobs
- [prompts.md](prompts.md): prompt templates and `Prompter`
- [frontend.md](frontend.md): Next.js layers and data flows
- [decisions/](decisions/README.md): why things are the way they are

## Processes

```
Browser
   │
   ▼
Next.js frontend ── :3000 in dev (`npm run dev`), :8502 in the Docker image
   │  proxies /api/* to INTERNAL_API_URL (default http://localhost:5055)
   ▼
FastAPI API ─────── :5055 (`api/main.py`)          Background worker
   │                                                (`surreal-commands-worker --import-modules commands`)
   │  submits jobs ───────────────► job queue in SurrealDB ◄──────── picks up jobs
   ▼                                                      │
SurrealDB ───────── :8000 ◄───────────────────────────────┘
```

- **Frontend** (`frontend/`): Next.js 16 App Router, React 19, TypeScript, TanStack Query, Zustand, Tailwind 4, i18next. It talks only to the API.
- **API** (`api/`): FastAPI. On startup it waits for SurrealDB and runs pending migrations. It serves CRUD, chat and Ask synchronously (chat and Ask call LangGraph directly) and hands long-running work to the worker.
- **Worker** (`commands/`): [surreal-commands](https://github.com/lfnovo/surreal-commands) reads jobs from SurrealDB and runs the functions registered with `@command`. Without it, source processing, embeddings and podcasts never run ([ADR-004](decisions/ADR-004-background-workers.md)).
- **SurrealDB** (v2): documents, graph edges, full-text (BM25) and vector search in one database ([ADR-001](decisions/ADR-001-surrealdb.md)).
- **Chat history** is not in SurrealDB: LangGraph's `SqliteSaver` keeps it in `./data/sqlite-db/checkpoints.sqlite` (`LANGGRAPH_CHECKPOINT_FILE` in `open_notebook/config.py`, a constant). Uploads go to `./data/uploads/` and podcast audio to `./data/podcasts/`.

The Docker image runs the API, worker and frontend under supervisord (`supervisord.conf`); the `-single` image also runs SurrealDB.

## Backend layout

| Path | What lives there |
|---|---|
| `api/main.py` | App setup: middleware (password auth, body-size limit, CORS), exception handlers, router registration (`prefix="/api"`), startup migrations |
| `api/routers/` | One module per resource (23 of them). Most call domain models and `repo_*` functions directly |
| `api/*_service.py` | Shared or orchestration logic: `command_service.py` (job submission), `credentials_service.py` (credential lifecycle, discovery), `podcast_service.py` |
| `api/models.py` | Pydantic request and response schemas |
| `open_notebook/domain/` | Domain models on `ObjectModel` / `RecordModel` (`base.py`): `Notebook`, `Source`, `Note`, `SourceInsight`, `ChatSession`, `Transformation`, `Credential`, settings singletons |
| `open_notebook/ai/` | `provider_registry.py` (provider metadata), `models.py` (`Model`, `DefaultModels`, `ModelManager`), `provision.py`, `key_provider.py`, `model_discovery.py`, `connection_tester.py` |
| `open_notebook/graphs/` | LangGraph workflows (below) |
| `open_notebook/podcasts/` | `EpisodeProfile`, `SpeakerProfile`, `PodcastEpisode` |
| `open_notebook/database/` | `repository.py` (`repo_query`, `repo_create`, …; one connection per call, no pool) and migrations |
| `open_notebook/utils/` | Chunking, embedding, context building, encryption, error classification, URL validation |
| `commands/` | Background commands: `process_source`, `run_transformation`, `embed_note`, `embed_insight`, `embed_source`, `create_insight`, `rebuild_embeddings`, `generate_podcast` |
| `prompts/` | Jinja templates for ask, chat, source chat, transformations and podcasts |

## Data model

Defined by the migrations in `open_notebook/database/migrations/` (read them for exact fields).

| Table | Holds |
|---|---|
| `notebook` | Name, description, `archived` flag (a filter, not a soft delete; deleting removes the record) |
| `source` | `title`, `full_text`, `asset` (file path or URL), `topics`, `command` (the processing job) |
| `source_embedding` | One chunk of a source: `source`, `order`, `content`, `embedding` |
| `source_insight` | Transformation output for a source: `source`, `insight_type`, `content`, `embedding` |
| `note` | Title, content, `note_type`, `embedding` |
| `chat_session` | Session metadata only; messages live in the SQLite checkpoint, keyed by session id |
| `transformation` | Prompt-based transformations: `name`, `title`, `prompt`, `apply_default`, optional `model_id` |
| `model` | A configured model: `provider`, `name`, `type`, optional `credential` link |
| `credential` | Provider credentials, API key encrypted ([credentials.md](credentials.md)) |
| `episode_profile`, `speaker_profile`, `episode` | Podcast configuration and generated episodes ([podcasts.md](podcasts.md)) |
| `open_notebook:*` records | Singletons: `default_models`, `default_prompts`, `content_settings` (plus legacy `provider_configs`, kept only for migration) |

Relationships are graph edges, not foreign keys:

- `reference`: source → notebook (a source can be in several notebooks)
- `artifact`: note → notebook
- `refers_to`: chat session → notebook or source

Search is two SurrealDB functions, `fn::text_search` (BM25 over titles, full text, chunks, insights and notes) and `fn::vector_search` (over the stored embeddings).

## Workflows (`open_notebook/graphs/`)

| Graph | Invoked by | Shape |
|---|---|---|
| `source.py` | `process_source` command | `content_process` (content-core extraction) → `save_source` → `transform_content` (one branch per requested transformation). Embedding is a separate `embed_source` job |
| `transformation.py` | `run_transformation` command, `POST /api/transformations/execute` | One node: apply a transformation prompt to a source |
| `chat.py` | `api/routers/chat.py` | One node, checkpointed in SQLite (notebook chat) |
| `source_chat.py` | `api/routers/source_chat.py` | One node, checkpointed in SQLite, streamed as SSE |
| `ask.py` | `POST /api/search/ask` | Search strategy → one answer per search (parallel) → final answer, streamed as SSE |
| `prompt.py` | `api/routers/notes.py` | One node: generate a note title |

Nodes are `async def`, except in the two checkpointed chat graphs, which use sync nodes with a new event loop because `SqliteSaver` is synchronous.

## How a model call happens

1. A graph node calls `provision_langchain_model(content, model_id, default_type, **kwargs)` (`open_notebook/ai/provision.py`).
2. Content over 105,000 tokens switches to the `large_context` default model. Otherwise an explicit `model_id` wins, then the default for `default_type` (`chat`, `transformation`, `tools`, …) from `DefaultModels`. No model → `ConfigurationError`, which the API returns as 422.
3. `ModelManager.get_model()` loads the `Model` record. If it links a credential, the credential's config goes straight to Esperanto's `AIFactory`; otherwise `provision_provider_keys()` fills environment variables from stored credentials ([credentials.md](credentials.md#provisioning-two-paths)).
4. The Esperanto model is converted with `.to_langchain()`. All provider calls go through [Esperanto](https://github.com/lfnovo/esperanto); nothing calls a provider SDK directly. Calls time out after `ESPERANTO_LLM_TIMEOUT` (Open Notebook sets 180 s when it's unset).
5. On failure, the node passes the exception through `classify_error()` (`open_notebook/utils/error_classifier.py`). It matches the error text (auth, rate limit, model not found, network/timeout, context length, …) and raises the matching `open_notebook.exceptions` type with a user-readable message. The API's exception handlers turn that into a status code, and the frontend shows the message.

## Background jobs

1. A router submits a job: `CommandService.submit_command_job("open_notebook", "<command>", args)`. The job is stored in SurrealDB and its id returned at once.
2. The worker runs the `@command` function. Its `retry` config decides what is retried; exceptions in `stop_on` fail the job immediately.
3. Clients poll `GET /api/commands/jobs/{job_id}`, or a resource-specific status endpoint such as `GET /api/sources/{source_id}/status`.

Example: `POST /api/sources` saves the source, submits `process_source`, and returns. The worker extracts the content, runs transformations, and submits `embed_source` if embedding was requested.

## Request path in the API

`CORSMiddleware` → `MaxBodySizeMiddleware` (rejects bodies over `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` with 413) → `PasswordAuthMiddleware` (Bearer password, if one is set) → router. Typed exceptions from anywhere below map to status codes in `api/main.py`; see [api-reference.md](api-reference.md#errors).
