# Frequently Asked Questions

Common questions about Open Notebook usage, configuration, and best practices.

---

## General Usage

### What is Open Notebook?

Open Notebook is an open-source, privacy-focused alternative to Google's Notebook LM. It allows you to:
- Create and manage research notebooks
- Chat with your documents using AI
- Generate podcasts from your content
- Search across all your sources with semantic search
- Transform and analyze your content

### How is it different from Google Notebook LM?

**Privacy**: Your data stays local by default. Only your chosen AI providers receive queries.
**Flexibility**: Support for 15+ AI providers (OpenAI, Anthropic, Google, local models, etc.)
**Customization**: Open source, so you can modify and extend functionality
**Control**: You control your data, models, and processing

### Can I use Open Notebook offline?

**Partially**: The application runs locally, but requires internet for:
- AI model API calls (unless using local models like Ollama)
- Web content scraping

**Fully offline**: Possible with local models (Ollama) for basic functionality.

### What file types are supported?

**Documents**: PDF, DOCX, TXT, Markdown
**Web Content**: URLs, YouTube videos
**Media**: MP3, WAV, M4A (audio), MP4, AVI, MOV (video)
**Other**: Direct text input, CSV, code files

### How much does it cost?

**Software**: Free (open source)
**AI API costs**: Pay-per-use to providers:
- OpenAI: ~$0.50-5 per 1M tokens
- Anthropic: ~$3-75 per 1M tokens
- Google: Often free tier available
- Local models: Free after initial setup

**Typical monthly costs**: $5-50 for moderate usage.

---

## AI Models and Providers

### Which AI provider should I choose?

**For beginners**: OpenAI (reliable, well-documented)
**For privacy**: Local models (Ollama) or European providers (Mistral)
**For cost optimization**: Groq, Google (free tier), or OpenRouter
**For long context**: Anthropic (200K tokens) or Google Gemini (1M tokens)

### Can I use multiple providers?

**Yes**: Configure different providers for different tasks:
- OpenAI for chat
- Google for embeddings
- ElevenLabs for text-to-speech
- Anthropic for complex reasoning

### What are the best model combinations?

**Budget-friendly**:
- Language: `gpt-4o-mini` (OpenAI) or `deepseek-chat`
- Embedding: `text-embedding-3-small` (OpenAI)

**High-quality**:
- Language: `claude-3-5-sonnet` (Anthropic) or `gpt-4o` (OpenAI)
- Embedding: `text-embedding-3-large` (OpenAI)

**Privacy-focused**:
- Language: Local Ollama models (mistral, llama3)
- Embedding: Local embedding models

### How do I optimize AI costs?

**Model selection**:
- Use smaller models for simple tasks (gpt-4o-mini, claude-3-5-haiku)
- Use larger models only for complex reasoning
- Leverage free tiers when available

**Usage optimization**:
- Use "Summary Only" context for background sources
- Ask more specific questions
- Use local models (Ollama) for frequent tasks

---

## Data Management

### Where is my data stored?

**Local storage**: By default, all data is stored locally:
- Database: SurrealDB files in `surreal_data/`
- Uploads: Files in `data/uploads/`
- Podcasts: Generated audio in `data/podcasts/`
- No external data transmission (except to chosen AI providers)

### How do I backup my data?

```bash
# Create backup
tar -czf backup-$(date +%Y%m%d).tar.gz data/ surreal_data/

# Restore backup
tar -xzf backup-20240101.tar.gz
```

### Can I sync data between devices?

**Currently**: No built-in sync functionality.
**Workarounds**:
- Use shared network storage for data directories
- Manual backup/restore between devices

### What happens if I delete a notebook?

**Soft deletion**: Notebooks are marked as archived, not permanently deleted.
**Recovery**: Archived notebooks can be restored from the database.

---

## Best Practices

### How should I organize my notebooks?

- **By topic**: Separate notebooks for different research areas
- **By project**: One notebook per project or course
- **By time period**: Monthly or quarterly notebooks

**Recommended size**: 20-100 sources per notebook for best performance.

### How do I get the best search results?

- Use descriptive queries ("data analysis methods" not just "data")
- Combine multiple related terms
- Use natural language (ask questions as you would to a human)
- Try both text search (keywords) and vector search (concepts)

### How can I improve chat responses?

- Provide context: Reference specific sources or topics
- Be specific: Ask detailed questions rather than general ones
- Request citations: "Answer with page citations"
- Use follow-up questions: Build on previous responses

### What are the security best practices?

- Never share API keys publicly
- Use `OPEN_NOTEBOOK_PASSWORD` for public deployments
- Use HTTPS for production (via reverse proxy)
- Keep Docker images updated
- Encrypt backups if they contain sensitive data

---

## Technical Questions

### Can I use Open Notebook programmatically?

**Yes**: Open Notebook provides a REST API:
- Full API documentation at `http://localhost:5055/docs`
- Support for all UI functionality
- Authentication via password header

### Can I run Open Notebook in production?

**Yes**: Designed for production use with:
- Docker deployment
- Security features (password protection)
- Monitoring and logging
- Reverse proxy support (nginx, Caddy, Traefik)

### What are the system requirements?

**Minimum**:
- 4GB RAM
- 2 CPU cores
- 10GB disk space

**Recommended**:
- 8GB+ RAM
- 4+ CPU cores
- SSD storage
- For local models: 16GB+ RAM, GPU recommended

---

## Timeout and Performance

### Why do I get timeout errors?

**Common causes**:
- Large context (too many sources)
- Slow AI provider
- Local models on CPU (slow)
- First request (model loading)

**Solutions**:
```bash
# In .env:
API_CLIENT_TIMEOUT=600  # 10 minutes for slow setups
ESPERANTO_LLM_TIMEOUT=180  # 3 minutes for model inference
```

### Recommended timeouts by setup:

| Setup | API_CLIENT_TIMEOUT |
|-------|-------------------|
| Cloud APIs (OpenAI, Anthropic) | 300 (default) |
| Local Ollama with GPU | 600 |
| Local Ollama with CPU | 1200 |
| Remote LM Studio | 900 |

---

## Getting Help

### My question isn't answered here

1. Check the troubleshooting guides in this section
2. Search existing GitHub issues
3. Ask in the Discord community
4. Create a GitHub issue with detailed information

### How do I report a bug?

Include:
- Steps to reproduce
- Expected vs actual behavior
- Error messages and logs
- System information
- Configuration details (without API keys)

Submit to: [GitHub Issues](https://github.com/lfnovo/open-notebook/issues)

### Where can I get help?

- **Discord**: https://discord.gg/37XJPXfz2w (fastest)
- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: This docs site

---

## Related

- [Quick Fixes](quick-fixes.md) - Common issues with 1-minute solutions
- [AI & Chat Issues](ai-chat-issues.md) - Model and chat problems
- [Connection Issues](connection-issues.md) - Network and API problems
