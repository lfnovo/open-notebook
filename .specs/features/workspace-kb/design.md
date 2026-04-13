# M1 Core KB Platform — Design

**Spec:** `.specs/features/workspace-kb/spec.md`
**Status:** Draft

---

## Architecture Overview

The design builds on the existing open-notebook architecture (FastAPI + Next.js 16 + SurrealDB) and introduces four new subsystems: Clerk auth, workspace-scoped data, LightRAG knowledge graphs, and an MCP server. The core principle is **isolation by workspace** — every piece of data (sources, notes, graph, embeddings) belongs to exactly one workspace.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENTS                                       │
│   Browser (Next.js 16)          AI Agents (MCP)          API consumers  │
└────────┬────────────────────────────┬─────────────────────────┬─────────┘
         │ Clerk JWT                  │ API Key                 │ Clerk JWT
         ▼                            ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                                   │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Auth Layer   │  │  Workspace   │  │  Ingestion  │  │    MCP      │  │
│  │  (Clerk JWT)  │  │  Router/RBAC │  │  Pipeline   │  │   Server    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  └──────┬──────┘  │
│         │                  │                  │                │         │
│  ┌──────▼──────────────────▼──────────────────▼────────────────▼──────┐  │
│  │                     Service Layer                                  │  │
│  │  WorkspaceService  SourceService  GraphService  ChatService        │  │
│  └────────────────────────────┬───────────────────────────────────────┘  │
│                               │                                          │
│  ┌────────────────────────────▼───────────────────────────────────────┐  │
│  │                     Data Layer                                      │  │
│  │  SurrealDB (metadata, vectors, RBAC)     LightRAG (per-workspace)  │  │
│  │  Filesystem (uploads, graph working_dirs)                          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
|---|---|---|
| `ObjectModel` base class | `open_notebook/domain/base.py:31` | Extend for Workspace, WorkspaceMember models — reuse `save()`, `delete()`, `get()`, `get_all()` |
| `RecordModel` singleton pattern | `open_notebook/domain/base.py:206` | Reuse pattern for MCP server config (singleton per deployment) |
| `Source` model + ingestion | `open_notebook/domain/notebook.py:288` | Add `workspace_id` field, reuse upload/processing pipeline |
| `Note` model | `open_notebook/domain/notebook.py:557` | Add `workspace_id` field, reuse CRUD and indexing |
| `vector_search()` | `open_notebook/domain/notebook.py:650` | Extend to accept workspace filter (SurrealDB WHERE clause) |
| `text_search()` | `open_notebook/domain/notebook.py:630` | Extend to accept workspace filter |
| Repository functions | `open_notebook/database/repository.py` | Reuse `repo_create`, `repo_query`, `repo_update`, `repo_delete` — no changes needed (table/query-level) |
| Source processing graph | `open_notebook/graphs/source.py` | Reuse content_process + save_source pipeline; add graph extraction step after save |
| Ask graph (RAG) | `open_notebook/graphs/ask.py` | Replace `vector_search()` call in `provide_answer()` with workspace-scoped LightRAG hybrid query |
| Chat graph | `open_notebook/graphs/chat.py` | Add workspace context loading, replace SqliteSaver with SurrealDB-backed checkpointer |
| Command system | `commands/` | Reuse `@command` pattern for `build_graph_command`, `embed_source_command` |
| `PasswordAuthMiddleware` | `api/auth.py:12` | **Replace** with `ClerkAuthMiddleware` |
| Source upload router | `api/routers/sources.py` | Extend with workspace_id parameter, reuse multipart handling |
| Frontend API client | `frontend/src/lib/api/client.ts` | Replace auth interceptor (Clerk token instead of password) |
| Auth store (Zustand) | `frontend/src/lib/stores/auth-store.ts` | **Replace** with Clerk session state |
| Dashboard layout guard | `frontend/src/app/(dashboard)/layout.tsx` | Replace with Clerk's `auth()` check |
| TanStack Query setup | `frontend/src/lib/api/query-client.ts` | Reuse — add workspace-scoped query keys |
| AppSidebar | `frontend/src/components/layout/AppSidebar.tsx` | Extend navigation: replace Notebooks with Workspaces |

### Integration Points

| System | Integration Method |
|---|---|
| SurrealDB | All domain models persist via existing `repo_*` functions; add `workspace_id` field + indexes |
| LightRAG | One `LightRAG` instance per workspace, initialized lazily, cached in memory with TTL eviction |
| RAGAnything | Wraps LightRAG for document parsing; called during source processing command |
| Clerk | Frontend: `@clerk/nextjs` middleware + `<ClerkProvider>`. Backend: JWT verification via JWKS |
| MCP | Standalone `FastMCP` server process, queries backend API internally |

---

## Components

### 1. Auth Layer — Clerk Integration

- **Purpose:** Replace password-based auth with Clerk SSO/OIDC + email invitation, providing user identity to all downstream components.
- **Location:** `api/auth.py` (replace), `frontend/src/proxy.ts` (replace), `frontend/src/components/auth/` (replace)

**Backend — `ClerkAuthMiddleware`:**
```python
# api/auth.py — replaces PasswordAuthMiddleware
class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Verifies Clerk JWT from Authorization header using JWKS."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip: /health, /api/config, /api/mcp/*
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        payload = await verify_clerk_jwt(token)  # Uses PyJWT + Clerk JWKS endpoint
        request.state.user_id = payload["sub"]
        request.state.org_id = payload.get("org_id")
        return await call_next(request)
```

Clerk issues standard JWTs. The backend verifies them using Clerk's JWKS endpoint (cacheable, no Clerk SDK needed in Python — use `PyJWT` + `jwcrypto`). No Clerk Python SDK dependency.

**Frontend — `@clerk/nextjs`:**
- `proxy.ts`: Export `clerkMiddleware()` for route protection.
- Root layout: Wrap app in `<ClerkProvider>`.
- Dashboard layout: Replace `useAuth()` hook with Clerk's `auth()`.
- API client interceptor: Get token via `useAuth().getToken()` instead of localStorage password.

**Env vars:**
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `CLERK_SECRET_KEY`
- `CLERK_JWKS_URL` (derived from Clerk frontend API URL)

### 2. Workspace Domain Model

- **Purpose:** Core data model for organizing content. Workspaces own sources, notes, chat sessions, and a LightRAG graph.
- **Location:** `open_notebook/domain/workspace.py` (new)
- **Reuses:** `ObjectModel` from `base.py`

```python
class Workspace(ObjectModel):
    table_name: ClassVar[str] = "workspace"
    
    name: str
    description: Optional[str] = None
    visibility: Literal["private", "shared", "community"]  # WS-01
    owner_id: str           # Clerk user ID
    org_id: Optional[str]   # Clerk org ID (for community discovery)
    
    async def get_members(self) -> List["WorkspaceMember"]: ...
    async def get_sources(self) -> List["Source"]: ...
    async def get_notes(self) -> List["Note"]: ...
    async def get_chat_sessions(self) -> List["ChatSession"]: ...
    async def delete(self) -> bool: ...  # Cascade: sources, notes, graph, members

class WorkspaceMember(ObjectModel):
    table_name: ClassVar[str] = "workspace_member"
    
    workspace_id: str
    user_id: str            # Clerk user ID
    role: Literal["owner", "editor", "viewer"]  # WS-05, WS-06
    
    @classmethod
    async def get_for_user(cls, user_id: str) -> List["WorkspaceMember"]: ...
    @classmethod
    async def get_for_workspace(cls, workspace_id: str) -> List["WorkspaceMember"]: ...
```

**Existing model changes:**
- `Source`: Add `workspace_id: str` field. Remove Notebook-based association (Sources belong to a Workspace, not a Notebook).
- `Note`: Add `workspace_id: str` field. Same treatment.
- `ChatSession`: Add `workspace_id: str` field.
- `SourceEmbedding`: Add `workspace_id: str` field (enables workspace-scoped vector search).
- `Notebook` model: **Deprecate.** Workspaces replace Notebooks as the primary container. Notebook functionality (grouping sources + notes + chat) is subsumed by Workspace.

### 3. RBAC Middleware

- **Purpose:** Enforce per-workspace role checks on every workspace-scoped API endpoint.
- **Location:** `api/rbac.py` (new)

```python
async def require_workspace_role(
    workspace_id: str,
    user_id: str,
    minimum_role: Literal["viewer", "editor", "owner"]
) -> WorkspaceMember:
    """Raises HTTP 403 if user lacks the required role. Returns the membership."""
```

Used as a FastAPI dependency on workspace-scoped routes:

```python
@router.post("/workspaces/{workspace_id}/sources")
async def upload_source(
    workspace_id: str,
    member: WorkspaceMember = Depends(require_editor),  # require_editor calls require_workspace_role
    ...
):
```

Community workspace discovery (WS-04): `GET /workspaces/discover` returns workspaces with `visibility=community` in the user's org, without requiring membership.

### 4. Graph Service — LightRAG per Workspace

- **Purpose:** Manage one LightRAG instance per workspace for knowledge graph construction and hybrid retrieval.
- **Location:** `open_notebook/services/graph_service.py` (new)

**Isolation strategy:** Each workspace gets a dedicated `working_dir` at `data/graphs/{workspace_id}/`. LightRAG stores its graph, vector index, and chunk data inside this directory. This is the simplest isolation — no shared state, no cross-contamination, easy to delete (rm -rf).

```python
class GraphService:
    _instances: Dict[str, LightRAG] = {}
    _lock: asyncio.Lock = asyncio.Lock()
    MAX_CACHED = 20  # LRU eviction for memory pressure
    
    @classmethod
    async def get_instance(cls, workspace_id: str) -> LightRAG:
        """Lazy-initialize or return cached LightRAG for this workspace."""
        async with cls._lock:
            if workspace_id not in cls._instances:
                working_dir = f"data/graphs/{workspace_id}"
                os.makedirs(working_dir, exist_ok=True)
                rag = LightRAG(
                    working_dir=working_dir,
                    llm_model_func=get_configured_llm(),
                    embedding_func=get_configured_embedding(),
                )
                await rag.initialize_storages()
                cls._instances[workspace_id] = rag
                cls._evict_lru()
            return cls._instances[workspace_id]
    
    @classmethod
    async def insert(cls, workspace_id: str, text: str) -> None:
        rag = await cls.get_instance(workspace_id)
        await rag.ainsert(text)
    
    @classmethod
    async def query(cls, workspace_id: str, question: str, mode: str = "hybrid") -> str:
        rag = await cls.get_instance(workspace_id)
        return await rag.aquery(question, param=QueryParam(mode=mode))
    
    @classmethod
    async def delete_workspace(cls, workspace_id: str) -> None:
        if workspace_id in cls._instances:
            await cls._instances[workspace_id].finalize_storages()
            del cls._instances[workspace_id]
        shutil.rmtree(f"data/graphs/{workspace_id}", ignore_errors=True)
```

**Graph extraction trigger:** After a Source reaches "Ready" status (content extracted + saved), a new `@command("build_graph")` is submitted. This command loads the source content, calls `GraphService.insert(workspace_id, content)`, and marks the source's graph status.

**LLM/Embedding provisioning:** LightRAG accepts custom `llm_model_func` and `embedding_func`. We wrap Esperanto's `provision_langchain_model()` into LightRAG-compatible callables, reusing the existing model configuration system (ProviderConfig).

### 5. RAGAnything Document Ingestion

- **Purpose:** Replace the basic content-core extraction with RAGAnything for multimodal document processing (PDF tables, images, equations).
- **Location:** `open_notebook/services/ingestion_service.py` (new)
- **Reuses:** Existing source processing graph (`open_notebook/graphs/source.py`) as the orchestrator.

**Integration point:** The `content_process` node in `source.py` currently calls `extract_content()` from content-core. We add an alternate path:

```python
# In source.py content_process node:
if file_type in ("pdf", "docx", "pptx"):
    # Use RAGAnything for rich document parsing
    content, multimodal_items = await raganything_extract(file_path)
else:
    # Existing content-core path for txt, md, url
    content = await extract_content(file_path)
```

RAGAnything uses MinerU for document parsing. For v1, we process text + tables. Image OCR is enabled but images are stored as text descriptions (VLM captioning deferred to v2 to avoid mandatory GPU).

**After extraction:** The extracted text is both:
1. Stored in the Source record (as today) + embedded via existing `embed_source_command`
2. Inserted into the workspace LightRAG graph via `build_graph` command

### 6. Chat & Search — Workspace-Scoped

- **Purpose:** Adapt the existing ask/chat graphs to query workspace-scoped LightRAG instead of global vector search.
- **Location:** Modify `open_notebook/graphs/ask.py`, `open_notebook/graphs/chat.py`

**Ask graph (`ask.py`) changes:**
- `provide_answer()` currently calls `vector_search(term, 10, True, True)`.
- Replace with: `GraphService.query(workspace_id, term, mode="hybrid")` for the primary retrieval path.
- Also run `vector_search(term, 10, workspace_id=workspace_id)` as a fallback for sources where graph extraction failed (GRAPH-03).
- Merge and deduplicate results before LLM synthesis.

**Chat graph (`chat.py`) changes:**
- Replace SqliteSaver (global sqlite) with a SurrealDB-backed checkpointer or per-workspace sqlite file at `data/graphs/{workspace_id}/chat_checkpoints.sqlite`.
- Context loading: When starting a chat, load workspace's source list + recent notes as context.

**Multi-workspace query (CHAT-01):**
- The chat interface allows selecting multiple workspaces.
- For each selected workspace, run the retrieval in parallel.
- Merge results (permission-checked — user must have Viewer+ on each workspace).
- Feed merged context to the synthesis LLM.

### 7. MCP Server

- **Purpose:** Expose workspace KB to AI coding agents (Cursor, Claude, Copilot) via Model Context Protocol.
- **Location:** `mcp/` (new top-level directory)

**Approach:** Standalone `FastMCP` server (Python, using the `mcp` library). Runs as a separate process alongside the main API. Communicates with the backend via internal HTTP calls or direct service imports.

**Tools exposed:**

```python
@mcp.tool()
async def search_kb(query: str, workspace_ids: list[str]) -> list[dict]:
    """Search one or more workspaces. Returns ranked results with content and source."""

@mcp.tool()
async def list_workspaces() -> list[dict]:
    """List workspaces accessible to the authenticated user."""

@mcp.tool()
async def get_entity(name: str, workspace_id: str) -> dict:
    """Get a knowledge graph entity by name — description, relationships, sources."""
```

**Auth:** MCP API keys are scoped to a user + specific workspace set. Stored encrypted in SurrealDB (reuse `Credential` encryption pattern). The MCP server validates the key on every request and maps it to a user_id for RBAC checks.

**Transport:** stdio (for Cursor/Claude local integration) and SSE (for remote agents).

### 8. Frontend — Workspace Shell

- **Purpose:** Replace the Notebook-centric UI with a Workspace-centric layout.
- **Location:** `frontend/src/`

**Structural changes:**
- `/notebooks` → `/workspaces` (list all accessible workspaces)
- `/notebooks/[id]` → `/workspaces/[id]` (workspace detail: sources, notes, chat, graph explorer)
- `/login` → Clerk's `<SignIn>` component
- New: `/workspaces/discover` — browse Community workspaces in the org

**Sidebar navigation update:**
```
Collect  → Workspaces (/workspaces)
         → Discover (/workspaces/discover)
Process  → Ask & Search (/search) — with workspace scope selector
Create   → [removed podcasts]
Manage   → Models, Settings, Advanced (unchanged)
```

**State management:**
- Remove `auth-store.ts` (Zustand) — Clerk manages session state.
- Add `workspace-store.ts` — tracks active workspace ID, membership cache.
- TanStack Query keys get workspace prefix: `["workspaces", workspaceId, "sources"]`.

---

## Data Models

### SurrealDB Schema Additions

```sql
-- Workspace
DEFINE TABLE workspace SCHEMAFULL;
DEFINE FIELD name ON workspace TYPE string;
DEFINE FIELD description ON workspace TYPE option<string>;
DEFINE FIELD visibility ON workspace TYPE string ASSERT $value IN ["private", "shared", "community"];
DEFINE FIELD owner_id ON workspace TYPE string;
DEFINE FIELD org_id ON workspace TYPE option<string>;
DEFINE FIELD created ON workspace TYPE datetime DEFAULT time::now();
DEFINE FIELD updated ON workspace TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_workspace_owner ON workspace FIELDS owner_id;
DEFINE INDEX idx_workspace_org ON workspace FIELDS org_id;

-- Workspace Member
DEFINE TABLE workspace_member SCHEMAFULL;
DEFINE FIELD workspace_id ON workspace_member TYPE record<workspace>;
DEFINE FIELD user_id ON workspace_member TYPE string;
DEFINE FIELD role ON workspace_member TYPE string ASSERT $value IN ["owner", "editor", "viewer"];
DEFINE FIELD created ON workspace_member TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_wm_user ON workspace_member FIELDS user_id;
DEFINE INDEX idx_wm_workspace ON workspace_member FIELDS workspace_id;
DEFINE INDEX idx_wm_unique ON workspace_member FIELDS workspace_id, user_id UNIQUE;

-- Add workspace_id to existing tables
DEFINE FIELD workspace_id ON source TYPE record<workspace>;
DEFINE INDEX idx_source_workspace ON source FIELDS workspace_id;

DEFINE FIELD workspace_id ON note TYPE record<workspace>;
DEFINE INDEX idx_note_workspace ON note FIELDS workspace_id;

DEFINE FIELD workspace_id ON source_embedding TYPE record<workspace>;
DEFINE INDEX idx_embedding_workspace ON source_embedding FIELDS workspace_id;

DEFINE FIELD workspace_id ON chat_session TYPE record<workspace>;
DEFINE INDEX idx_chat_workspace ON chat_session FIELDS workspace_id;

-- MCP API Key
DEFINE TABLE mcp_api_key SCHEMAFULL;
DEFINE FIELD key_hash ON mcp_api_key TYPE string;
DEFINE FIELD user_id ON mcp_api_key TYPE string;
DEFINE FIELD workspace_ids ON mcp_api_key TYPE array;
DEFINE FIELD label ON mcp_api_key TYPE string;
DEFINE FIELD created ON mcp_api_key TYPE datetime DEFAULT time::now();
DEFINE FIELD expires_at ON mcp_api_key TYPE option<datetime>;
DEFINE INDEX idx_mcp_key ON mcp_api_key FIELDS key_hash UNIQUE;
```

### Relationships (existing SurrealDB graph edges — kept)

- `notebook:xxx -> has_source -> source:xxx` → Replaced by `workspace_id` field on Source
- `notebook:xxx -> has_note -> note:xxx` → Replaced by `workspace_id` field on Note

The existing graph-edge relationships between notebooks and sources/notes are **replaced** by a simple foreign key (`workspace_id`) on each record. This simplifies queries and aligns with workspace-scoped access patterns.

---

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
|---|---|---|
| Clerk JWT expired/invalid | Return HTTP 401, frontend redirects to Clerk sign-in | "Session expired, please sign in again" |
| User not a workspace member | Return HTTP 403 from RBAC middleware | "You don't have access to this workspace" |
| LightRAG initialization fails | Log error, mark graph status as "unavailable", allow vector-only fallback | Source shows "Graph Warning" badge; search still works via vector |
| RAGAnything/MinerU parsing fails | Mark source as "Failed", store error message, allow retry | "Processing failed: [error]. Click to retry." |
| LightRAG insert fails on source | Mark source with "Graph Warning" flag, vector search still works (GRAPH-03) | Source available for search but without graph-enhanced retrieval |
| Multi-workspace query with mixed access | Silently exclude inaccessible workspaces from results | No error shown; results only from accessible workspaces |
| MCP API key invalid/expired | Return HTTP 401 with JSON error body | Agent receives auth error, user must regenerate key |

---

## Tech Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Clerk JWT verification in Python | `PyJWT` + JWKS, NOT Clerk Python SDK | Clerk has no official Python SDK. PyJWT is well-tested, the JWKS endpoint is standard. Avoids an unnecessary dependency. |
| LightRAG isolation | One `working_dir` per workspace (filesystem) | Simplest isolation. LightRAG's native approach — each instance is fully independent. Easy to delete. External DB backends (Qdrant, Neo4j) would require workspace field filtering, adding complexity. |
| LightRAG LLM/Embedding | Wrap Esperanto provisioning | Reuses the existing model configuration (ProviderConfig) — users manage models in one place. |
| Replace Notebooks with Workspaces | Drop the Notebook entity entirely | Notebooks and Workspaces are semantically identical containers for sources + notes + chat. Keeping both adds confusion. Migration: rename `notebook` table to `workspace`, add new fields. |
| MCP server as separate process | FastMCP with stdio + SSE transport | MCP spec requires stdio for local agents (Cursor). Running it in-process with FastAPI would conflict. Separate process is the standard pattern. |
| RAGAnything for document parsing | Use for PDF/DOCX/PPTX; keep content-core for TXT/MD/URL | RAGAnything (built on LightRAG by the same team) provides table/image extraction that content-core lacks. But it requires MinerU which is heavy — only use it for rich documents. |
| Chat checkpointer | Per-workspace sqlite file in `data/graphs/{workspace_id}/` | Avoids the global single-sqlite bottleneck. Each workspace's chat history is isolated. Consistent with the per-workspace-directory strategy. |
| Frontend auth | `@clerk/nextjs` middleware + `<ClerkProvider>` | Clerk's Next.js SDK handles the middleware, session management, and organization switching. Zero custom auth code on the frontend. |
| Deprecate Notebook model | Replace with Workspace in a single migration | Maintaining both Notebook and Workspace would double the data model complexity. Users think in "workspaces", not "notebooks" — this is a corporate tool. |
