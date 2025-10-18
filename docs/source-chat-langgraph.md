# Source Chat Langgraph

The Source Chat Langgraph is a specialized conversation system designed for deep, contextual discussions about specific source documents within the Open Notebook project. It provides source-focused chat capabilities with automatic context building, insight integration, and conversation persistence.

## Overview

The Source Chat Langgraph enables users to have focused conversations about individual sources in their knowledge base. Unlike the general chat system, this specialized graph:

- **Focuses on a single source** and its related insights
- **Automatically builds context** using the ContextBuilder
- **Tracks referenced content** for citation purposes
- **Persists conversations** using SQLite checkpointer
- **Supports model override** functionality

## Architecture

### Core Components

1. **SourceChatState** - TypedDict defining the conversation state
2. **call_model_with_source_context** - Main processing function
3. **source_chat_graph** - Compiled Langgraph with checkpointer
4. **source_chat.jinja** - Specialized prompt template

### State Management

```python
class SourceChatState(TypedDict):
    messages: Annotated[list, add_messages]       # Conversation messages
    source_id: str                                # Required source identifier
    source: Optional[Source]                      # Loaded source object
    insights: Optional[List[SourceInsight]]       # Source insights
    context: Optional[str]                        # Formatted context
    model_override: Optional[str]                 # Optional model override
    context_indicators: Optional[Dict[str, List[str]]]  # Citation tracking
```

## Key Features

### 1. Automatic Context Building

The system uses the ContextBuilder to automatically gather relevant context:

```python
context_builder = ContextBuilder(
    source_id=source_id,
    include_insights=True,
    include_notes=False,  # Focus on source-specific content
    max_tokens=50000
)
context_data = await context_builder.build()
```

### 2. Specialized Prompt Template

The `source_chat.jinja` template provides:
- Source-specific instructions
- Proper citation formatting
- Context-aware conversation guidance
- Focus on single-source analysis

### 3. Citation Tracking

The system tracks which insights and content are referenced:

```python
context_indicators = {
    "sources": ["source:id1"],
    "insights": ["insight:id1", "insight:id2"],
    "notes": []
}
```

### 4. Model Override Support

Users can specify a particular model for the conversation:

```python
state = {
    # ... other fields ...
    "model_override": "model:specific_model_id"
}
```

### 5. Conversation Persistence

Using SQLite checkpointer with thread-based conversation management:

```python
config = {
    "configurable": {
        "thread_id": f"source_chat_{source_id}",
        "model_id": "optional_model_override"
    }
}
```

## Usage Examples

### Basic Source Chat

```python
from open_notebook.graphs.source_chat import source_chat_graph, SourceChatState
from langchain_core.messages import HumanMessage

async def basic_source_chat():
    state = SourceChatState(
        messages=[HumanMessage(content="What are the main insights from this source?")],
        source_id="source:example123",
        source=None,
        insights=None,
        context=None,
        model_override=None,
        context_indicators=None
    )
    
    config = {
        "configurable": {
            "thread_id": f"source_chat_example123",
        }
    }
    
    result = await source_chat_graph.ainvoke(state, config)
    return result
```

### Conversation Continuation

```python
async def continue_conversation():
    # Same thread_id continues the conversation
    follow_up_state = SourceChatState(
        messages=[HumanMessage(content="Can you elaborate on the first insight?")],
        source_id="source:example123",
        # ... other fields ...
    )
    
    config = {
        "configurable": {
            "thread_id": f"source_chat_example123",  # Same thread
        }
    }
    
    result = await source_chat_graph.ainvoke(follow_up_state, config)
    return result
```

### Model Override

```python
async def chat_with_specific_model():
    state = SourceChatState(
        messages=[HumanMessage(content="Provide a detailed analysis")],
        source_id="source:example123",
        model_override="model:claude-3-opus",  # Specific model
        # ... other fields ...
    )
    
    result = await source_chat_graph.ainvoke(state, config)
    return result
```

## Integration Points

### With ContextBuilder

The Source Chat integrates seamlessly with the ContextBuilder:

```python
# Automatic context building for the specified source
context_builder = ContextBuilder(
    source_id=source_id,
    include_insights=True,
    include_notes=False,
    max_tokens=50000
)
```

### With Model Management

Uses the existing model provisioning system:

```python
model = await provision_langchain_model(
    str(payload),
    model_override or config_model_id,
    "chat",
    max_tokens=10000,
)
```

### With Citation System

Automatically tracks and formats citations:

```python
# Citations are automatically included in context_indicators
{
    "sources": ["source:abc123"],
    "insights": ["insight:def456", "insight:ghi789"],
    "notes": []
}
```

## Prompt Template Structure

The `source_chat.jinja` template includes:

1. **System Role** - Defines the assistant as a source-focused researcher
2. **Capabilities** - Lists available analysis features
3. **Operating Method** - Instructions for source-specific analysis
4. **Source Information** - Dynamic source metadata
5. **Context Section** - Formatted source content and insights
6. **Citation Instructions** - Proper referencing guidelines
7. **Examples** - Sample interactions
8. **Conversation Focus** - Guidelines for source-specific discussions

## Error Handling

The system includes comprehensive error handling:

### Required Fields Validation

```python
if not source_id:
    raise ValueError("source_id is required in state")
```

### Context Building Errors

```python
try:
    context_data = await context_builder.build()
except Exception as e:
    logger.error(f"Failed to build context: {str(e)}")
    raise
```

### Model Provisioning Errors

```python
try:
    model = await provision_langchain_model(...)
except Exception as e:
    logger.error(f"Model provisioning failed: {str(e)}")
    raise
```

## Testing

The system includes comprehensive tests:

- **Unit Tests** - Individual component testing
- **Integration Tests** - Full workflow testing
- **Mock Tests** - External dependency testing
- **Validation Tests** - Input validation testing

Run tests with:

```bash
pytest tests/test_source_chat.py -v
```

## Configuration

### Environment Variables

The system respects standard Open Notebook configuration:

- `LANGGRAPH_CHECKPOINT_FILE` - SQLite checkpoint database location
- Model configuration through the model manager

### Thread Management

Thread IDs should follow the pattern:

```python
thread_id = f"source_chat_{source_id}"
```

This ensures conversation isolation per source.

## Best Practices

### 1. Source ID Management

Always use complete source IDs with table prefix:

```python
source_id = "source:abc123"  # Correct
source_id = "abc123"         # Will be converted automatically
```

### 2. Context Size Management

Use appropriate token limits:

```python
max_tokens = 50000  # Good for detailed source analysis
max_tokens = 20000  # Good for focused discussions
```

### 3. Thread ID Consistency

Use consistent thread IDs for conversation continuity:

```python
thread_id = f"source_chat_{source_id}"
```

### 4. Model Selection

Choose appropriate models for different use cases:

```python
# For detailed analysis
model_override = "model:claude-3-opus"

# For quick summaries  
model_override = "model:gpt-5-mini"
```

## Troubleshooting

### Common Issues

1. **Missing source_id** - Ensure source_id is provided in state
2. **Context building failures** - Check source exists in database
3. **Model provisioning errors** - Verify model configuration
4. **Citation issues** - Ensure proper ID formatting

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger("open_notebook.graphs.source_chat").setLevel(logging.DEBUG)
```

## Future Enhancements

Potential improvements for the Source Chat system:

1. **Multi-source comparison** - Compare insights across sources
2. **Advanced citation formats** - Enhanced referencing options
3. **Export capabilities** - Export conversations as notes
4. **Visual context** - Integration with source visualizations
5. **Collaborative features** - Shared source conversations

## Related Documentation

- [ContextBuilder Documentation](./context-builder.md)
- [Model Management](./model-management.md)
- [General Chat System](./chat-system.md)
- [Source Management](./source-management.md)