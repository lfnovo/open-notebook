# Feature Proposal: Built-in Research Agent

## GitHub Issue Draft

### Title
`[Feature Proposal] Built-in Research Agent with ReAct Architecture`

### Body

```markdown
## Summary

I'd like to propose adding a built-in AI research agent to Open Notebook. This feature would transform Open Notebook from a "tool you use" into an "assistant that works for you."

## Motivation

Currently, users manually:
1. Search their knowledge base
2. Read through sources
3. Extract insights
4. Create notes

With an agent, users could simply say: *"Research quantum computing and summarize the key findings"* - and the agent handles the rest.

## Proposed Features

### Core Agent Capabilities
- **Autonomous Research**: Agent can search, read, and analyze sources independently
- **Note Creation**: Automatically creates well-organized notes from findings
- **ReAct Architecture**: Transparent reasoning with visible thought process
- **Streaming UI**: Real-time display of agent's thinking and actions

### Technical Implementation
- Built on LangGraph for reliable agent orchestration
- 8 specialized tools for knowledge base interaction
- SSE streaming for real-time UI updates
- Fully async for performance

### Model Support
- Works with existing model configuration
- Added support for cost-effective models:
  - DeepSeek (great reasoning, low cost)
  - Qwen/DashScope (strong Chinese support)

## UI Preview

The agent appears as a new tab alongside the existing Chat:

```
┌─────────────────────────────────┐
│  Chat  │  Agent  │              │
├─────────────────────────────────┤
│                                 │
│  🤔 Thinking...                 │
│                                 │
│  🔧 Calling: search_knowledge   │
│     Query: "quantum computing"  │
│                                 │
│  📋 Found 5 relevant sources    │
│                                 │
│  💬 Based on my research...     │
│                                 │
└─────────────────────────────────┘
```

## Implementation Status

I've already developed a working prototype with:

| Component | Status |
|-----------|--------|
| Agent Tools (8 tools) | ✅ Complete |
| Agent Graph (LangGraph) | ✅ Complete |
| API Endpoints | ✅ Complete |
| Frontend Panel | ✅ Complete |
| Streaming Support | ✅ Complete |
| Documentation | ✅ Complete |

## Questions for Maintainers

1. Is this feature aligned with the project's vision?
2. Any concerns about the architecture or implementation?
3. Preferred approach for the PR (single PR vs. incremental)?

## Demo

I can provide:
- [ ] Video demo
- [ ] Screenshots
- [ ] Test deployment

Happy to discuss and iterate based on feedback!

---

**Related**: This builds on the existing chat functionality and reuses the model provisioning infrastructure.
```

---

## Pull Request Draft

### Title
`feat: Add built-in research agent with ReAct architecture`

### Description

```markdown
## Description

This PR adds a built-in AI research agent that can autonomously search, analyze, and organize research within notebooks.

Closes #XXX (link to issue)

## Changes

### Backend

**New Files:**
- `open_notebook/graphs/agent.py` - ReAct agent graph implementation
- `open_notebook/graphs/agent_tools.py` - 8 agent tools for KB interaction
- `api/routers/agent.py` - Agent API endpoints

**Modified Files:**
- `api/main.py` - Register agent router

### Frontend

**New Files:**
- `frontend/src/lib/types/agent.ts` - TypeScript types
- `frontend/src/lib/api/agent.ts` - API client with SSE support
- `frontend/src/lib/hooks/useAgent.ts` - Agent state management
- `frontend/src/components/agent/AgentPanel.tsx` - Agent UI component

**Modified Files:**
- `frontend/src/app/(dashboard)/notebooks/components/ChatColumn.tsx` - Add Chat/Agent tabs

### Documentation
- `docs/AGENT_DESIGN.md` - Architecture documentation

## Agent Tools

| Tool | Description |
|------|-------------|
| `search_knowledge_base` | Vector/text search across sources and notes |
| `get_source_content` | Retrieve full source content |
| `get_source_insights` | Get AI-generated insights for a source |
| `create_note` | Create a new note |
| `update_note` | Update existing note |
| `list_notebook_sources` | List all sources in notebook |
| `list_notebook_notes` | List all notes in notebook |
| `get_current_datetime` | Get current time for context |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agent/stream` | Stream agent execution (SSE) |
| POST | `/api/agent/execute` | Synchronous execution |
| GET | `/api/agent/tools` | List available tools |
| GET | `/api/agent/models` | List supported models |

## Screenshots

[TODO: Add screenshots]

## Testing

- [ ] Agent can search knowledge base
- [ ] Agent can create notes
- [ ] Streaming updates work correctly
- [ ] Error handling works
- [ ] Works with DeepSeek/Qwen models

## Checklist

- [x] Code follows project style guidelines
- [x] Documentation updated
- [x] No breaking changes to existing functionality
- [ ] Tests added (if applicable)
```

---

## Next Steps

1. **Open Issue first** - Get maintainer feedback before PR
2. **Wait for response** - Usually 1-3 days
3. **Submit PR** - After positive feedback
4. **Iterate** - Address review comments
