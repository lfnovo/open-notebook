# Commands Module

**Purpose**: Defines async command handlers for long-running operations via `surreal-commands` job queue system.

## Key Components

### Embedding Commands

- **`embed_note_command`**: Embeds a single note using unified embedding pipeline with content-type aware processing. Uses MARKDOWN content type detection. Retry: 5 attempts, exponential jitter 1-60s.
- **`embed_insight_command`**: Embeds a single source insight. Uses MARKDOWN content type. Retry: 5 attempts, exponential jitter 1-60s.
- **`embed_source_command`**: Embeds a source by chunking full_text with content-type aware splitters (HTML, Markdown, plain), then batch embedding all chunks. Uses single Esperanto API call. Retry: 5 attempts, exponential jitter 1-60s.
- **`create_insight_command`**: Creates a source insight with automatic retry on transaction conflicts. Creates the DB record, then submits `embed_insight` command (fire-and-forget). Retry: 5 attempts, exponential jitter 1-60s. Used by `Source.add_insight()`.
- **`rebuild_embeddings_command`**: Submits individual embed_* commands for all sources/notes/insights. Returns immediately; actual embedding happens async. No retry (coordinator only).

### Other Commands

- **`process_source_command`**: Ingests content through `source_graph`, creates embeddings (optional), and generates insights. Retries on transaction conflicts (exp. jitter, max 15×, 1-120s).
- **`run_transformation_command`**: Runs a transformation on an existing source to generate an insight. Executes the transformation graph (LLM call) then creates insight via `create_insight_command`. Used by `POST /sources/{id}/insights` API endpoint. Retry: 5 attempts, exponential jitter 1-60s.
- **`generate_podcast_command`**: Creates podcasts via `podcast-creator` library using stored episode/speaker profiles.
- **`process_text_command`** (example): Test fixture for text operations (uppercase, lowercase, reverse, word_count).
- **`analyze_data_command`** (example): Test fixture for numeric aggregations.

## Important Patterns

- **Pydantic I/O**: All commands use `CommandInput`/`CommandOutput` subclasses for type safety and serialization.
- **Error handling**: Permanent errors (ValueError) return failure output; all other exceptions auto-retry via surreal-commands.
- **Retry configuration**: Uses `stop_on: [ValueError]` (blocklist approach) - retries all exceptions EXCEPT ValueError. This is more resilient than allowlist as new exception types auto-retry.
- **Fire-and-forget embedding**: Domain models submit embed_* commands via `submit_command()` without waiting. Commands process asynchronously.
- **Content-type aware chunking**: `embed_source_command` uses `chunk_text()` with automatic content type detection (HTML, Markdown, plain text) for optimal text splitting. Default: 1500 char chunks with 225 char overlap.
- **Batch embedding**: `embed_source_command` uses `generate_embeddings()` for single API call efficiency instead of per-chunk calls.
- **Mean pooling for large content**: `embed_note_command` and `embed_insight_command` use `generate_embedding()` which handles content larger than chunk size via mean pooling.
- **Model dumping**: Recursive `full_model_dump()` utility converts Pydantic models → dicts for DB/API responses.
- **Logging**: Uses `loguru.logger` throughout; logs execution start/end and key metrics (processing time, counts).
- **Time tracking**: All commands measure `start_time` → `processing_time` for monitoring.

## Dependencies

**External**: `surreal_commands` (command decorator, job queue, submit_command), `loguru`, `pydantic`, `podcast_creator`
**Internal**: `open_notebook.domain.notebook` (Source, Note, SourceInsight), `open_notebook.utils.chunking` (chunk_text, detect_content_type), `open_notebook.utils.embedding` (generate_embedding, generate_embeddings), `open_notebook.database.repository` (repo_query, repo_insert)

## Quirks & Edge Cases

- **source_commands**: `ensure_record_id()` wraps command IDs for DB storage; transaction conflicts trigger exponential backoff retry. ValueError exceptions are permanent (not retried).
- **embedding_commands**: Content type detection uses file extension as primary source, heuristics as fallback. Chunks >1800 chars trigger secondary splitting. Empty/whitespace-only content returns ValueError (not retried).
- **rebuild_embeddings_command**: Returns "jobs_submitted" not "processed_items" - embedding is async. Individual commands handle failures with their own retries.
- **podcast_commands**: Profiles loaded from SurrealDB by name (must exist); briefing can be extended with suffix. Episode records created mid-execution.
- **Example commands**: Accept optional `delay_seconds` for testing async behavior; not for production.

## Code Example

```python
@command("process_source", app="open_notebook", retry={
    "max_attempts": 5,
    "wait_strategy": "exponential_jitter",
    "stop_on": [ValueError],  # Don't retry validation errors
})
async def process_source_command(input_data: SourceProcessingInput) -> SourceProcessingOutput:
    start_time = time.time()
    try:
        transformations = [await Transformation.get(id) for id in input_data.transformations]
        source = await Source.get(input_data.source_id)
        result = await source_graph.ainvoke({...})
        return SourceProcessingOutput(success=True, ...)
    except ValueError as e:
        return SourceProcessingOutput(success=False, error_message=str(e))  # No retry
    except Exception as e:
        raise  # Retry all other exceptions
```
