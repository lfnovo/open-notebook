# Open Notebook - Mermaid Architecture Diagrams

## 1. Overall Three-Tier Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React/Next.js) - Port 3000"]
        UI["UI Layer<br/>Shadcn/ui + Tailwind"]
        Components["Components<br/>notebooks, sources, chat, podcasts, search"]
        Hooks["Hooks<br/>TanStack Query + Custom Hooks"]
        Stores["Zustand Stores<br/>auth, sidebar, theme, columns"]
    end

    subgraph API["API Backend (FastAPI) - Port 5055"]
        Routers["19 Routers<br/>notebooks, sources, chat, search, credentials..."]
        Services["Services<br/>*_service.py (business logic)"]
        LangGraph["LangGraph Workflows<br/>source, chat, ask, transformation"]
        AI["AI Provisioning<br/>Esperanto + ModelManager"]
    end

    subgraph Database["Database (SurrealDB) - Port 8000"]
        SurrealDB["Graph DB + Vector Search"]
        Migrations["14 Migrations (async)"]
        Tables["Tables: notebooks, sources, notes, credentials, models..."]
    end

    Frontend -->|"HTTP REST"| API
    API -->|"SurrealQL"| Database

    style Frontend fill:#e1f5fe
    style API fill:#fff3e0
    style Database fill:#e8f5e9
```

---

## 2. Frontend Module Structure

```mermaid
flowchart TB
    subgraph App["src/app/ (Next.js App Router)"]
        Auth["(auth)/login"]
        Dashboard["(dashboard)/"]
        Config["config/route.ts"]
    end

    subgraph Components["src/components/"]
        UI["ui/ (24 shadcn components)"]
        Layout["layout/ (AppShell, AppSidebar)"]
        Providers["providers/ (Theme, Query, I18n, Modal)"]
        Features["notebooks/, sources/, podcasts/, search/, settings/"]
    end

    subgraph Lib["src/lib/"]
        API["api/ (14 modules + client)"]
        Hooks["hooks/ (16 custom hooks)"]
        Stores["stores/ (4 Zustand stores)"]
        Types["types/ (7 TypeScript files)"]
        Locales["locales/ (10 languages)"]
    end

    App --> Components
    Components --> Lib
    Lib -->|"HTTP"| API

    style Frontend fill:#e1f5fe
```

---

## 3. API Backend Structure

```mermaid
flowchart TB
    subgraph Routers["19 Routers"]
        R1["auth"]
        R2["notebooks"]
        R3["sources"]
        R4["chat"]
        R5["search"]
        R6["models"]
        R7["credentials"]
        R8["transformations"]
        R9["podcasts"]
        R10["notes"]
        R11["embedding"]
        R12["settings"]
        R13["context"]
        R14["insights"]
        R15["commands"]
        R16["episode_profiles"]
        R17["speaker_profiles"]
        R18["source_chat"]
        R19["languages"]
    end

    subgraph Services["Services"]
        S1["command_service"]
        S2["chat_service"]
        S3["sources_service"]
        S4["podcast_service"]
        S5["credentials_service"]
        S6["models_service"]
    end

    subgraph Core["open_notebook/"]
        AI["ai/ (ModelManager, provision)"]
        Domain["domain/ (Notebook, Source, Note)"]
        Graphs["graphs/ (6 LangGraph workflows)"]
        DB["database/ (repository, migrations)"]
        Utils["utils/ (embedding, chunking, etc.)"]
    end

    Routers --> Services
    Services --> Core

    style API fill:#fff3e0
```

---

## 4. LangGraph Workflows

```mermaid
flowchart LR
    subgraph source_graph["source.py"]
        direction TB
        START1["START"] --> Extract["content_process<br/>extract content"]
        Extract --> Save["save_source<br/>save to DB"]
        Save --> CheckT{"apply<br/>transformations?"}
        CheckT -->|Yes| Transforms["transform_content<br/>(parallel)"]
        CheckT -->|No| END1["END"]
        Transforms --> END1
    end

    subgraph chat_graph["chat.py"]
        direction TB
        START2["START"] --> Agent["agent<br/>call_model_with_messages"]
        Agent --> END2["END"]
    end

    subgraph ask_graph["ask.py"]
        direction TB
        START3["START"] --> Strategy["agent<br/>call_model (ask/entry)"]
        Strategy --> Search1["Search 1"]
        Strategy --> Search2["Search 2"]
        Strategy --> SearchN["Search N"]
        Search1 --> Answer1["provide_answer"]
        Search2 --> Answer2["provide_answer"]
        SearchN --> AnswerN["provide_answer"]
        Answer1 --> Synthesize["write_final_answer<br/>(ask/final_answer)"]
        Answer2 --> Synthesize
        AnswerN --> Synthesize
        Synthesize --> END3["END"]
    end

    subgraph source_chat_graph["source_chat.py"]
        direction TB
        START4["START"] --> SC_Agent["source_chat_agent<br/>call_model_with_source_context"]
        SC_Agent --> END4["END"]
    end

    style Graphs fill:#fce4ec
```

---

## 5. Data Flow: Source Upload to Chat

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API
    participant Router
    participant Service
    participant Graph
    participant Domain
    participant DB

    User->>Frontend: Upload file (PDF/URL)
    Frontend->>Frontend: useCreateSource() hook
    Frontend->>API: POST /api/sources (FormData)
    API->>Router: routes to sources router
    Router->>Service: sources_service.create_source()
    Service->>Graph: source_graph.ainvoke()
    Graph->>Graph: content_core.extract_content()
    Graph->>Domain: Source.save()
    Domain->>DB: repo_create("sources", data)
    DB-->>Domain: source_id
    Graph->>Graph: submit_command("embed_source")
    Service-->>Router: source created
    Router-->>Frontend: SourceResponse

    Note over Frontend,DB: Source uploaded and queued for embedding

    User->>Frontend: Send chat message
    Frontend->>Frontend: useNotebookChat() sendMessage()
    Frontend->>API: POST /api/chat/execute (SSE)
    API->>Router: routes to chat router
    Router->>Service: chat_service.send_message()
    Service->>Graph: chat_graph.ainvoke()
    Graph->>Graph: SqliteSaver checkpoint
    Graph->>Graph: provision_langchain_model()
    Graph->>AI: ModelManager.get_model()
    AI->>DB: query model credentials
    AI-->>Graph: LLM instance
    Graph->>Graph: model.ainvoke(messages)
    Graph-->>Service: response
    Service-->>Router: streaming response
    Router-->>Frontend: SSE stream

    Note over User,DB: Full round-trip for chat with source context
```

---

## 6. Domain Model Hierarchy

```mermaid
flowchart TB
    subgraph Base["open_notebook/domain/base.py"]
        ObjectModel["ObjectModel<br/>save(), delete(), relate(), get()"]
        RecordModel["RecordModel<br/>update(), get_instance()"]
    end

    subgraph Models["Domain Models (ObjectModel)"]
        Notebook["Notebook<br/>get_sources(), get_notes(), delete()"]
        Source["Source<br/>vectorize(), add_insight(), get_status()"]
        Note["Note<br/>add_to_notebook()"]
        ChatSession["ChatSession<br/>model_override"]
        Credential["Credential<br/>to_esperanto_config()"]
        Transformation["Transformation"]
        Model["Model<br/>get_models_by_type()"]
    end

    subgraph Singletons["RecordModel (Singleton)"]
        ContentSettings["ContentSettings"]
        DefaultPrompts["DefaultPrompts"]
        DefaultModels["DefaultModels"]
    end

    ObjectModel --> Notebook
    ObjectModel --> Source
    ObjectModel --> Note
    ObjectModel --> ChatSession
    ObjectModel --> Credential
    ObjectModel --> Transformation
    ObjectModel --> Model

    RecordModel --> ContentSettings
    RecordModel --> DefaultPrompts
    RecordModel --> DefaultModels

    style Domain fill:#e8f5e9
```

---

## 7. AI Provisioning Flow

```mermaid
flowchart TB
    Start["provision_langchain_model()"] --> TokenCheck{"tokens > 105k?"}
    TokenCheck -->|Yes| Large["large_context_model"]
    TokenCheck -->|No| ModelID{"model_id specified?"}
    ModelID -->|Yes| Specific["specific model"]
    ModelID -->|No| Default["default for type"]

    Large --> Lookup["ModelManager.get_model()"]
    Specific --> Lookup
    Default --> Lookup

    Lookup --> Cred{"credential<br/>linked?"}
    Cred -->|Yes| UseCred["credential.to_esperanto_config()<br/>→ AIFactory.create_*()"]
    Cred -->|No| UseEnv["provision_provider_keys()<br/>→ env vars → AIFactory"]

    UseCred --> Esperanto["Esperanto (8+ providers)"]
    UseEnv --> Esperanto

    Esperanto --> LC["to_langchain()<br/>→ LangChain model"]

    style AI fill:#fff3e0
```

---

## 8. Database Repository Pattern

```mermaid
flowchart TB
    subgraph Repository["open_notebook/database/repository.py"]
        DBConn["db_connection()<br/>Async context manager"]
        Query["repo_query()"]
        Create["repo_create()"]
        Update["repo_update()"]
        Upsert["repo_upsert()"]
        Delete["repo_delete()"]
        Relate["repo_relate()"]
        Insert["repo_insert()"]
    end

    subgraph Migration["open_notebook/database/async_migrate.py"]
        Manager["AsyncMigrationManager"]
        Migrations["14 migrations<br/>(001 to 014)"]
        Tracker["_sbl_migrations table"]
    end

    subgraph SurrealDB["SurrealDB (port 8000)"]
        NS["Namespace<br/>open_notebook"]
        DBname["Database<br/>open_notebook"]
        Tables["Tables + Graph Relations"]
        Vectors["Vector embeddings"]
    end

    Repository -->|"AsyncSurreal"| SurrealDB
    Manager -->|"run on startup"| Migrations
    Migrations -->|"track in"| Tracker

    style Database fill:#e8f5e9
```

---

## 9. Async Job Command Flow

```mermaid
flowchart LR
    subgraph Submit["Submit Phase"]
        API["API Request"] --> Router["Router"]
        Router --> Service["Service.submit_command()"]
        Service --> Queue["surreal_commands<br/>submit_command()"]
    end

    subgraph Execute["Execute Phase (async)"]
        Queue --> Handler["Command Handler"]
        Handler --> Embed["embed_source_command"]
        Handler --> Insight["create_insight_command"]
        Handler --> Transform["run_transformation_command"]
        Handler --> Podcast["generate_podcast_command"]
    end

    subgraph Update["Update Phase"]
        Embed --> Repo["Domain.save()"]
        Embed --> Command["repo_update command status"]
        Insight --> Repo
        Transform --> Repo
        Podcast --> Repo
    end

    subgraph Poll["Poll Phase"]
        Client["Frontend"] --> Status["GET /api/commands/{id}"]
        Status --> Command
    end

    style Commands fill:#fce4ec
```

---

## 10. Frontend State Management

```mermaid
flowchart TB
    subgraph Stores["Zustand Stores"]
        Auth["auth-store.ts<br/>token, isAuthenticated<br/>localStorage persist"]
        Sidebar["sidebar-store.ts<br/>collapsed state"]
        Theme["theme-store.ts<br/>light/dark/system"]
        Columns["notebook-columns-store.ts<br/>Sources/Notes collapse"]
    end

    subgraph Client["Axios Client (lib/api/client.ts)"]
        Interceptor1["Request: Bearer token + API URL"]
        Interceptor2["Response: 401 → clear auth → /login"]
    end

    subgraph Query["TanStack Query"]
        Notebooks["useNotebooks, useNotebook"]
        Sources["useSources, useNotebookSources"]
        Chat["useNotebookChat (SSE)"]
        Search["useSearch, useAsk (SSE)"]
        Models["useModels, useCredentials"]
    end

    Stores --> Client
    Client --> Query

    style Frontend fill:#e1f5fe
```

---

## 11. Error Handling Flow

```mermaid
flowchart TB
    LLM["LLM API Call"] --> Exception
    Exception --> classify["classify_error(e)"]
    classify --> Match{"Keyword match"}
    Match -->|"401"| AuthErr["AuthenticationError"]
    Match -->|"rate limit"| RateErr["RateLimitError"]
    Match -->|"not found"| NotFound["NotFoundError"]
    Match -->|"network"| NetworkErr["NetworkError"]
    Match -->|"config"| ConfigErr["ConfigurationError"]
    Match -->|"other"| External["ExternalServiceError"]

    AuthErr --> Handler1["api/main.py<br/>→ HTTP 401"]
    RateErr --> Handler2["→ HTTP 429"]
    NotFound --> Handler3["→ HTTP 404"]
    NetworkErr --> Handler4["→ HTTP 502"]
    ConfigErr --> Handler5["→ HTTP 422"]
    External --> Handler6["→ HTTP 502"]

    style ErrorHandling fill:#ffebee
```

---

## 12. Content Processing Pipeline

```mermaid
flowchart TB
    Input["File/URL Upload"] --> Extract["content-core<br/>extract_content()"]
    Extract --> Type{"Content type?"}
    Type -->|HTML| HTML["HTMLHeaderTextSplitter"]
    Type -->|Markdown| MD["MarkdownHeaderTextSplitter"]
    Type -->|Plain| Plain["RecursiveCharacterTextSplitter"]

    HTML --> Chunk["chunk_text()<br/>CHUNK_SIZE=400 tokens<br/>OVERLAP=60 tokens"]
    MD --> Chunk
    Plain --> Chunk

    Chunk --> Short{"text length?"}
    Short -->|small| Direct["direct embedding"]
    Short -->|large| Batch["chunk → embed each → mean pool"]

    Direct --> VectorDB["fn::vector_search()<br/>minimum_score=0.2"]
    Batch --> VectorDB

    style Pipeline fill:#e8f5e9
```

---

## 13. Multi-Provider AI (Esperanto)

```mermaid
flowchart TB
    subgraph Providers["8+ AI Providers"]
        OpenAI["OpenAI<br/>gpt-4, gpt-3.5"]
        Anthropic["Anthropic<br/>claude-3-opus"]
        Google["Google<br/>gemini-1.5-pro"]
        Groq["Groq<br/>llama-3.1-70b"]
        Ollama["Ollama<br/>local models"]
        Mistral["Mistral<br/>mistral-large"]
        DeepSeek["DeepSeek<br/>deepseek-chat"]
        XAI["xAI<br/>grok-1"]
    end

    subgraph Esperanto["Esperanto Library"]
        Factory["AIFactory.create_*()<br/>create_language()<br/>create_embedding()<br/>create_speech_to_text()<br/>create_text_to_speech()"]
        Cache["Internal model cache"]
    end

    subgraph Config["Configuration"]
        Env["Environment Variables"]
        Creds["Credential records (encrypted)"]
    end

    Providers --> Factory
    Config --> Factory
    Factory --> Cache

    style AI fill:#fff3e0
```

---

## 14. File Upload Flow

```mermaid
sequenceDiagram
    participant User
    participant FE as Frontend
    participant API as API
    participant Router as sources router
    participant Service as sources_service
    participant Graph as source_graph
    participant Content as content-core
    participant Domain as Source
    participant DB as SurrealDB

    User->>FE: Select file (PDF/audio/video)
    FE->>FE: JSON.stringify metadata
    FE->>FE: Append to FormData
    FE->>API: POST /api/sources (FormData)
    API->>Router: route matching
    Router->>Service: create_source()
    Service->>Graph: source_graph.ainvoke()
    Graph->>Content: extract_content(file)
    Content-->>Graph: content_state
    Graph->>Domain: Source(**content_state)
    Domain->>DB: repo_create("sources", data)
    DB-->>Domain: source:xxx
    Domain->>Graph: source_id
    Graph->>Graph: submit_command("embed_source", source_id)
    Graph-->>Service: result
    Service-->>Router: SourceResponse
    Router-->>FE: 201 Created

    Note over FE,DB: File extraction happens in source_graph
    Note over Graph: Embedding is fire-and-forget (async job)
```

---

## 15. Search + Ask Flow

```mermaid
flowchart TB
    subgraph Ask_Workflow["ask.py Workflow"]
        Start["User question"] --> Entry["ask/entry.jinja<br/>generate search strategy"]
        Entry --> JSON["Strategy (JSON)<br/>searches: [{term, instructions}]"]
        JSON --> Split["Fan-out (Send)"]
        Split --> P1["Parallel: query_process.jinja"]
        Split --> P2["Parallel: query_process.jinja"]
        Split --> PN["Parallel: query_process.jinja"]
        P1 --> A1["Sub-answer 1"]
        P2 --> A2["Sub-answer 2"]
        PN --> AN["Sub-answer N"]
        A1 --> Synth["ask/final_answer.jinja<br/>synthesize"]
        A2 --> Synth
        AN --> Synth
        Synth --> Final["Final answer<br/>[source:id] citations"]
    end

    style Ask_Workflow fill:#fce4ec
```

---

## 16. Podcast Generation Flow

```mermaid
flowchart LR
    subgraph Submit["User Request"]
        U["POST /api/podcasts/generate"]
    end

    subgraph Profile["Load Profiles"]
        SP["SpeakerProfile<br/>resolve_tts_config()"]
        EP["EpisodeProfile<br/>resolve_outline_config()<br/>resolve_transcript_config()"]
    end

    subgraph Outline["Outline Generation"]
        OL["podcast/outline.jinja"]
        OLLM["outline_llm model"]
    end

    subgraph Transcript["Transcript Generation"]
        TR["podcast/transcript.jinja"]
        TRLLM["transcript_llm model"]
    end

    subgraph TTS["Text-to-Speech"]
        Voice["voice_model (TTS)"]
        Audio["Audio segments"]
    end

    U --> SP
    U --> EP
    SP --> Voice
    EP --> OLLM
    EP --> TRLLM
    OLLM --> OL
    OL --> TR
    TR --> Voice
    Voice --> Audio

    style Podcast fill:#e1f5fe
```

---

## 17. Credential Encryption Flow

```mermaid
flowchart TB
    subgraph Store["Store Credential"]
        Input["API Key Input"]
        Key["OPEN_NOTEBOOK_ENCRYPTION_KEY"]
        Encrypt["Fernet encrypt_value()"]
        Save["repo_create(credentials)"]
        Input --> Encrypt
        Key --> Encrypt
        Encrypt --> Save
    end

    subgraph Retrieve["Retrieve Credential"]
        Query["repo_query(credentials)"]
        Decrypt["Fernet decrypt_value()"]
        SecretStr["Pydantic SecretStr"]
        Query --> Decrypt
        Decrypt --> SecretStr
    end

    subgraph Use["Use in AI Provisioning"]
        SecretStr --> Config["credential.to_esperanto_config()"]
        Config --> Factory["AIFactory.create_*()"]
        Factory --> Model["Esperanto model"]
    end

    style Security fill:#ffebee
```

---

## 18. Project Directory Tree (Mermaid)

```mermaid
graph TD
    Root["open-notebook/"] --> Frontend["frontend/"]
    Root --> API["api/"]
    Root --> Core["open_notebook/"]
    Root --> Commands["commands/"]
    Root --> Prompts["prompts/"]
    Root --> Docs["docs/"]
    Root --> Tests["tests/"]

    Frontend --> FE_SRC["src/"]
    FE_SRC --> FE_APP["app/"]
    FE_SRC --> FE_COMP["components/"]
    FE_SRC --> FE_LIB["lib/"]

    FE_LIB --> FE_API["api/"]
    FE_LIB --> FE_HOOKS["hooks/"]
    FE_LIB --> FE_STORES["stores/"]
    FE_LIB --> FE_TYPES["types/"]
    FE_LIB --> FE_LOCALES["locales/"]

    API --> API_ROUTERS["routers/"]
    API --> API_SERVICES["*_service.py"]

    Core --> CORE_AI["ai/"]
    Core --> CORE_DOMAIN["domain/"]
    Core --> CORE_GRAPHS["graphs/"]
    Core --> CORE_DB["database/"]
    Core --> CORE_UTILS["utils/"]
    Core --> CORE_PODCASTS["podcasts/"]

    Prompts --> PR_ASK["ask/"]
    Prompts --> PR_CHAT["chat/"]
    Prompts --> PR_SOURCE["source_chat/"]
    Prompts --> PR_PODCAST["podcast/"]

    style Root fill:#f5f5f5
    style Frontend fill:#e1f5fe
    style API fill:#fff3e0
    style Core fill:#e8f5e9
```