# ContextBuilder

A flexible and generic ContextBuilder class for the Open Notebook project that can handle any parameters and build context from sources, notebooks, insights, and notes.

## Features

- **Flexible Parameters**: Accepts any parameters via `**kwargs` for future extensibility
- **Priority-based Management**: Automatic prioritization and sorting of context items
- **Token Counting**: Built-in token counting and truncation to fit limits
- **Deduplication**: Automatic removal of duplicate items based on ID
- **Type-based Grouping**: Separates sources, notes, and insights in output
- **Async Support**: Fully async for database operations

## Basic Usage

```python
from open_notebook.utils.context_builder import ContextBuilder, ContextConfig

# Simple notebook context
builder = ContextBuilder(notebook_id="notebook:123")
context = await builder.build()

# Single source with insights
builder = ContextBuilder(
    source_id="source:456",
    include_insights=True,
    max_tokens=2000
)
context = await builder.build()
```

## Convenience Functions

```python
from open_notebook.utils.context_builder import (
    build_notebook_context,
    build_source_context,
    build_mixed_context
)

# Build notebook context
context = await build_notebook_context(
    notebook_id="notebook:123",
    max_tokens=5000
)

# Build single source context
context = await build_source_context(
    source_id="source:456",
    include_insights=True
)

# Build mixed context
context = await build_mixed_context(
    source_ids=["source:1", "source:2"],
    note_ids=["note:1", "note:2"],
    max_tokens=3000
)
```

## Advanced Configuration

```python
from open_notebook.utils.context_builder import ContextConfig

# Custom configuration
config = ContextConfig(
    sources={
        "source:doc1": "insights",
        "source:doc2": "full content", 
        "source:doc3": "not in"  # Exclude
    },
    notes={
        "note:summary": "full content",
        "note:draft": "not in"  # Exclude
    },
    include_insights=True,
    max_tokens=3000,
    priority_weights={
        "source": 120,  # Higher priority
        "note": 80,     # Medium priority  
        "insight": 100  # High priority
    }
)

builder = ContextBuilder(
    notebook_id="notebook:project",
    context_config=config
)
context = await builder.build()
```

## Programmatic Item Management

```python
from open_notebook.utils.context_builder import ContextItem

builder = ContextBuilder()

# Add custom items
item = ContextItem(
    id="source:important",
    type="source",
    content={"title": "Key Document", "summary": "..."},
    priority=150  # Very high priority
)
builder.add_item(item)

# Apply management operations
builder.remove_duplicates()
builder.prioritize()
builder.truncate_to_fit(1000)

context = builder._format_response()
```

## Flexible Parameters

The ContextBuilder accepts any parameters via `**kwargs`, making it extensible for future features:

```python
builder = ContextBuilder(
    notebook_id="notebook:123",
    include_insights=True,
    max_tokens=2000,
    
    # Custom parameters for future extensions
    user_id="user:456",
    custom_filter="advanced",
    experimental_feature=True
)

# Access custom parameters
user_id = builder.params.get('user_id')
```

## Output Format

The ContextBuilder returns a structured response:

```python
{
    "sources": [...],           # List of source contexts
    "notes": [...],             # List of note contexts  
    "insights": [...],          # List of insight contexts
    "total_tokens": 1234,       # Total token count
    "total_items": 10,          # Total number of items
    "notebook_id": "notebook:123",  # If provided
    "metadata": {
        "source_count": 5,
        "note_count": 3,
        "insight_count": 2,
        "config": {
            "include_insights": true,
            "include_notes": true,
            "max_tokens": 2000
        }
    }
}
```

## Architecture

The ContextBuilder follows these design principles:

1. **Separation of Concerns**: Context building, item management, and formatting are separate
2. **Extensibility**: Uses `**kwargs` and flexible configuration for future features
3. **Performance**: Token-aware truncation and efficient deduplication
4. **Type Safety**: Proper type hints and data classes for structure
5. **Error Handling**: Graceful handling of missing items and database errors

## Integration

The ContextBuilder integrates seamlessly with the existing Open Notebook architecture:

- Uses existing domain models (`Source`, `Notebook`, `Note`)
- Leverages the repository pattern for database access
- Follows the same async patterns as other services
- Integrates with the token counting utilities

## Error Handling

The ContextBuilder handles errors gracefully:

- Missing notebooks/sources/notes are logged but don't stop execution
- Database errors are wrapped in `DatabaseOperationError`
- Invalid parameters raise `InvalidInputError`
- All errors include detailed context information