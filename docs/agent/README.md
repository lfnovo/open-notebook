# Research Agent for Open Notebook

A built-in AI research agent that can autonomously search, analyze, and organize research within your notebooks.

## Overview

The Research Agent transforms Open Notebook from a manual research tool into an intelligent research assistant. Instead of manually searching, reading, and note-taking, you can delegate research tasks to the agent.

### Example Use Cases

- *"Research quantum computing and summarize the key findings"*
- *"Find all sources related to machine learning and create a summary note"*
- *"What do my sources say about climate change?"*
- *"Create a note comparing the different approaches mentioned in my sources"*

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │    Chat      │  │    Agent     │  │   Agent Steps View   │  │
│  │   (existing) │  │    Panel     │  │ (thinking/tools/resp)│  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                        │
│                                                                 │
│  POST /api/agent/stream   - SSE streaming execution             │
│  POST /api/agent/execute  - Synchronous execution               │
│  GET  /api/agent/tools    - List available tools                │
│  GET  /api/agent/models   - List supported models               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Graph (LangGraph)                      │
│                                                                 │
│  ┌─────────┐     ┌─────────────┐     ┌─────────────────────┐   │
│  │  START  │────▶│ Agent Node  │────▶│ Should Continue?    │   │
│  └─────────┘     │ (LLM+Tools) │     │                     │   │
│                  └─────────────┘     └──────────┬──────────┘   │
│                        ▲                        │              │
│                        │              ┌─────────┴─────────┐    │
│                        │              ▼                   ▼    │
│                  ┌─────────────┐  ┌───────┐          ┌─────┐   │
│                  │ Tool Node   │  │ Tools │          │ END │   │
│                  │ (Execute)   │◀─┤       │          └─────┘   │
│                  └─────────────┘  └───────┘                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Tools (8 tools)                      │
│                                                                 │
│  search_knowledge_base  │  get_source_content                   │
│  get_source_insights    │  create_note                          │
│  update_note            │  list_notebook_sources                │
│  list_notebook_notes    │  get_current_datetime                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Knowledge Base (SurrealDB)                  │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Tools

### search_knowledge_base
Search for relevant content in the knowledge base.

**Parameters:**
- `query` (str): Search query
- `search_type` (str): "vector" for semantic or "text" for keyword search
- `limit` (int): Maximum results (default: 5)
- `include_sources` (bool): Include sources in search
- `include_notes` (bool): Include notes in search

### get_source_content
Retrieve the full content of a source document.

**Parameters:**
- `source_id` (str): Source record ID

### get_source_insights
Get AI-generated insights (summary, key points) for a source.

**Parameters:**
- `source_id` (str): Source record ID

### create_note
Create a new note in the notebook.

**Parameters:**
- `notebook_id` (str): Target notebook ID
- `title` (str): Note title
- `content` (str): Note content (Markdown supported)

### update_note
Update an existing note.

**Parameters:**
- `note_id` (str): Note record ID
- `title` (str, optional): New title
- `content` (str, optional): New content

### list_notebook_sources
List all sources in a notebook.

**Parameters:**
- `notebook_id` (str): Notebook ID

### list_notebook_notes
List all notes in a notebook.

**Parameters:**
- `notebook_id` (str): Notebook ID

### get_current_datetime
Get current date and time for context.

**Parameters:** None

## API Reference

### POST /api/agent/stream

Stream agent execution with Server-Sent Events.

**Request Body:**
```json
{
  "message": "Research quantum computing",
  "notebook_id": "notebook:xxx",
  "thread_id": "unique-thread-id",
  "model_override": "deepseek-chat",
  "api_key": "sk-xxx"
}
```

**SSE Events:**
```
event: thinking
data: {"type": "thinking", "content": "Analyzing request..."}

event: tool_call
data: {"type": "tool_call", "tool": "search_knowledge_base", "input": {...}}

event: tool_result
data: {"type": "tool_result", "tool": "search_knowledge_base", "output": "..."}

event: response
data: {"type": "response", "content": "Based on my research..."}

event: done
data: {"type": "done"}
```

### POST /api/agent/execute

Synchronous agent execution.

**Request/Response:** Same structure as stream, but returns complete result.

### GET /api/agent/tools

List available agent tools.

**Response:**
```json
{
  "tools": [
    {
      "name": "search_knowledge_base",
      "description": "Search the knowledge base...",
      "parameters": {...}
    }
  ]
}
```

### GET /api/agent/models

List supported AI models.

**Response:**
```json
{
  "models": [
    {
      "id": "deepseek/deepseek-chat",
      "name": "deepseek-chat",
      "provider": "deepseek",
      "description": "DeepSeek - Cost effective, strong reasoning"
    }
  ],
  "providers": {...}
}
```

## Supported Models

### DeepSeek
- **Provider**: `deepseek`
- **Models**: `deepseek-chat`, `deepseek-reasoner`
- **API Key**: `DEEPSEEK_API_KEY`
- **Cost**: ~$0.001/1K tokens

### Qwen (Alibaba Cloud)
- **Provider**: `openai_compatible`
- **Models**: `qwen-turbo`, `qwen-plus`, `qwen-max`, `qwen-long`
- **API Key**: `OPENAI_COMPATIBLE_API_KEY_LLM`
- **Base URL**: `https://dashscope.aliyuncs.com/compatible-mode/v1`

## Frontend Components

### AgentPanel
Main component for agent interaction.

**Location:** `frontend/src/components/agent/AgentPanel.tsx`

**Features:**
- Message input and history
- Real-time step visualization
- Tool call expansion
- Model selection
- API key configuration

### useAgent Hook
React hook for agent state management.

**Location:** `frontend/src/lib/hooks/useAgent.ts`

**Provides:**
- `messages` - Conversation history
- `steps` - Current execution steps
- `isLoading` - Loading state
- `sendMessage()` - Send message to agent
- `selectedModel` - Current model selection

## Configuration

### Environment Variables

```bash
# DeepSeek
DEEPSEEK_API_KEY=sk-xxx

# Qwen (via DashScope)
OPENAI_COMPATIBLE_BASE_URL_LLM=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_COMPATIBLE_API_KEY_LLM=sk-xxx
```

### BYOK (Bring Your Own Key)

Users can provide their API key directly in the UI without server configuration. The key is:
- Stored only in browser session
- Sent with each request
- Never persisted on server

## Development

### Running Tests

```bash
# Backend tests
uv run pytest tests/test_agent.py

# Type checking
uv run python -m mypy open_notebook/graphs/agent.py
```

### Adding New Tools

1. Define tool in `open_notebook/graphs/agent_tools.py`:

```python
from langchain_core.tools import tool

@tool
async def my_new_tool(param: str) -> str:
    """Tool description for the LLM."""
    # Implementation
    return result
```

2. Add to `AGENT_TOOLS` list in the same file.

3. The tool will automatically be available to the agent.

## Future Improvements

- [ ] Conversation memory persistence
- [ ] Multi-agent collaboration
- [ ] Custom tool creation UI
- [ ] Agent templates for common tasks
- [ ] Usage analytics and cost tracking
