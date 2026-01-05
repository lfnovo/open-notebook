# Utils Module

Utility functions and helpers for context building, text processing, tokenization, and versioning.

## Purpose

Provides cross-cutting concerns: building LLM context from sources/insights, text utilities (truncation, cleaning), token counting, and version management.

## Architecture Overview

**Four core utilities**:
1. **context_builder.py**: Flexible context assembly from sources, notes, insights with token budgeting
2. **text_utils.py**: Text truncation, whitespace cleaning, formatting helpers
3. **token_utils.py**: Token counting for LLM context windows (wrapper around encoding library)
4. **version_utils.py**: Version parsing, comparison, and schema compatibility checks

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

### text_utils.py
- **truncate_text(text, max_chars, suffix="...")**: Truncates string, adds ellipsis
- **clean_text(text)**: Removes extra whitespace, normalizes newlines
- **extract_sentences(text, max_count)**: Splits text into sentences up to limit
- **normalize_whitespace(text)**: Collapse multiple spaces/newlines into single
- **format_for_llm(text)**: Combines cleaning + normalization for LLM consumption

**Key behavior**: All functions are pure (no side effects); safe for high-volume processing

### token_utils.py
- **token_count(text)**: Returns estimated token count for string (via encoding library)
- **remaining_tokens(max_tokens, used)**: Returns remaining tokens in budget
- **fits_in_context(text, max_tokens)**: Boolean check if text fits token budget

**Key behavior**: Uses fixed encoding (cl100k_base for GPT models); may differ slightly from actual model tokenization

### version_utils.py
- **parse_version(version_string)**: Parses "1.2.3" format; returns Version namedtuple
- **compare_versions(v1, v2)**: Returns -1 (v1 < v2), 0 (equal), 1 (v1 > v2)
- **is_compatible(current, required)**: Checks if current version meets requirement (e.g., current >= required)
- **schema_version_check()**: Validates database schema version on startup

**Key behavior**: Assumes semantic versioning (MAJOR.MINOR.PATCH); non-standard formats raise ValueError

## Common Patterns

- **Dataclass-driven config**: ContextConfig used by ContextBuilder (immutable after init)
- **Token budgeting**: ContextBuilder respects max_tokens constraint; prioritizes high-priority items
- **Error handling resilience**: token_count() returns estimate; context_builder catches DB errors gracefully
- **Pure text functions**: text_utils functions are stateless utilities (no class needed)
- **Lazy evaluation**: ContextBuilder doesn't fetch items until build() called
- **Type hints throughout**: All functions use Optional, List, Dict for clarity

## Key Dependencies

- `open_notebook.domain.notebook`: Source, Note, SourceInsight models; vector_search function
- `open_notebook.exceptions`: DatabaseOperationError, NotFoundError
- `tiktoken` (via token_utils.py): Token encoding for GPT models
- `loguru`: Logging in context_builder (debug-level)

## Important Quirks & Gotchas

- **Token count estimation**: Uses cl100k_base encoding; may differ 5-10% from actual model tokens
- **Priority weights default**: If not specified, ContextConfig uses default weights (source=1, note=0.8, insight=1.2)
- **Vector search required**: ContextBuilder assumes vector_search is available on Notebook model; fails if not
- **Source.full_text vs content**: Uses full_text field (may include extracted text + metadata)
- **Type-specific fetch logic**: ContextItem.content stores raw dict; caller must parse (e.g., dict["content"])
- **Circular import risk**: context_builder imports from domain.notebook; avoid domain importing utils
- **Max tokens hard limit**: ContextBuilder stops adding items once max_tokens exceeded (not prorated)
- **No caching**: Every build() call re-fetches from database (use cache layer if needed)
- **Whitespace normalization lossy**: clean_text() may change intended formatting (code blocks, poetry, etc.)

## How to Extend

1. **Add new context source type**: Create fetch method in ContextBuilder; update ContextConfig.sources dict
2. **Add text preprocessing**: Add new function to text_utils (e.g., remove_urls, extract_keywords)
3. **Change tokenization**: Replace tiktoken with alternative library in token_utils; update all calls
4. **Add context filtering**: Extend ContextConfig with filter_by_date, filter_by_topic fields
5. **Implement caching**: Wrap ContextBuilder.build() with functools.lru_cache (be aware of mutability)

## Usage Example

```python
from open_notebook.utils.context_builder import ContextBuilder, ContextConfig

config = ContextConfig(
    sources={"source:123": "full", "source:456": "summary"},
    max_tokens=2000,
)
builder = ContextBuilder(notebook, config)
context_items = await builder.build()

# context_items is List[ContextItem] sorted by priority
for item in context_items:
    print(f"{item.type}:{item.id} ({item.token_count} tokens)")
```
