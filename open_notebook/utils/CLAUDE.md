# Utils Module

Utility functions and helpers for context building, text processing, chunking, embedding, tokenization, and versioning.

## Purpose

Provides cross-cutting concerns: building LLM context from sources/insights, content-type aware text chunking, unified embedding generation with mean pooling, token counting, and version management.

## Architecture Overview

**Six core utilities**:
1. **context_builder.py**: Flexible context assembly from sources, notes, insights with token budgeting
2. **chunking.py**: Content-type detection and smart text chunking for embedding operations
3. **embedding.py**: Unified embedding generation with mean pooling for large content
4. **text_utils.py**: Text cleaning and thinking content extraction
5. **token_utils.py**: Token counting for LLM context windows (wrapper around encoding library)
6. **version_utils.py**: Version parsing, comparison, and schema compatibility checks

Each utility is stateless and can be imported independently.

## Component Catalog

### context_builder.py
- **ContextItem**: Dataclass for individual context piece (id, type, content, priority, token_count)
- **ContextConfig**: Configuration for context building (sources/notes/insights selection, max tokens, priority weights)
- **ContextBuilder**: Main class assembling context
  - `add_source()`: Include source by ID with inclusion level
  - `add_note()`: Include note by ID
  - `add_insight()`: Include insight by ID
  - `build()`: Assemble context respecting token budget and priorities
  - Uses vector_search to fetch source/insight content from SurrealDB
  - Returns list of ContextItem objects sorted by priority

**Key behavior**:
- Token counting is automatic (calculated in ContextItem.__post_init__)
- Max token enforcement via priority weighting (higher priority items included first)
- Type-specific fetching: sources → Source.full_text, notes → Note.content, insights → SourceInsight.content
- Raises DatabaseOperationError if source/note fetch fails

### chunking.py
- **ContentType**: Enum (HTML, MARKDOWN, PLAIN)
- **CHUNK_SIZE**: constant
- **CHUNK_OVERLAP**: constant
- **detect_content_type_from_extension(file_path)**: Detect type from file extension
- **detect_content_type_from_heuristics(text)**: Detect type from content patterns (returns type + confidence)
- **detect_content_type(text, file_path)**: Combined detection (extension primary, heuristics fallback)
- **chunk_text(text, content_type, file_path)**: Split text using appropriate splitter

**Key behavior**:
- Uses LangChain splitters: HTMLHeaderTextSplitter, MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
- Extension-based detection is primary; heuristics can override PLAIN extensions with 0.8+ confidence
- Secondary chunking applied when HTML/Markdown splitters produce oversized chunks
- Returns list of strings, each ≤ CHUNK_SIZE characters

### embedding.py
- **mean_pool_embeddings(embeddings)**: Combine multiple embeddings via normalized mean pooling
- **generate_embeddings(texts)**: Batch embedding via single Esperanto API call
- **generate_embedding(text, content_type, file_path)**: Unified embedding with automatic chunking + mean pooling

**Key behavior**:
- Uses model_manager.get_model("embedding") for embedding model
- Short text (≤ CHUNK_SIZE): direct embedding
- Long text: chunk → embed each → mean pool results
- Mean pooling: normalize each → mean → normalize result (using numpy)
- Raises ValueError for empty/whitespace-only text

### text_utils.py
- **remove_non_ascii(text)**: Remove non-ASCII characters from text
- **remove_non_printable(text)**: Remove non-printable characters, preserving newlines/tabs
- **parse_thinking_content(content)**: Extract `<think>` tags content from AI responses
- **clean_thinking_content(content)**: Remove `<think>` blocks, return cleaned content only

**Key behavior**:
- parse_thinking_content handles malformed output (missing opening `<think>` tag)
- Large content (>100KB) bypasses thinking extraction for performance
- Non-string input returns empty thinking and stringified content

### token_utils.py
- **token_count(text)**: Returns estimated token count for string (via tiktoken)
- **token_cost(text, model)**: Calculate cost estimate for text with given model

**Key behavior**: Uses cl100k_base encoding; may differ slightly from actual model tokenization

### version_utils.py
- **compare_versions(v1, v2)**: Returns -1 (v1 < v2), 0 (equal), 1 (v1 > v2)
- **get_installed_version(package)**: Get version of installed Python package
- **get_version_from_github(url)**: Fetch latest version from GitHub releases

**Key behavior**: Uses packaging library for version parsing; supports pre-release tags

## Common Patterns

- **Dataclass-driven config**: ContextConfig used by ContextBuilder (immutable after init)
- **Token budgeting**: ContextBuilder respects max_tokens constraint; prioritizes high-priority items
- **Content-type aware processing**: Chunking uses appropriate splitter based on detected content type
- **Mean pooling for large content**: Embedding handles arbitrarily large text via chunking + pooling
- **Error handling resilience**: token_count() returns estimate; context_builder catches DB errors gracefully
- **Pure text functions**: text_utils functions are stateless utilities (no class needed)
- **Lazy evaluation**: ContextBuilder doesn't fetch items until build() called
- **Type hints throughout**: All functions use Optional, List, Dict for clarity

## Key Dependencies

- `open_notebook.domain.notebook`: Source, Note, SourceInsight models; vector_search function
- `open_notebook.ai.models`: model_manager for embedding model access
- `open_notebook.exceptions`: DatabaseOperationError, NotFoundError
- `langchain_text_splitters`: HTMLHeaderTextSplitter, MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
- `numpy`: Mean pooling calculations
- `tiktoken`: Token encoding for GPT models
- `loguru`: Logging throughout

## Important Quirks & Gotchas

- **Token count estimation**: Uses cl100k_base encoding; may differ 5-10% from actual model tokens
- **Chunk size for Ollama**: 1500 chars chosen to fit within Ollama embedding model context limits
- **Content type detection order**: Extension checked first, then heuristics; high-confidence heuristics (≥0.8) can override PLAIN extensions
- **Mean pooling normalization**: Each embedding normalized before mean, result normalized after
- **Priority weights default**: If not specified, ContextConfig uses default weights (source=1, note=0.8, insight=1.2)
- **Vector search required**: ContextBuilder assumes vector_search is available on Notebook model; fails if not
- **Circular import risk**: context_builder imports from domain.notebook; avoid domain importing utils
- **Max tokens hard limit**: ContextBuilder stops adding items once max_tokens exceeded (not prorated)
- **No caching**: Every build() call re-fetches from database (use cache layer if needed)

## How to Extend

1. **Add new context source type**: Create fetch method in ContextBuilder; update ContextConfig.sources dict
2. **Add content type**: Add to ContentType enum; create splitter getter; update chunk_text()
3. **Change chunk size**: Modify CHUNK_SIZE and CHUNK_OVERLAP constants in chunking.py
4. **Add text preprocessing**: Add new function to text_utils (e.g., remove_urls, extract_keywords)
5. **Change tokenization**: Replace tiktoken with alternative library in token_utils; update all calls
6. **Add context filtering**: Extend ContextConfig with filter_by_date, filter_by_topic fields

## Usage Examples

### Chunking
```python
from open_notebook.utils.chunking import chunk_text, detect_content_type, ContentType

# Auto-detect content type and chunk
chunks = chunk_text(long_text, file_path="document.md")

# Explicit content type
chunks = chunk_text(html_content, content_type=ContentType.HTML)
```

### Embedding
```python
from open_notebook.utils.embedding import generate_embedding, generate_embeddings

# Single text (handles chunking + mean pooling automatically)
embedding = await generate_embedding(long_text)

# Batch embedding (more efficient for multiple texts)
embeddings = await generate_embeddings(["text1", "text2", "text3"])
```

### Context Building
```python
from open_notebook.utils.context_builder import ContextBuilder, ContextConfig

config = ContextConfig(
    sources={"source:123": "full", "source:456": "summary"},
    max_tokens=2000,
)
builder = ContextBuilder(notebook, config)
context_items = await builder.build()

for item in context_items:
    print(f"{item.type}:{item.id} ({item.token_count} tokens)")
```

### encryption.py
- **get_secret_from_env(var_name)**: Retrieve secret from environment with Docker secrets support (checks VAR_FILE first, then VAR)
- **get_fernet()**: Get Fernet instance if valid encryption key is configured; returns None otherwise
- **encrypt_value(value)**: Encrypt a string using Fernet symmetric encryption; returns original value if encryption unavailable
- **decrypt_value(value)**: Decrypt a Fernet-encrypted string; gracefully falls back to original value for legacy/unencrypted data
- **generate_key()**: Generate a new Fernet encryption key for use as OPEN_NOTEBOOK_ENCRYPTION_KEY

**Purpose**: Provides field-level encryption for sensitive data (API keys) stored in the database. Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256) for authenticated encryption.

**Key behavior**:
- Key derivation priority: OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE (Docker secrets) → OPEN_NOTEBOOK_ENCRYPTION_KEY (env var) → default key (development only)
- Default key is NOT secure for production; always set your own key in production deployments
- Graceful fallback on decryption: InvalidToken errors (legacy unencrypted data) return the original value
- Encryption failure returns original value with error logging (never blocks operations)
- Module-level key initialization: `_ENCRYPTION_KEY` is set once at import time

**Security considerations**:
- Default key is derived from a known passphrase; provides no real security (development convenience only)
- Production deployments MUST set OPEN_NOTEBOOK_ENCRYPTION_KEY explicitly
- Docker secrets pattern supported for secure key injection in containerized environments
- Key rotation would require re-encrypting all stored keys (not currently implemented)
- Encryption is transparent to callers; unencrypted legacy data continues to work

**Usage Example**:
```python
from open_notebook.utils.encryption import encrypt_value, decrypt_value, generate_key

# Encrypt before storing in database
encrypted_api_key = encrypt_value(api_key)

# Decrypt when reading from database
decrypted_api_key = decrypt_value(encrypted_api_key)

# Generate a new key for OPEN_NOTEBOOK_ENCRYPTION_KEY
new_key = generate_key()
print(f"Add to .env: OPEN_NOTEBOOK_ENCRYPTION_KEY={new_key}")
```
