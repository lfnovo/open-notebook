# Commands Module

**Purpose**: Defines async command handlers for long-running operations via `surreal-commands` job queue system.

## Key Components

- **`process_source_command`**: Ingests content through `source_graph`, creates embeddings (optional), and generates insights. Retries on transaction conflicts (exp. jitter, max 5×).
- **`embed_single_item_command`**: Embeds individual sources/notes/insights; splits content into chunks for vector storage.
- **`rebuild_embeddings_command`**: Bulk re-embed all/existing items with selective type filtering.
- **`generate_podcast_command`**: Creates podcasts via `podcast-creator` library using stored episode/speaker profiles.
- **`process_text_command`** (example): Test fixture for text operations (uppercase, lowercase, reverse, word_count).
- **`analyze_data_command`** (example): Test fixture for numeric aggregations.

## Important Patterns

- **Pydantic I/O**: All commands use `CommandInput`/`CommandOutput` subclasses for type safety and serialization.
- **Error handling**: Permanent errors return failure output; `RuntimeError` exceptions auto-retry via surreal-commands.
- **Model dumping**: Recursive `full_model_dump()` utility converts Pydantic models → dicts for DB/API responses.
- **Logging**: Uses `loguru.logger` throughout; logs execution start/end and key metrics (processing time, counts).
- **Time tracking**: All commands measure `start_time` → `processing_time` for monitoring.

## Dependencies

**External**: `surreal_commands` (command decorator, job queue), `loguru`, `pydantic`, `podcast_creator`
**Internal**: `open_notebook.domain.*` (Source, Note, Transformation), `open_notebook.graphs.source`, `open_notebook.ai.models`

## Quirks & Edge Cases

- **source_commands**: `ensure_record_id()` wraps command IDs for DB storage; transaction conflicts trigger exponential backoff retry (1-30s). Non-`RuntimeError` exceptions are permanent.
- **embedding_commands**: Queries DB directly for item state; chunk index must match source's chunk list. Model availability checked at command start.
- **podcast_commands**: Profiles loaded from SurrealDB by name (must exist); briefing can be extended with suffix. Episode records created mid-execution.
- **Example commands**: Accept optional `delay_seconds` for testing async behavior; not for production.

## Code Example

```python
@command("process_source", app="open_notebook", retry={...})
async def process_source_command(input_data: SourceProcessingInput) -> SourceProcessingOutput:
    start_time = time.time()
    try:
        transformations = [await Transformation.get(id) for id in input_data.transformations]
        source = await Source.get(input_data.source_id)
        result = await source_graph.ainvoke({...})
        return SourceProcessingOutput(success=True, ...)
    except RuntimeError as e:
        raise  # Retry this
    except Exception as e:
        return SourceProcessingOutput(success=False, error_message=str(e))
```
