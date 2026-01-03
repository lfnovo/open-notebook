# API Module

FastAPI-based REST backend exposing services for notebooks, sources, notes, chat, podcasts, and AI model management.

## Purpose

FastAPI application serving three architectural layers: routes (HTTP endpoints), services (business logic), and models (request/response schemas). Integrates LangGraph workflows (chat, ask, source_chat), SurrealDB persistence, and AI providers via Esperanto.

## Architecture Overview

**Three layers**:
1. **Routes** (`routers/*`): HTTP endpoints mapping to services
2. **Services** (`*_service.py`): Business logic orchestrating domain models, database, graphs, AI providers
3. **Models** (`models.py`): Pydantic request/response schemas with validation

**Startup flow**:
- Load .env environment variables
- Initialize CORS middleware + password auth middleware
- Run database migrations via AsyncMigrationManager on lifespan startup
- Register all routers

**Key services**:
- `chat_service.py`: Invokes chat graph with messages, context
- `podcast_service.py`: Orchestrates outline + transcript generation
- `sources_service.py`: Content ingestion, vectorization, metadata
- `notes_service.py`: Note creation, linking to sources/insights
- `transformations_service.py`: Applies transformations to content
- `models_service.py`: Manages AI provider/model configuration
- `episode_profiles_service.py`: Manages podcast speaker/episode profiles

## Component Catalog

### Main Application
- **main.py**: FastAPI app initialization, CORS setup, auth middleware, lifespan event, router registration
- **Lifespan handler**: Runs AsyncMigrationManager on startup (database schema migration)
- **Auth middleware**: PasswordAuthMiddleware protects endpoints (password-based access control)

### Services (Business Logic)
- **chat_service.py**: Invokes chat.py graph; handles message history via SqliteSaver
- **podcast_service.py**: Generates outline (outline.jinja), then transcript (transcript.jinja) for episodes
- **sources_service.py**: Ingests files/URLs (content_core), extracts text, vectorizes, saves to SurrealDB
- **transformations_service.py**: Applies transformations via transformation.py graph
- **models_service.py**: Manages ModelManager config (AI provider overrides)
- **episode_profiles_service.py**: CRUD for EpisodeProfile and SpeakerProfile models
- **insights_service.py**: Generates and retrieves source insights
- **notes_service.py**: Creates notes linked to sources/insights

### Models (Schemas)
- **models.py**: Pydantic schemas for request/response validation
- Request bodies: ChatRequest, CreateNoteRequest, PodcastGenerationRequest, etc.
- Response bodies: ChatResponse, NoteResponse, PodcastResponse, etc.
- Custom validators for enum fields, file paths, model references

### Routers
- **routers/chat.py**: POST /chat
- **routers/source_chat.py**: POST /source/{source_id}/chat
- **routers/podcasts.py**: POST /podcasts, GET /podcasts/{id}, etc.
- **routers/notes.py**: POST /notes, GET /notes/{id}
- **routers/sources.py**: POST /sources, GET /sources/{id}, DELETE /sources/{id}
- **routers/models.py**: GET /models, POST /models/config
- **routers/transformations.py**: POST /transformations
- **routers/insights.py**: GET /sources/{source_id}/insights
- **routers/auth.py**: POST /auth/password (password-based auth)
- **routers/commands.py**: GET /commands/{command_id} (job status tracking)

## Common Patterns

- **Service injection via FastAPI**: Routers import services directly; no DI framework
- **Async/await throughout**: All DB queries, graph invocations, AI calls are async
- **SurrealDB transactions**: Services use repo_query, repo_create, repo_upsert from database layer
- **Config override pattern**: Models/config override via models_service passed to graph.ainvoke(config=...)
- **Error handling**: Services catch exceptions and return HTTP status codes (400 Bad Request, 404 Not Found, 500 Internal Server Error)
- **Logging**: loguru logger in main.py; services expected to log key operations
- **Response normalization**: All responses follow standard schema (data + metadata structure)

## Key Dependencies

- `fastapi`: FastAPI app, routers, HTTPException
- `pydantic`: Validation models with Field, field_validator
- `open_notebook.graphs`: chat, ask, source_chat, source, transformation graphs
- `open_notebook.database`: SurrealDB repository functions (repo_query, repo_create, repo_upsert)
- `open_notebook.domain`: Notebook, Source, Note, SourceInsight models
- `open_notebook.ai.provision`: provision_langchain_model() factory
- `ai_prompter`: Prompter for template rendering
- `content_core`: extract_content() for file/URL processing
- `esperanto`: AI provider client library (LLM, embeddings, TTS)
- `surreal_commands`: Job queue for async operations (podcast generation)
- `loguru`: Structured logging

## Important Quirks & Gotchas

- **Migration auto-run**: Database schema migrations run on every API startup (via lifespan); no manual migration steps
- **PasswordAuthMiddleware is basic**: Uses simple password check; production deployments should replace with OAuth/JWT
- **No request rate limiting**: No built-in rate limiting; deployment must add via proxy/middleware
- **Service state is stateless**: Services don't cache results; each request re-queries database/AI models
- **Graph invocation is blocking**: chat/podcast workflows may take minutes; no timeout handling in services
- **Command job fire-and-forget**: podcast_service.py submits jobs but doesn't wait (async job queue pattern)
- **Model override scoping**: Model config override via RunnableConfig is per-request only (not persistent)
- **CORS open by default**: main.py CORS settings allow all origins (restrict before production)
- **No OpenAPI security scheme**: API docs available without auth (disable before production)
- **Services don't validate user permission**: All endpoints trust authentication layer; no per-notebook permission checks

## How to Add New Endpoint

1. Create router file in `routers/` (e.g., `routers/new_feature.py`)
2. Import router into `main.py` and register: `app.include_router(new_feature.router, tags=["new_feature"])`
3. Create service in `new_feature_service.py` with business logic
4. Define request/response schemas in `models.py` (or create `new_feature_models.py`)
5. Implement router functions calling service methods
6. Test with `uv run uvicorn api.main:app --host 0.0.0.0 --port 5055`

## Testing Patterns

- **Interactive docs**: http://localhost:5055/docs (Swagger UI)
- **Direct service tests**: Import service, call methods directly with test data
- **Mock graphs**: Replace graph.ainvoke() with mock for testing service logic
- **Database: Use test database** (separate SurrealDB instance or mock repo_query)
