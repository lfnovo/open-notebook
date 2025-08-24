# Source Graph Update Summary

## Overview
Updated the `open_notebook/graphs/source.py` to support multi-notebook associations and source updates instead of creation, as requested.

## Changes Made

### 1. Updated SourceState TypedDict
**Before:**
```python
class SourceState(TypedDict):
    content_state: ProcessSourceState
    apply_transformations: List[Transformation]
    notebook_id: str  # Single notebook
    source: Source
    transformation: Annotated[list, operator.add]
    embed: bool
```

**After:**
```python
class SourceState(TypedDict):
    content_state: ProcessSourceState
    apply_transformations: List[Transformation]
    source_id: str  # NEW: Pre-existing source ID
    notebook_ids: List[str]  # CHANGED: Multiple notebooks
    source: Source
    transformation: Annotated[list, operator.add]
    embed: bool
```

### 2. Updated save_source() Function
**Key Changes:**
- **Source Updates Instead of Creation:** Uses `Source.get(source_id)` to retrieve existing source
- **Multi-notebook Support:** Loops through `notebook_ids` list to associate with multiple notebooks
- **Title Preservation:** Preserves existing title if processed content doesn't provide one
- **Empty ID Handling:** Skips empty/None notebook IDs gracefully
- **Error Handling:** Raises ValueError if source_id doesn't exist

**Before:**
```python
async def save_source(state: SourceState) -> dict:
    content_state = state["content_state"]

    source = Source(  # Created new source
        asset=Asset(url=content_state.url, file_path=content_state.file_path),
        full_text=content_state.content,
        title=content_state.title,
    )
    await source.save()

    if state["notebook_id"]:  # Single notebook
        logger.debug(f"Adding source to notebook {state['notebook_id']}")
        await source.add_to_notebook(state["notebook_id"])
    # ...
```

**After:**
```python
async def save_source(state: SourceState) -> dict:
    content_state = state["content_state"]

    # Get existing source using the provided source_id
    source = await Source.get(state["source_id"])
    if not source:
        raise ValueError(f"Source with ID {state['source_id']} not found")

    # Update the source with processed content
    source.asset = Asset(url=content_state.url, file_path=content_state.file_path)
    source.full_text = content_state.content
    
    # Preserve existing title if none provided in processed content
    if content_state.title:
        source.title = content_state.title
    
    await source.save()

    # Handle multiple notebook associations
    notebook_ids = state.get("notebook_ids", [])
    if notebook_ids:
        for notebook_id in notebook_ids:
            if notebook_id:  # Skip empty/None notebook IDs
                logger.debug(f"Adding source to notebook {notebook_id}")
                await source.add_to_notebook(notebook_id)
    # ...
```

## Preserved Functionality
- ✅ All transformation processing logic unchanged
- ✅ Embedding/vectorization logic unchanged  
- ✅ Error handling patterns maintained
- ✅ Existing return format preserved
- ✅ Graph structure and workflow unchanged
- ✅ All imports and dependencies maintained

## Usage Examples

### Basic Source Update
```python
state = {
    "content_state": processed_content,
    "source_id": "source:existing_id",
    "notebook_ids": ["notebook:nb1", "notebook:nb2"],
    "apply_transformations": [],
    "embed": True
}

result = await source_graph.ainvoke(state)
```

### Handling Empty Notebooks
```python
state = {
    "source_id": "source:existing_id", 
    "notebook_ids": [],  # Empty list - no associations
    # ... other fields
}
```

### Title Preservation
```python
# If content_state.title is None/empty, existing source title is preserved
# If content_state.title has value, source title is updated
```

## Backward Compatibility Notes
- **Breaking Change:** `notebook_id` field changed to `notebook_ids` 
- **Breaking Change:** `source_id` field is now required
- **Behavior Change:** Updates existing sources instead of creating new ones
- **New Requirement:** Source must exist before graph execution

## Testing
Created `test_source_graph_updates.py` to verify:
- ✅ Source update functionality
- ✅ Multi-notebook association
- ✅ Empty notebook IDs handling
- ✅ Title preservation logic
- ✅ Error handling for non-existent sources

## Files Modified
1. `/open_notebook/graphs/source.py` - Main implementation
2. `test_source_graph_updates.py` - Test verification (new file)
3. `source_graph_update_summary.md` - This documentation (new file)