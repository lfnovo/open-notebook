# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Open Notebook is an open-source, privacy-focused alternative to Google's Notebook LM. It's a research assistant that allows users to manage research, generate AI-assisted notes, and interact with content through Streamlit UI and REST API, backed by SurrealDB.

## Development Commands

### Environment Setup
```bash
# Copy environment templates
cp .env.example .env
cp .env.example docker.env

# Install dependencies
uv sync
uv pip install python-magic
```

### Running the Application
```bash
# Start SurrealDB (required)
make database
# or: docker compose up -d surrealdb

# Start API backend (port 5055)
make api
# or: uv run run_api.py
# or: uv run --env-file .env uvicorn api.main:app --host 0.0.0.0 --port 5055

# Start Streamlit UI (port 8502)
make run
# or: uv run --env-file .env streamlit run app_home.py
```

### Code Quality
```bash
# Run linter with auto-fix
make ruff
# or: ruff check . --fix

# Run type checking
make lint
# or: uv run python -m mypy .
```

### Docker Commands
```bash
# Full stack deployment
docker compose --profile multi up

# Build multi-platform image
make docker-build

# Release with version tag
make docker-release
```

## Architecture Overview

### Three-Layer Architecture
1. **Frontend**: Streamlit UI (`app_home.py` and `/pages/`)
2. **API**: FastAPI backend (`/api/`) on port 5055
3. **Database**: SurrealDB graph database

### Key Directories
- `/open_notebook/domain/`: Domain models (notebook, models, transformation)
- `/open_notebook/graphs/`: LangGraph processing (chat, ask, source, transformation)
- `/open_notebook/database/`: SurrealDB repository pattern
- `/api/`: REST API endpoints
- `/pages/`: Streamlit UI pages
- `/migrations/`: Database migrations

### Data Storage
- `/data/uploads/`: User-uploaded files
- `/data/podcasts/`: Generated podcasts
- `/data/sqlite-db/`: LangGraph checkpoints
- `/surreal_data/`: SurrealDB files

## AI Provider Integration

The project uses the Esperanto library for multi-provider AI support:
- Language models: OpenAI, Anthropic, Google, Groq, Ollama, Mistral, DeepSeek, xAI, OpenRouter
- Embeddings: OpenAI, Google, Ollama, Mistral, Voyage
- Speech: OpenAI, Groq, ElevenLabs, Google TTS

Model configuration is centralized through `ModelManager` class in `/open_notebook/domain/models.py`.

## Database Operations

Uses SurrealDB with async operations:
```python
# Create record
await repo_create(table: str, data: dict)

# Upsert (merge) record
await repo_upsert(table: str, record_id: Union[str, RecordID], data: dict)

# Query
await repo_query("SELECT * FROM table WHERE field = $value", {"value": "example"})

# Delete
await repo_delete(record_id)
```

### Database Migrations

Database schema migrations run **automatically** when the API starts up. The migration system:
- Uses `AsyncMigrationManager` from `/open_notebook/database/async_migrate.py`
- Runs in the FastAPI `lifespan` event handler in `/api/main.py`
- Checks current database version against available migrations in `/migrations/`
- Executes pending migrations sequentially on startup
- Tracks migration state in the `_sbl_migrations` table
- Fails fast if migrations encounter errors (preventing API startup with outdated schema)

**Important**: Database migrations are now handled by the API. The Streamlit UI migration check (`pages/stream_app/utils.py:check_migration()`) is deprecated and does nothing. Always ensure the API is running before using the React frontend or Streamlit UI.

**Troubleshooting**:
- If the API fails to start, check logs for migration errors
- Verify SurrealDB is running: `docker compose ps surrealdb`
- Check database connection settings in `.env`
- Migration files must exist in `/migrations/` directory
- For manual migration rollback, use down migration files (not automated)

## Content Processing Pipeline

1. Content ingestion (files, URLs, text) via `/open_notebook/graphs/source.py`
2. Text extraction using Content-Core library
3. Embedding generation for semantic search
4. Transformation workflows in `/open_notebook/graphs/transformation.py`

## Testing Approach

Check README or search codebase for test configuration before running tests. The project uses `uv` for all Python operations.

## API Documentation

Interactive API docs available at http://localhost:5055/docs when API is running. Comprehensive endpoints for notebooks, sources, notes, search, models, transformations, and embeddings.