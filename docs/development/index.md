# Development Documentation

Welcome to the Open Notebook development documentation! This section provides comprehensive technical information for developers and contributors.

## 📋 Quick Navigation

### Getting Started
- **[Architecture Overview](architecture.md)** - Understanding the system design and components
- **[API Reference](api-reference.md)** - Complete REST API documentation
- **[Contributing Guide](contributing.md)** - Development workflow and standards

### Development Setup
Before diving into the documentation below, make sure you have Open Notebook set up locally:

```bash
# Clone the repository
git clone https://github.com/lfnovo/open-notebook
cd open-notebook

# Install dependencies with uv
uv sync

# Start the development environment
make start-all
```

For detailed setup instructions, see the [Installation Guide](../getting-started/installation.md).

## 🏗️ System Architecture

Open Notebook is built with a modern Python stack using:

- **Backend**: FastAPI with async/await patterns
- **Database**: SurrealDB for flexible document storage
- **Frontend**: Next.js for rapid UI development
- **AI Integration**: Multi-provider support via Esperanto library
- **Processing**: LangChain for AI workflows and content processing

### Key Components

| Component | Description | Location |
|-----------|-------------|----------|
| **API Layer** | FastAPI REST endpoints | `api/` |
| **Domain Models** | Core business logic | `open_notebook/domain/` |
| **Database** | SurrealDB repository pattern | `open_notebook/database/` |
| **AI Graphs** | LangChain processing workflows | `open_notebook/graphs/` |
| **Next.js Frontend** | Modern React-based web interface | `frontend/` |
| **Commands** | Background job processing | `commands/` |

## 🔧 Development Workflow

### Code Standards
- **Python**: PEP 8 compliance with type hints
- **Async/Await**: Consistent async patterns throughout
- **Error Handling**: Comprehensive exception handling
- **Logging**: Structured logging with Loguru
- **Testing**: Unit and integration tests with pytest

### Database Patterns
Open Notebook uses SurrealDB with a custom repository pattern:

```python
# Create records
await repo_create("table", data)

# Query with SurrealQL
await repo_query("SELECT * FROM table WHERE field = $value", {"value": "example"})

# Update records
await repo_update("table", record_id, data)
```

### AI Integration
Multi-provider AI support via the Esperanto library:

```python
from esperanto import AIFactory

# Create language model
model = AIFactory.create_language("openai", "gpt-4")

# Generate completion
response = model.chat_complete(messages)
```

## 🚀 Key Features to Understand

### 1. Multi-Notebook Organization
- Notebooks contain sources, notes, and chat sessions
- Each notebook maintains isolated context
- Sources can be shared across notebooks (roadmap)

### 2. Content Processing Pipeline
- **Ingestion**: Documents, URLs, text → structured content
- **Embedding**: Vector representations for semantic search
- **Transformations**: AI-powered content analysis
- **Indexing**: Both full-text and vector search

### 3. AI Workflows
- **Chat**: Context-aware conversations
- **Ask**: Multi-step question answering
- **Transformations**: Content summarization and analysis
- **Podcast Generation**: Advanced multi-speaker content

### 4. Background Processing
- Commands system for long-running tasks
- Async job queue with SurrealDB
- Status tracking and error handling

## 📝 Contributing

We welcome contributions! Here's how to get started:

1. **Read the [Contributing Guide](contributing.md)** for detailed workflow
2. **Check the [Architecture Overview](architecture.md)** to understand the system
3. **Browse the [API Reference](api-reference.md)** for endpoint details
4. **Join our [Discord](https://discord.gg/37XJPXfz2w)** for community support

### Current Development Priorities

- **Frontend Enhancement**: Improving the Next.js/React UI with real-time updates
- **Performance**: Async processing and caching improvements
- **Testing**: Expanded test coverage
- **Documentation**: API documentation and examples

## 📖 Additional Resources

### External Documentation
- [SurrealDB Documentation](https://surrealdb.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [Esperanto Library](https://github.com/lfnovo/esperanto)

### Community
- [Discord Server](https://discord.gg/37XJPXfz2w) - Development discussions
- [GitHub Issues](https://github.com/lfnovo/open-notebook/issues) - Bug reports and features
- [GitHub Discussions](https://github.com/lfnovo/open-notebook/discussions) - Ideas and questions

---

Ready to contribute? Start with the [Contributing Guide](contributing.md) and join our vibrant developer community!