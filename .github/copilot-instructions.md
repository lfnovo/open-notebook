# Open Notebook AI Agent Instructions

## Project Overview
Open Notebook is a self-hosted, privacy-focused alternative to Google Notebook LM. Multi-provider AI research assistant with podcast generation, Anki card creation, and vector search. **Architecture**: FastAPI backend + Next.js React frontend + SurrealDB + command workers.

## Core Architecture

### Three-Process System
1. **API Process** (`api/main.py`): FastAPI server on port 5055 with REST endpoints + router modules
2. **Worker Process** (`surreal-commands-worker`): Background command execution via `surreal-commands` library
3. **Frontend Process** (`frontend/`): Next.js 15 React app on port 8502 (dev: 3000)

All orchestrated by `supervisord.conf` in Docker. Dev: `docker-compose.dev.yml` with hot reload.

### Data Flow Pattern
1. **Synchronous UI Response**: API creates placeholder records immediately → user sees instant feedback
2. **Async Processing**: API dispatches `@command` decorated functions to worker → progress tracked via command status
3. **Source Processing Pipeline**: `process_source` command → content extraction (via `content-core`) → transformations (LangGraph) → embeddings → save

### Database Architecture (SurrealDB)
- **Connection**: `open_notebook/database/repository.py` provides `repo_query`, `repo_create`, `repo_update` helpers
- **Migrations**: Auto-run on startup via `AsyncMigrationManager` (numbered files: `migrations/1.surrealql`, `2.surrealql`, etc.)
- **Domain Models**: `open_notebook/domain/` with `Source`, `Note`, `Notebook` using repository pattern
- **Graph Relations**: SurrealDB RELATE for notebook→source, source→chunks, etc.

## Development Commands

```bash
# Full dev environment (backend + services)
docker-compose -f docker-compose.dev.yml up -d
# Logs: docker-compose -f docker-compose.dev.yml logs -f open_notebook

# Restart after config changes
docker-compose -f docker-compose.dev.yml restart open_notebook

# Hybrid dev (best hot reload): backend in Docker, frontend native
docker-compose -f docker-compose.dev.yml up surrealdb ollama whisper piper
cd frontend && npm run dev  # Port 3000

# API standalone (requires services running)
uv run uvicorn api.main:app --host 0.0.0.0 --port 5055 --reload
```

**Hot Reload Note**: Docker on Windows/macOS doesn't trigger Next.js Fast Refresh due to file watch limitations. Manual browser refresh (Ctrl+R) required. Use native `npm run dev` for full hot reload.

## Service Layer Pattern

Services in `api/` use **API client pattern** (not direct DB access) to match frontend:

```python
# api/sources_service.py example
class SourcesService:
    def get_all_sources(self, notebook_id: Optional[str] = None) -> List[SourceWithMetadata]:
        sources_data = api_client.get_sources(notebook_id=notebook_id)
        # Transform API response to domain objects
```

Always use `api_client` in services for consistency with frontend behavior.

## Command System (Background Tasks)

Uses `surreal-commands` library for async execution. Commands in `commands/` folder:

```python
from surreal_commands import command, CommandInput, CommandOutput

class ProcessInput(CommandInput):
    source_id: str
    embed: bool

@command("process_source", app="open_notebook", retry={"max_attempts": 2})
async def process_source_command(input: ProcessInput) -> ProcessOutput:
    # Long-running processing here
    pass
```

**Dispatch from API**: `await submit_command("process_source", input_data)` returns `command_id` for status tracking.

## LangGraph Processing Graphs

Located in `open_notebook/graphs/`:
- **`source.py`**: Content extraction → transformations → embedding pipeline
- **`transformation.py`**: Individual transformation execution with model selection
- **`chat.py`**: Conversational AI with context retrieval
- **Podcast generation**: Uses `podcast-creator` library with multi-speaker profiles

State management uses TypedDict for LangGraph compatibility.

## Transformations System

**Definition**: JSON in `transformations.json` with prompt templates (shipped with defaults)
**Processing**: User selects transformations → applied via LangGraph → results stored as insights
**Custom Transformations**: Users can add via UI → stored in database → merged with defaults

Example: "Dense Summary", "Key Insights", "Anki Cards - Dutch B1"

## Anki Integration

**Card Generation**: `commands/anki_commands.py` - `generate_anki_cards` command
**CEFR Classification**: Multi-model voting system in `api/cefr_service.py` for language level detection
**Audio**: TTS via Piper with custom voice profiles
**Export**: Generates `.apkg` files with media

## Multi-Provider AI (Esperanto)

**Models Config**: Stored in DB via `api/models_service.py` → `Model` domain objects
**Providers**: 16+ supported (OpenAI, Anthropic, Ollama, Gemini, LM Studio, etc.)
**Selection**: Per-feature model selection (chat, embeddings, TTS) via `ModelManager.get_defaults()`

Default for embeddings: `mxbai-embed-large` (Ollama), recommended for speed/quality.

## Frontend Architecture

**Framework**: Next.js 15 with App Router + React Server Components
**State**: Zustand stores in `frontend/src/stores/` (notebooks, sources, chat)
**API Client**: `frontend/src/lib/api/` with typed axios calls
**UI Components**: Shadcn/ui (Radix UI primitives) in `frontend/src/components/`
**Key Layout**: Three-panel design - Sources | Notes | Chat (configurable context levels)

## Testing & Validation

**Python**: Run `pytest` in root (test files in `tests/`)
**Type Checking**: `uv run python -m mypy .`
**Linting**: `ruff check . --fix`
**Frontend**: `cd frontend && npm run lint`

## Critical Conventions

1. **Async First**: All DB operations are `async def` with `await`
2. **RecordID Handling**: Use `parse_record_ids()` on SurrealDB results to stringify IDs
3. **Error Logging**: Use `loguru` logger (pre-configured) - `logger.error()` for retriable, `logger.exception()` for stack traces
4. **Pydantic Models**: `api/models.py` for API contracts (separate from domain models)
5. **Environment Variables**: Load via `dotenv` - see `docker.env` for required vars
6. **Migration Pattern**: Numbered SQL files with matching `_down.surrealql` for rollbacks

## Documentation Reference

- `DEVELOPMENT.md`: Setup workflows and hot reload details
- `DESIGN_PRINCIPLES.md`: Privacy-first, API-first, multi-provider philosophy
- `docs/`: Full feature documentation (check `docs/index.md` for overview)
- `MIGRATION.md`: Upgrade guides for breaking changes

## Common Tasks

**Add API Endpoint**: 
1. Create router in `api/routers/` 
2. Register in `api/main.py` 
3. Define models in `api/models.py`
4. Import router in main.py includes

**Add Background Task**: 
1. Create `@command` in `commands/`
2. Import in `commands/__init__.py`
3. Dispatch via `submit_command()` from API

**Add Transformation**: 
1. Add prompt to `transformations.json` OR create via UI
2. System auto-loads on startup

**Debug Worker**: Check `docker logs open-notebook-open_notebook-1 --tail=100` for worker process logs (supervisord shows all three processes)
