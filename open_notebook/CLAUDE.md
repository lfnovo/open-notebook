# Open Notebook Core Backend

The `open_notebook` module is the heart of the system: a multi-layer backend orchestrating AI-powered research workflows. It bridges domain models, asynchronous database operations, LangGraph-based content processing, and multi-provider AI model management.

## Purpose

Encapsulates the entire backend architecture:
1. **Data layer**: SurrealDB persistence with async CRUD and migrations
2. **Domain layer**: Research models (Notebook, Source, Note, etc.) with embedded relationships
3. **Workflow layer**: LangGraph state machines for content ingestion, chat, and transformations
4. **AI provisioning**: Multi-provider model management with smart fallback logic
5. **Support services**: Context building, tokenization, and utility functions

All components communicate through async/await patterns and use Pydantic for validation.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    API / Streamlit UI                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │                                     │
┌───▼────────────────────┐   ┌──────────▼────────────────┐
│    Graphs (LangGraph)   │   │   Domain Models (Data)    │
│ - source.py (ingestion) │   │ - Notebook, Source, Note  │
│ - chat.py              │   │ - ChatSession, Asset       │
│ - ask.py (search)      │   │ - SourceInsight, Embedding│
│ - transformation.py    │   │ - Transformation, Settings│
└───┬────────────────────┘   │ - EpisodeProfile, Podcast │
    │                        └──────────┬─────────────────┘
    │                                   │
    └───────────────────┬───────────────┘
                        │
    ┌───────────────────┴────────────────────┐
    │                                        │
┌───▼─────────────────┐      ┌──────────────▼──────┐
│  AI Module (Models)  │      │  Utils (Helpers)     │
│ - ModelManager       │      │ - ContextBuilder     │
│ - DefaultModels      │      │ - TokenUtils         │
│ - provision_langchain│      │ - TextUtils          │
│ - Multi-provider AI  │      │ - VersionUtils       │
└───┬─────────────────┘      └──────────┬──────────┘
    │                                   │
    └───────────────────┬───────────────┘
                        │
         ┌──────────────▼────────────────┐
         │  Database (SurrealDB)          │
         │ - repository.py (CRUD ops)     │
         │ - async_migrate.py (schema)    │
         │ - Configuration                │
         └────────────────────────────────┘
```

## Component Catalog

### Core Layers

**See dedicated CLAUDE.md files for detailed patterns and usage:**

- **`database/`**: Async repository pattern (repo_query, repo_create, repo_upsert), connection pooling, and automatic schema migrations on API startup. See `database/CLAUDE.md`.

- **`domain/`**: Core data models using Pydantic with SurrealDB persistence. Two base classes: `ObjectModel` (mutable records with auto-increment IDs and embedding) and `RecordModel` (singleton configuration). Includes search functions (text_search, vector_search). See `domain/CLAUDE.md`.

- **`graphs/`**: LangGraph state machines for async workflows. Content ingestion (source.py), conversational agents (chat.py), search synthesis (ask.py), and transformations. Uses provision_langchain_model() for smart model selection with token-aware fallback. See `graphs/CLAUDE.md`.

- **`ai/`**: Centralized AI model lifecycle via Esperanto library. ModelManager factory with intelligent fallback (large context detection, type-specific defaults, config override). Supports 8+ providers (OpenAI, Anthropic, Google, Groq, Ollama, Mistral, DeepSeek, xAI). See `ai/CLAUDE.md`.

- **`utils/`**: Cross-cutting utilities: ContextBuilder (flexible context assembly from sources/notes/insights with token budgeting), TextUtils (truncation, cleaning), TokenUtils (GPT token counting), VersionUtils (schema compatibility). See `utils/CLAUDE.md`.

- **`podcasts/`**: Podcast generation models: SpeakerProfile (TTS voice config), EpisodeProfile (generation settings), PodcastEpisode (job tracking via surreal-commands). See `podcasts/CLAUDE.md`.

### Configuration & Exceptions

- **`config.py`**: Paths for data folder, uploads, LangGraph checkpoints, and tiktoken cache. Auto-creates directories.
- **`exceptions.py`**: Hierarchy of OpenNotebookError subclasses for database, file, network, authentication, and rate-limit failures.

## Data Flow: Content Ingestion

```
User uploads file/URL
         │
         ▼
┌─────────────────────────────────────┐
│ source.py (LangGraph state machine) │
├─────────────────────────────────────┤
│ 1. content_process()                │
│    - extract_content() from file/URL│
│    - Use ContentSettings defaults    │
│    - speech_to_text model from DB   │
│                                     │
│ 2. save_source()                    │
│    - Update Source with full_text   │
│    - Preserve title if empty        │
│                                     │
│ 3. trigger_transformations()        │
│    - Parallel fan-out to each TXN   │
└────────────────┬────────────────────┘
                 │
                 ▼
         ┌──────────────┐
         │ transformation.py (parallel)
         │ - Apply prompt to source text
         │ - Generate insights
         │ - Auto-embed results
         └──────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Database Storage    │
        │ - Source.full_text  │
        │ - SourceInsight     │
        │ - Embeddings        │
        │ - (async job)       │
        └────────────────────┘
```

**Fire-and-forget embeddings**: Source.vectorize() returns command_id without awaiting; embedding happens asynchronously via surreal-commands job system.

## Data Flow: Chat & Search

```
User message in chat
         │
         ▼
┌──────────────────────────┐
│ ContextBuilder           │
│ - Select sources/notes   │
│ - Token budget limiting  │
│ - Priority weighting     │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ chat.py or ask.py (LangGraph)    │
│ - Load context from above        │
│ - provision_langchain_model()    │
│   * Auto-upgrade for large text  │
│   * Apply model_id override      │
│ - Call LLM with context          │
│ - Store message in SqliteSaver   │
└──────────┬───────────────────────┘
           │
           ▼
    ┌──────────────┐
    │ LLM Response │
    │ (persisted)  │
    └──────────────┘
```

## Key Patterns Across Layers

### Async/Await Everywhere
All database operations, model provisioning, and graph execution are async. Mix with sync code only via `asyncio.run()` or LangGraph's async bridges (see graphs/CLAUDE.md for workarounds).

### Type-Driven Dispatch
Model types (language, embedding, speech_to_text, text_to_speech) drive factory logic in ModelManager. Domain model IDs encode their type: `notebook:uuid`, `source:uuid`, `note:uuid`.

### Smart Fallback Logic
`provision_langchain_model()` auto-detects large contexts (105K+ tokens) and upgrades to dedicated large_context_model. Falls back to default_chat_model if specific type not found.

### Fire-and-Forget Jobs
Time-consuming operations (embedding, podcast generation) return command_id immediately. Caller polls surreal-commands for status; no blocking.

### Embedding on Save
Domain models with `needs_embedding()=True` auto-generate embeddings in `save()`. Search functions (text_search, vector_search) use embeddings for semantic matching.

### Relationship Management
SurrealDB graph edges link entities: Notebook→Source (has), Source→Note (artifact), Note→Source (refers_to). See `relate()` in domain/base.py.

## Integration Points

**API startup** (`api/main.py`):
- AsyncMigrationManager.run_migration_up() on lifespan startup
- Ensures schema is current before handling requests

**Streamlit UI** (`pages/stream_app/`):
- Calls domain models directly to fetch/create notebooks, sources, notes
- Invokes graphs (chat, source, ask) via async wrapper
- Relies on API for migrations (deprecated check in UI)

**Background Jobs** (`surreal_commands`):
- Source.vectorize() submits async embedding job
- PodcastEpisode.get_job_status() polls job queue
- Decouples long-running operations from request flow

## Important Quirks & Gotchas

1. **Token counting rough estimate**: Uses cl100k_base encoding; may differ 5-10% from actual model
2. **Large context threshold hard-coded**: 105,000 token limit for large_context_model upgrade (not configurable)
3. **Async loop gymnastics in graphs**: ThreadPoolExecutor workaround for LangGraph sync nodes calling async functions (fragile)
4. **DefaultModels always fresh**: get_instance() bypasses singleton cache to pick up live config changes
5. **Polymorphic model.get()**: Resolves subclass from ID prefix; fails silently if subclass not imported
6. **RecordID string inconsistency**: repo_update() accepts both "table:id" format and full RecordID
7. **Snapshot profiles**: podcast profiles stored as dicts, so config updates don't affect past episodes
8. **No connection pooling**: Each repo_* creates new connection (adequate for HTTP but inefficient for bulk)
9. **Circular import guard**: utils imports domain; domain must not import utils (breaks on import)
10. **SqliteSaver shared location**: LangGraph checkpoints from LANGGRAPH_CHECKPOINT_FILE env var; all graphs use same file

## How to Add New Feature

**New data model**:
1. Create class inheriting from `ObjectModel` with `table_name` ClassVar
2. Define Pydantic fields and validators
3. Override `needs_embedding()` if searchable
4. Add custom methods for domain logic (get_X, add_to_Y)
5. Register in domain/__init__.py exports

**New workflow**:
1. Create state machine in graphs/WORKFLOW.py using StateGraph
2. Import domain models and provision_langchain_model()
3. Define nodes as async functions taking State, returning dict
4. Compile with graph.compile()
5. Invoke from API endpoint or Streamlit page

**New AI model type**:
1. Add type string to Model class
2. Add AIFactory.create_* method in Esperanto
3. Handle in ModelManager.get_model()
4. Add DefaultModels field + getter

## Key Dependencies

- **surrealdb**: AsyncSurreal client, RecordID type
- **pydantic**: Validation, field_validator
- **langgraph**: StateGraph, Send, SqliteSaver, async/sync bridging
- **langchain_core**: Messages, OutputParser, RunnableConfig
- **esperanto**: Multi-provider AI model abstraction (OpenAI, Anthropic, Google, Groq, Ollama, etc.)
- **content-core**: File/URL content extraction
- **ai_prompter**: Jinja2 template rendering for prompts
- **surreal_commands**: Async job queue for embeddings, podcast generation
- **loguru**: Structured logging throughout
- **tiktoken**: GPT token encoding for context window estimation

## Codebase Statistics

- **Modules**: 6 core layers + support services
- **Async operations**: Database, AI provisioning, graph execution, embedding, job tracking
- **Supported AI providers**: 8+ (OpenAI, Anthropic, Google, Groq, Ollama, Mistral, DeepSeek, xAI, OpenRouter)
- **Domain models**: Notebook, Source, Note, SourceInsight, SourceEmbedding, ChatSession, Asset, Transformation, ContentSettings, EpisodeProfile, SpeakerProfile, PodcastEpisode
- **Graph workflows**: 6 (source, chat, source_chat, ask, transformation, prompt)
