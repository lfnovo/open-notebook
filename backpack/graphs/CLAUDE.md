# Graphs Module

LangGraph-based workflow orchestration for content processing, chat interactions, and AI-powered transformations.

## Key Components

- **`chat.py`**: Conversational agent with message history, notebook context, and model override support
- **`source_chat.py`**: Source-focused chat with ContextBuilder for insights/content injection and context tracking
- **`ask.py`**: Multi-search strategy agent (generates search terms, retrieves results, synthesizes answers)
- **`source.py`**: Content ingestion pipeline (extract → save → transform with content-core)
- **`transformation.py`**: Single-node transformation executor with prompt templating via ai_prompter
- **`prompt.py`**: Generic pattern chain for arbitrary prompt-based LLM calls
- **`tools.py`**: Minimal tool library (currently just `get_current_timestamp()`)

## Important Patterns

- **Async/sync bridging in graphs**: Both `chat.py` and `source_chat.py` use `asyncio.new_event_loop()` workaround because LangGraph nodes are sync but `provision_langchain_model()` is async
- **State machines via StateGraph**: Each graph compiles to stateful runnable; conditional edges fan out work (ask.py, source.py do parallel transforms)
- **Prompt templating**: `ai_prompter.Prompter` with Jinja2 templates referenced by path ("chat/system", "ask/entry", etc.)
- **Model provisioning via context**: Config dict passed to node via `RunnableConfig`; defaults fall back to state overrides
- **Checkpointing**: `chat.py` and `source_chat.py` use SqliteSaver for message history (LangGraph's built-in persistence)
- **Content extraction**: `source.py` uses content-core library with provider/model from DefaultModels; URLs and files both supported

## Quirks & Edge Cases

- **Async loop gymnastics**: ThreadPoolExecutor workaround needed because LangGraph invokes sync nodes but we call async functions; fragile if event loop state changes
- **`clean_thinking_content()` ubiquitous**: Strips `<think>...</think>` tags from model responses (handles extended thinking models)
- **source_chat.py builds context twice**: ContextBuilder runs during node execution to fetch source/insights; rebuilds list from context_data (inefficient but safe)
- **source.py embedding is async**: `source.vectorize()` returns job command ID; not awaited (fire-and-forget)
- **transformation.py nullable source**: Accepts `input_text` or `source.full_text` (falls back to second if first missing)
- **ask.py hard-coded vector_search**: No fallback to text search despite commented code suggesting it was planned
- **SqliteSaver location**: Checkpoints stored in path from `LANGGRAPH_CHECKPOINT_FILE` env var; connection shared across graphs

## Key Dependencies

- `langgraph`: StateGraph, Send, END, START, SqliteSaver checkpoint persistence
- `langchain_core`: Messages, OutputParser, RunnableConfig
- `ai_prompter`: Prompter for Jinja2 template rendering
- `content_core`: `extract_content()` for file/URL processing
- `open_notebook.ai.provision`: `provision_langchain_model()` (async factory with fallback logic)
- `open_notebook.domain.notebook`: Domain models (Source, Note, SourceInsight, vector_search)
- `loguru`: Logging

## Usage Example

```python
# Invoke a graph with config override
config = {"configurable": {"model_id": "model:custom_id"}}
result = await chat_graph.ainvoke(
    {"messages": [HumanMessage(content="...")], "notebook": notebook},
    config=config
)

# Source processing (content → save → transform)
result = await source_graph.ainvoke({
    "content_state": {...},  # ProcessSourceState from content-core
    "apply_transformations": [t1, t2],
    "source_id": "source:123",
    "embed": True
})
```
