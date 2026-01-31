# Domain Module

Core data models for notebooks, sources, notes, and settings with async SurrealDB persistence, auto-embedding, and relationship management.

## Purpose

Two base classes support different persistence patterns: **ObjectModel** (mutable records with auto-increment IDs) and **RecordModel** (singleton configuration with fixed IDs).

## Key Components

### base.py
- **ObjectModel**: Base for notebooks, sources, notes
  - `save()`: Create/update with auto-embedding for searchable content
  - `delete()`: Remove by ID
  - `relate(relationship, target_id)`: Create graph relationships (reference, artifact, refers_to)
  - `get(id)`: Polymorphic fetch; resolves subclass from ID prefix
  - `get_all(order_by)`: Fetch all records from table
  - Integrates with ModelManager for automatic embedding

- **RecordModel**: Singleton configuration (ContentSettings, DefaultPrompts)
  - Fixed record_id per subclass
  - `update()`: Upsert to database
  - Lazy DB loading via `_load_from_db()`

### notebook.py
- **Notebook**: Research project container
  - `get_sources()`, `get_notes()`, `get_chat_sessions()`: Navigate relationships
  - `get_delete_preview()`: Returns counts of notes, exclusive sources, and shared sources that would be affected by deletion
  - `delete(delete_exclusive_sources)`: Cascade deletion - always deletes notes, optionally deletes exclusive sources, always unlinks all sources

- **Source**: Content item (file/URL)
  - `vectorize()`: Submit async embedding job (returns command_id, fire-and-forget)
  - `get_status()`, `get_processing_progress()`: Track job via surreal_commands
  - `get_context()`: Returns summary for LLM context
  - `add_insight()`: Submit async insight creation via `create_insight_command` (fire-and-forget, returns command_id)

- **Note**: Standalone or linked notes
  - `save()`: Submits `embed_note` command after save (fire-and-forget)
  - `add_to_notebook()`: Link to notebook

- **SourceInsight, SourceEmbedding**: Derived content models
- **ChatSession**: Conversation container with optional model_override
- **Asset**: File/URL reference helper

- **Search functions**:
  - `text_search()`: Full-text keyword search
  - `vector_search()`: Semantic search via embeddings (default minimum_score=0.2)

### content_settings.py
- **ContentSettings**: Singleton for processing engines, embedding strategy, file deletion, YouTube languages

### transformation.py
- **Transformation**: Reusable prompts for content transformation
- **DefaultPrompts**: Singleton with transformation instructions

### api_key_config.py
- **APIKeyConfig**: Singleton configuration for API keys and provider credentials
  - **33+ configuration fields** organized by provider type:
    - **Simple Providers**: `openai_api_key`, `anthropic_api_key`, `google_api_key`, `groq_api_key`, `mistral_api_key`, `deepseek_api_key`, `xai_api_key`, `openrouter_api_key`, `voyage_api_key`, `elevenlabs_api_key`
    - **URL-based Providers**: `ollama_api_base`
    - **Google Vertex AI**: `vertex_project`, `vertex_location`, `google_application_credentials`
    - **Azure OpenAI**: `azure_openai_api_key`, `azure_openai_api_version`, `azure_openai_endpoint`, plus service-specific endpoints (LLM, embedding, STT, TTS)
    - **OpenAI-Compatible**: Generic (`openai_compatible_api_key`, `openai_compatible_base_url`) and service-specific variants (LLM, embedding, STT, TTS)
  - **SecretStr protection**: API key fields use Pydantic's `SecretStr` (values masked in logs/repr)
  - **Encryption integration**: Uses `encrypt_value()`/`decrypt_value()` from `open_notebook.utils.encryption`
    - Keys encrypted with Fernet before database storage
    - Requires `OPEN_NOTEBOOK_ENCRYPTION_KEY` environment variable (warns if not set)
  - **Fresh fetch pattern**: `get_instance()` always queries database (no caching) to ensure latest values
  - **Custom serialization**: `_prepare_save_data()` extracts SecretStr values and encrypts before storage

## Important Patterns

- **Async/await**: All DB operations async; always use await
- **Polymorphic get()**: `ObjectModel.get(id)` determines subclass from ID prefix (table:id format)
- **Fire-and-forget embedding**: Models submit embed_* commands after save via `submit_command()` (non-blocking)
- **Nullable fields**: Declare via `nullable_fields` ClassVar to allow None in database
- **Timestamps**: `created` and `updated` auto-managed as ISO strings
- **Fire-and-forget jobs**: `source.vectorize()` returns command_id without waiting

## Key Dependencies

- `surrealdb`: RecordID type for relationships
- `pydantic`: Validation and field_validator decorators
- `open_notebook.database.repository`: CRUD and relationship functions
- `open_notebook.ai.models`: ModelManager for embeddings
- `surreal_commands`: Async job submission (vectorization, insights)
- `loguru`: Logging

## Quirks & Gotchas

- **Polymorphic resolution**: `ObjectModel.get()` fails if subclass not imported (search subclasses list)
- **RecordModel singleton**: __new__ returns existing instance; call `clear_instance()` in tests
- **Source.command field**: Stored as RecordID; auto-parsed from strings via field_validator
- **Text truncation**: `Note.get_context(short)` hardcodes 100-char limit
- **Auto-embedding behavior**:
  - `Note.save()` → auto-submits `embed_note` command
  - `Source.save()` → does NOT auto-submit (must call `vectorize()` explicitly)
  - `Source.add_insight()` → submits `create_insight_command` which handles DB insert + `embed_insight` command (all fire-and-forget)
- **Relationship strings**: Must match SurrealDB schema (reference, artifact, refers_to)

## How to Add New Model

1. Inherit from ObjectModel with table_name ClassVar
2. Define Pydantic fields with validators
3. Override `save()` to submit embedding command if searchable (use `submit_command("embed_*", id)`)
4. Add custom methods for domain logic (get_X, add_to_Y)
5. Implement `_prepare_save_data()` if custom serialization needed

## Usage

```python
notebook = Notebook(name="Research", description="My project")
await notebook.save()

obj = await ObjectModel.get("notebook:123")  # Polymorphic fetch

# Search
await text_search("quantum", results=5)
await vector_search("quantum computing", results=10, minimum_score=0.3)
```
