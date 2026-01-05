# Open Notebook Architecture

## High-Level Overview

Open Notebook follows a three-tier architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│  Your Browser                                           │
│  Access: http://your-server-ip:8502                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │   Port 8502   │  ← Next.js Frontend (what you see)
         │   Frontend    │    Also proxies API requests internally!
         └───────┬───────┘
                 │ proxies /api/* requests ↓
                 ▼
         ┌───────────────┐
         │   Port 5055   │  ← FastAPI Backend (handles requests)
         │     API       │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │   SurrealDB   │  ← Database (internal, auto-configured)
         │   (Port 8000) │
         └───────────────┘
```

**Key Points:**
- **v1.1+**: Next.js automatically proxies `/api/*` requests to the backend, simplifying reverse proxy setup
- Your browser loads the frontend from port 8502
- The frontend needs to know where to find the API - when accessing remotely, set: `API_URL=http://your-server-ip:5055`
- **Behind reverse proxy?** You only need to proxy to port 8502 now! See [Reverse Proxy Configuration](../5-CONFIGURATION/reverse-proxy.md)

---

## Detailed Architecture

Open Notebook is built on a **three-tier, async-first architecture** designed for scalability, modularity, and multi-provider AI flexibility. The system separates concerns across frontend, API, and database layers, with LangGraph powering intelligent workflows and Esperanto enabling seamless integration with 8+ AI providers.

**Core Philosophy**:
- Privacy-first: Users control their data and AI provider choice
- Async/await throughout: Non-blocking operations for responsive UX
- Domain-Driven Design: Clear separation between domain models, repositories, and orchestrators
- Multi-provider flexibility: Swap AI providers without changing application code
- Self-hosted capable: All components deployable in isolated environments

---

## Three-Tier Architecture

### Layer 1: Frontend (React/Next.js @ port 3000)

**Purpose**: Responsive, interactive user interface for research, notes, chat, and podcast management.

**Technology Stack**:
- **Framework**: Next.js 15 with React 19
- **Language**: TypeScript with strict type checking
- **State Management**: Zustand (lightweight store) + TanStack Query (server state)
- **Styling**: Tailwind CSS + Shadcn/ui component library
- **Build Tool**: Webpack (bundled via Next.js)

**Key Responsibilities**:
- Render notebooks, sources, notes, chat sessions, and podcasts
- Handle user interactions (create, read, update, delete operations)
- Manage complex UI state (modals, file uploads, real-time search)
- Stream responses from API (chat, podcast generation)
- Display embeddings, vector search results, and insights

**Communication Pattern**:
- All data fetched via REST API (async requests to port 5055)
- Configured base URL: `http://localhost:5055` (dev) or environment-specific (prod)
- TanStack Query handles caching, refetching, and data synchronization
- Zustand stores global state (user, notebooks, selected context)
- CORS enabled on API side for cross-origin requests

**Component Architecture**:
- `/src/app/`: Next.js App Router (pages, layouts)
- `/src/components/`: Reusable React components (buttons, forms, cards)
- `/src/hooks/`: Custom hooks (useNotebook, useChat, useSearch)
- `/src/lib/`: Utility functions, API clients, validators
- `/src/styles/`: Global CSS, Tailwind config

---

### Layer 2: API (FastAPI @ port 5055)

**Purpose**: RESTful backend exposing operations on notebooks, sources, notes, chat sessions, and AI models.

**Technology Stack**:
- **Framework**: FastAPI 0.104+ (async Python web framework)
- **Language**: Python 3.11+
- **Validation**: Pydantic v2 (request/response schemas)
- **Logging**: Loguru (structured JSON logging)
- **Testing**: Pytest (unit and integration tests)

**Architecture**:
```
FastAPI App (main.py)
  ├── Routers (HTTP endpoints)
  │   ├── routers/notebooks.py (CRUD operations)
  │   ├── routers/sources.py (content ingestion, upload)
  │   ├── routers/notes.py (note management)
  │   ├── routers/chat.py (conversation sessions)
  │   ├── routers/search.py (full-text + vector search)
  │   ├── routers/transformations.py (custom transformations)
  │   ├── routers/models.py (AI model configuration)
  │   └── routers/*.py (11 additional routers)
  │
  ├── Services (business logic)
  │   ├── *_service.py (orchestration, graph invocation)
  │   ├── command_service.py (async job submission)
  │   └── middleware (auth, logging)
  │
  ├── Models (Pydantic schemas)
  │   └── models.py (validation, serialization)
  │
  └── Lifespan (startup/shutdown)
      └── AsyncMigrationManager (database schema migrations)
```

**Key Responsibilities**:
1. **HTTP Interface**: Accept REST requests, validate, return JSON responses
2. **Business Logic**: Orchestrate domain models, repository operations, and workflows
3. **Async Job Queue**: Submit long-running tasks (podcast generation, source processing)
4. **Database Migrations**: Run schema updates on startup
5. **Error Handling**: Catch exceptions, return appropriate HTTP status codes
6. **Logging**: Track operations for debugging and monitoring

**Startup Flow**:
1. Load `.env` environment variables
2. Initialize FastAPI app with CORS + auth middleware
3. Run AsyncMigrationManager (creates/updates database schema)
4. Register all routers (20+ endpoints)
5. Server ready on port 5055

**Request-Response Cycle**:
```
HTTP Request → Router → Service → Domain/Repository → SurrealDB
                                       ↓
                                  LangGraph (optional)
                                       ↓
Response ← Pydantic serialization ← Service ← Result
```

---

### Layer 3: Database (SurrealDB @ port 8000)

**Purpose**: Graph database with built-in vector embeddings, semantic search, and relationship management.

**Technology Stack**:
- **Database**: SurrealDB (multi-model, ACID transactions)
- **Query Language**: SurrealQL (SQL-like syntax with graph operations)
- **Async Driver**: Async Rust client for Python
- **Migrations**: Manual `.surql` files in `/migrations/` (auto-run on API startup)

**Core Tables**:

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `notebook` | Research project container | id, name, description, archived, created, updated |
| `source` | Content item (PDF, URL, text) | id, title, full_text, topics, asset, created, updated |
| `source_embedding` | Vector embeddings for semantic search | id, source, embedding, chunk_text, chunk_index |
| `note` | User-created research notes | id, title, content, note_type (human/ai), created, updated |
| `chat_session` | Conversation session | id, notebook_id, title, messages (JSON), created, updated |
| `transformation` | Custom transformation rules | id, name, description, prompt, created, updated |
| `source_insight` | Transformation output | id, source_id, insight_type, content, created, updated |
| `reference` | Relationship: source → notebook | out (source), in (notebook) |
| `artifact` | Relationship: note → notebook | out (note), in (notebook) |

**Relationship Graph**:
```
Notebook
  ↓ (referenced_by)
Source
  ├→ SourceEmbedding (1:many for chunked text)
  ├→ SourceInsight (1:many for transformation outputs)
  └→ Note (via artifact relationship)
    ├→ Embedding (semantic search)
    └→ Topics (tags)

ChatSession
  ├→ Notebook
  └→ Messages (stored as JSON array)
```

**Vector Search Capability**:
- Embeddings stored natively in SurrealDB
- Full-text search on `source.full_text` and `note.content`
- Cosine similarity search on embedding vectors
- Semantic search integrates with search endpoint

**Connection Management**:
- Async connection pooling (configurable size)
- Transaction support for multi-record operations
- Schema auto-validation via migrations
- Query timeout protection (prevent infinite queries)

---

## Tech Stack Rationale

### Why Python + FastAPI?

**Python**:
- Rich AI/ML ecosystem (LangChain, LangGraph, transformers, scikit-learn)
- Rapid prototyping and deployment
- Extensive async support (asyncio, async/await)
- Strong type hints (Pydantic, mypy)

**FastAPI**:
- Modern, async-first framework
- Automatic OpenAPI documentation (Swagger UI @ /docs)
- Built-in request validation (Pydantic)
- Excellent performance (benchmarked near C/Rust speeds)
- Easy middleware/dependency injection

### Why Next.js + React + TypeScript?

**Next.js**:
- Full-stack React framework with SSR/SSG
- File-based routing (intuitive project structure)
- Built-in API routes (optional backend co-location)
- Optimized image/code splitting
- Easy deployment (Vercel, Docker, self-hosted)

**React 19**:
- Component-based UI (reusable, testable)
- Excellent tooling and community
- Client-side state management (Zustand)
- Server-side state sync (TanStack Query)

**TypeScript**:
- Type safety catches errors at compile time
- Better IDE autocomplete and refactoring
- Documentation via types (self-documenting code)
- Easier onboarding for new contributors

### Why SurrealDB?

**SurrealDB**:
- Native graph database (relationships are first-class)
- Built-in vector embeddings (no separate vector DB)
- ACID transactions (data consistency)
- Multi-model (relational + document + graph)
- Full-text search + semantic search in one query
- Self-hosted (unlike managed Pinecone/Weaviate)
- Flexible SurrealQL (SQL-like syntax)

**Alternative Considered**: PostgreSQL + pgvector (more mature but separate extensions)

### Why Esperanto for AI Providers?

**Esperanto Library**:
- Unified interface to 8+ LLM providers (OpenAI, Anthropic, Google, Groq, Ollama, Mistral, DeepSeek, xAI)
- Multi-provider embeddings (OpenAI, Google, Ollama, Mistral, Voyage)
- TTS/STT integration (OpenAI, Groq, ElevenLabs, Google)
- Smart provider selection (fallback logic, cost optimization)
- Per-request model override support
- Local Ollama support (completely self-hosted option)

**Alternative Considered**: LangChain's provider abstraction (more verbose, less flexible)

---

## LangGraph Workflows

LangGraph is a state machine library that orchestrates multi-step AI workflows. Open Notebook uses five core workflows:

### 1. **Source Processing Workflow** (`open_notebook/graphs/source.py`)

**Purpose**: Ingest content (PDF, URL, text) and prepare for search/insights.

**Flow**:
```
Input (file/URL/text)
  ↓
Extract Content (content-core library)
  ↓
Clean & tokenize text
  ↓
Generate Embeddings (Esperanto)
  ↓
Create SourceEmbedding records (chunked + indexed)
  ↓
Extract Topics (LLM summarization)
  ↓
Save to SurrealDB
  ↓
Output (Source record with embeddings)
```

**State Dict**:
```python
{
  "content_state": {"file_path" | "url" | "content": str},
  "source_id": str,
  "full_text": str,
  "embeddings": List[Dict],
  "topics": List[str],
  "notebook_ids": List[str],
}
```

**Invoked By**: Sources API (`POST /sources`)

---

### 2. **Chat Workflow** (`open_notebook/graphs/chat.py`)

**Purpose**: Conduct multi-turn conversations with AI model, referencing notebook context.

**Flow**:
```
User Message
  ↓
Build Context (selected sources/notes)
  ↓
Add Message to Session
  ↓
Create Chat Prompt (system + history + context)
  ↓
Call LLM (via Esperanto)
  ↓
Stream Response
  ↓
Save AI Message to ChatSession
  ↓
Output (complete message)
```

**State Dict**:
```python
{
  "session_id": str,
  "messages": List[BaseMessage],
  "context": Dict[str, Any],  # sources, notes, snippets
  "response": str,
  "model_override": Optional[str],
}
```

**Key Features**:
- Message history persisted in SurrealDB (SqliteSaver checkpoint)
- Context building via `build_context_for_chat()` utility
- Token counting to prevent overflow
- Per-message model override support

**Invoked By**: Chat API (`POST /chat/execute`)

---

### 3. **Ask Workflow** (`open_notebook/graphs/ask.py`)

**Purpose**: Answer user questions by searching sources and synthesizing responses.

**Flow**:
```
User Question
  ↓
Plan Search Strategy (LLM generates searches)
  ↓
Execute Searches (vector + text search)
  ↓
Score & Rank Results
  ↓
Provide Answers (LLM synthesizes from results)
  ↓
Stream Responses
  ↓
Output (final answer)
```

**State Dict**:
```python
{
  "question": str,
  "strategy": SearchStrategy,
  "answers": List[str],
  "final_answer": str,
  "sources_used": List[Source],
}
```

**Streaming**: Uses `astream()` to emit updates in real-time (strategy → answers → final answer)

**Invoked By**: Search API (`POST /ask` with streaming)

---

### 4. **Transformation Workflow** (`open_notebook/graphs/transformation.py`)

**Purpose**: Apply custom transformations to sources (extract summaries, key points, etc).

**Flow**:
```
Source + Transformation Rule
  ↓
Generate Prompt (Jinja2 template)
  ↓
Call LLM
  ↓
Parse Output
  ↓
Create SourceInsight record
  ↓
Output (insight with type + content)
```

**Example Transformations**:
- Summary (5-sentence overview)
- Key Points (bulleted list)
- Quotes (notable excerpts)
- Q&A (generated questions and answers)

**Invoked By**: Sources API (`POST /sources/{id}/insights`)

---

### 5. **Prompt Workflow** (`open_notebook/graphs/prompt.py`)

**Purpose**: Generic LLM task execution (e.g., auto-generate note titles, analyze content).

**Flow**:
```
Input Text + Prompt
  ↓
Call LLM (simple request-response)
  ↓
Output (completion)
```

**Used For**: Note title generation, content analysis, etc.

---

## AI Provider Integration Pattern

### ModelManager: Centralized Factory

Located in `open_notebook/ai/models.py`, ModelManager handles:

1. **Provider Detection**: Check environment variables for available providers
2. **Model Selection**: Choose best model based on context size and task
3. **Fallback Logic**: If primary provider unavailable, try backup
4. **Cost Optimization**: Prefer cheaper models for simple tasks
5. **Token Calculation**: Estimate cost before LLM call

**Usage**:
```python
from open_notebook.ai.provision import provision_langchain_model

# Get best LLM for context size
model = await provision_langchain_model(
    task="chat",  # or "search", "extraction"
    model_override="anthropic/claude-opus-4",  # optional
    context_size=8000,  # estimated tokens
)

# Invoke model
response = await model.ainvoke({"input": prompt})
```

### Multi-Provider Support

**LLM Providers**:
- OpenAI (gpt-4, gpt-4-turbo, gpt-3.5-turbo)
- Anthropic (claude-opus, claude-sonnet, claude-haiku)
- Google (gemini-pro, gemini-1.5)
- Groq (mixtral, llama-2)
- Ollama (local models)
- Mistral (mistral-large, mistral-medium)
- DeepSeek (deepseek-chat)
- xAI (grok)

**Embedding Providers**:
- OpenAI (text-embedding-3-large, text-embedding-3-small)
- Google (embedding-001)
- Ollama (local embeddings)
- Mistral (mistral-embed)
- Voyage (voyage-large-2)

**TTS Providers**:
- OpenAI (tts-1, tts-1-hd)
- Groq (no TTS, fallback to OpenAI)
- ElevenLabs (multilingual voices)
- Google TTS (text-to-speech)

### Per-Request Override

Every LangGraph invocation accepts a `config` parameter to override models:

```python
result = await graph.ainvoke(
    input={...},
    config={
        "configurable": {
            "model_override": "anthropic/claude-opus-4"  # Use Claude instead
        }
    }
)
```

---

## Design Patterns

### 1. **Domain-Driven Design (DDD)**

**Domain Objects** (`open_notebook/domain/`):
- `Notebook`: Research container with relationships to sources/notes
- `Source`: Content item (PDF, URL, text) with embeddings
- `Note`: User-created or AI-generated research note
- `ChatSession`: Conversation history for a notebook
- `Transformation`: Custom rule for extracting insights

**Repository Pattern**:
- Database access layer (`open_notebook/database/repository.py`)
- `repo_query()`: Execute SurrealQL queries
- `repo_create()`: Insert records
- `repo_upsert()`: Merge records
- `repo_delete()`: Remove records

**Entity Methods**:
```python
# Domain methods (business logic)
notebook = await Notebook.get(id)
await notebook.save()
notes = await notebook.get_notes()
sources = await notebook.get_sources()
```

### 2. **Async-First Architecture**

**All I/O is async**:
- Database queries: `await repo_query(...)`
- LLM calls: `await model.ainvoke(...)`
- File I/O: `await upload_file.read()`
- Graph invocations: `await graph.ainvoke(...)`

**Benefits**:
- Non-blocking request handling (FastAPI serves multiple concurrent requests)
- Better resource utilization (I/O waiting doesn't block CPU)
- Natural fit for Python async/await syntax

**Example**:
```python
@router.post("/sources")
async def create_source(source_data: SourceCreate):
    # All operations are non-blocking
    source = Source(title=source_data.title)
    await source.save()  # async database operation
    await graph.ainvoke({...})  # async LangGraph invocation
    return SourceResponse(...)
```

### 3. **Service Pattern**

Services orchestrate domain objects, repositories, and workflows:

```python
# api/notebook_service.py
class NotebookService:
    async def get_notebook_with_stats(notebook_id: str):
        notebook = await Notebook.get(notebook_id)
        sources = await notebook.get_sources()
        notes = await notebook.get_notes()
        return {
            "notebook": notebook,
            "source_count": len(sources),
            "note_count": len(notes),
        }
```

**Responsibilities**:
- Validate inputs (Pydantic)
- Orchestrate database operations
- Invoke workflows (LangGraph graphs)
- Handle errors and return appropriate status codes
- Log operations

### 4. **Streaming Pattern**

For long-running operations (ask workflow, podcast generation), stream results as Server-Sent Events:

```python
@router.post("/ask", response_class=StreamingResponse)
async def ask(request: AskRequest):
    async def stream_response():
        async for chunk in ask_graph.astream(input={...}):
            yield f"data: {json.dumps(chunk)}\n\n"
    return StreamingResponse(stream_response(), media_type="text/event-stream")
```

### 5. **Job Queue Pattern**

For async background tasks (source processing), use Surreal-Commands job queue:

```python
# Submit job
command_id = await CommandService.submit_command_job(
    app="open_notebook",
    command="process_source",
    input={...}
)

# Poll status
status = await source.get_status()
```

---

## Service Communication Patterns

### Frontend → API

1. **REST requests** (HTTP GET/POST/PUT/DELETE)
2. **JSON request/response bodies**
3. **Standard HTTP status codes** (200, 400, 404, 500)
4. **Optional streaming** (Server-Sent Events for long operations)

**Example**:
```typescript
// Frontend
const response = await fetch("http://localhost:5055/sources", {
  method: "POST",
  body: formData,  // multipart/form-data for file upload
});
const source = await response.json();
```

### API → SurrealDB

1. **SurrealQL queries** (similar to SQL)
2. **Async driver** with connection pooling
3. **Type-safe record IDs** (record_id syntax)
4. **Transaction support** for multi-step operations

**Example**:
```python
# API
result = await repo_query(
    "SELECT * FROM source WHERE notebook = $notebook_id",
    {"notebook_id": ensure_record_id(notebook_id)}
)
```

### API → AI Providers (via Esperanto)

1. **Esperanto unified interface**
2. **Per-request provider override**
3. **Automatic fallback on failure**
4. **Token counting and cost estimation**

**Example**:
```python
# API
model = await provision_langchain_model(task="chat")
response = await model.ainvoke({"input": prompt})
```

### API → Job Queue (Surreal-Commands)

1. **Async job submission**
2. **Fire-and-forget pattern**
3. **Status polling via `/commands/{id}` endpoint**
4. **Job completion callbacks (optional)**

**Example**:
```python
# Submit async source processing
command_id = await CommandService.submit_command_job(...)

# Client polls status
response = await fetch(f"http://localhost:5055/commands/{command_id}")
status = await response.json()  # returns { status: "running|queued|completed|failed" }
```

---

## Database Schema Overview

### Core Schema Structure

**Tables** (20+):
- Notebooks (with soft-delete via `archived` flag)
- Sources (content + metadata)
- SourceEmbeddings (vector chunks)
- Notes (user-created + AI-generated)
- ChatSessions (conversation history)
- Transformations (custom rules)
- SourceInsights (transformation outputs)
- Relationships (notebook→source, notebook→note)

**Migrations**:
- Automatic on API startup
- Located in `/migrations/` directory
- Numbered sequentially (001_*.surql, 002_*.surql, etc)
- Tracked in `_sbl_migrations` table
- Rollback via `_down.surql` files (manual)

### Relationship Model

**Graph Relationships**:
```
Notebook
  ← reference ← Source (many:many)
  ← artifact ← Note (many:many)

Source
  → source_embedding (one:many)
  → source_insight (one:many)
  → embedding (via source_embedding)

ChatSession
  → messages (JSON array in database)
  → notebook_id (reference to Notebook)

Transformation
  → source_insight (one:many)
```

**Query Example** (get all sources in a notebook with counts):
```sql
SELECT id, title,
  count(<-reference.in) as note_count,
  count(<-embedding.in) as embedded_chunks
FROM source
WHERE notebook = $notebook_id
ORDER BY updated DESC
```

---

## Key Architectural Decisions

### 1. **Async Throughout**

All I/O operations are non-blocking to maximize concurrency and responsiveness.

**Trade-off**: Slightly more complex code (async/await syntax) vs. high throughput.

### 2. **Multi-Provider from Day 1**

Built-in support for 8+ AI providers prevents vendor lock-in.

**Trade-off**: Added complexity in ModelManager vs. flexibility and cost optimization.

### 3. **Graph-First Workflows**

LangGraph state machines for complex multi-step operations (ask, chat, transformations).

**Trade-off**: Steeper learning curve vs. maintainable, debuggable workflows.

### 4. **Self-Hosted Database**

SurrealDB for graph + vector search in one system (no external dependencies).

**Trade-off**: Operational responsibility vs. simplified architecture and cost savings.

### 5. **Job Queue for Long-Running Tasks**

Async job submission (source processing, podcast generation) prevents request timeouts.

**Trade-off**: Eventual consistency vs. responsive user experience.

---

## Important Quirks & Gotchas

### API Startup

- **Migrations run automatically** on every startup; check logs for errors
- **SurrealDB must be running** before starting API (connection test in lifespan)
- **Auth middleware is basic** (password-only); upgrade to OAuth/JWT for production

### Database Operations

- **Record IDs use SurrealDB syntax** (table:id format, e.g., "notebook:abc123")
- **ensure_record_id()** helper prevents malformed IDs
- **Soft deletes** via `archived` field (data not removed, just marked inactive)
- **Timestamps in ISO 8601 format** (created, updated fields)

### LangGraph Workflows

- **State persistence** via SqliteSaver in `/data/sqlite-db/`
- **No built-in timeout**; long workflows may block requests (use streaming for UX)
- **Model fallback** automatic if primary provider unavailable
- **Checkpoint IDs** must be unique per session (avoid collisions)

### AI Provider Integration

- **Esperanto library** handles all provider APIs (no direct API calls)
- **Per-request override** via RunnableConfig (temporary, not persistent)
- **Cost estimation** via token counting (not 100% accurate, use for guidance)
- **Fallback logic** tries cheaper models if primary fails

### File Uploads

- **Stored in `/data/uploads/`** directory (not database)
- **Unique filename generation** prevents overwrites (counter suffix)
- **Content-core library** extracts text from 50+ file types
- **Large files** may block API briefly (sync content extraction)

---

## Performance Considerations

### Optimization Strategies

1. **Connection Pooling**: SurrealDB async driver with configurable pool size
2. **Query Caching**: TanStack Query on frontend (client-side caching)
3. **Embedding Reuse**: Vector search uses pre-computed embeddings
4. **Chunking**: Sources split into chunks for better search relevance
5. **Async Operations**: Non-blocking I/O for high concurrency
6. **Lazy Loading**: Frontend requests only needed data (pagination)

### Bottlenecks

1. **LLM Calls**: Latency depends on provider (typically 1-30 seconds)
2. **Embedding Generation**: Time proportional to content size and provider
3. **Vector Search**: Similarity computation over all embeddings
4. **Content Extraction**: Sync operation in source processing

### Monitoring

- **API Logs**: Check loguru output for errors and slow operations
- **Database Queries**: SurrealDB metrics available via admin UI
- **Token Usage**: Estimated via `estimate_tokens()` utility
- **Job Status**: Poll `/commands/{id}` for async operations

---

## Extension Points

### Adding a New Workflow

1. Create `open_notebook/graphs/workflow_name.py`
2. Define StateDict and node functions
3. Build graph with `.add_node()` / `.add_edge()`
4. Create service in `api/workflow_service.py`
5. Register router in `api/main.py`
6. Add tests in `tests/test_workflow.py`

### Adding a New Data Model

1. Create model in `open_notebook/domain/model_name.py`
2. Inherit from BaseModel (domain object)
3. Implement `save()`, `get()`, `delete()` methods (CRUD)
4. Add repository functions if complex queries needed
5. Create database migration in `migrations/`
6. Add API routes and models in `api/`

### Adding a New AI Provider

1. Configure Esperanto for new provider (see .env.example)
2. ModelManager automatically detects via environment variables
3. Override via per-request config (no code changes needed)
4. Test fallback logic if provider unavailable

---

## Deployment Considerations

### Development

- All services on localhost (3000, 5055, 8000)
- Auto-reload on file changes (Next.js, FastAPI)
- Hot-reload database migrations
- Open API docs at http://localhost:5055/docs

### Production

- **Frontend**: Deploy to Vercel, Netlify, or Docker
- **API**: Docker container (see Dockerfile)
- **Database**: SurrealDB container or managed service
- **Environment**: Secure .env file with API keys
- **SSL/TLS**: Reverse proxy (Nginx, CloudFlare)
- **Rate Limiting**: Add at proxy layer
- **Auth**: Replace PasswordAuthMiddleware with OAuth/JWT
- **Monitoring**: Log aggregation (CloudWatch, DataDog, etc)

---

## Summary

Open Notebook's architecture provides a solid foundation for privacy-focused, AI-powered research. The separation of concerns (frontend/API/database), async-first design, and multi-provider flexibility enable rapid development and easy deployment. LangGraph workflows orchestrate complex AI tasks, while Esperanto abstracts provider details. The result is a scalable, maintainable system that puts users in control of their data and AI provider choice.
