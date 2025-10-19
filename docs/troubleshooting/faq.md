# Frequently Asked Questions

This document addresses common questions about Open Notebook usage, configuration, and best practices.

## General Usage

### What is Open Notebook?

Open Notebook is an open-source, privacy-focused alternative to Google's Notebook LM. It allows you to:
- Create and manage research notebooks
- Chat with your documents using AI
- Generate podcasts from your content
- Search across all your sources with semantic search
- Transform and analyze your content

### How is Open Notebook different from Google Notebook LM?

**Privacy**: Your data stays local by default. Only your chosen AI providers receive queries.
**Flexibility**: Support for 15+ AI providers (OpenAI, Anthropic, Google, local models, etc.)
**Customization**: Open source, so you can modify and extend functionality
**Control**: You control your data, models, and processing

### Do I need technical skills to use Open Notebook?

**Basic usage**: No technical skills required. The Docker installation is designed for non-technical users.
**Advanced features**: Some technical knowledge helpful for:
- Custom model configurations
- API integrations
- Source code modifications

### Can I use Open Notebook offline?

**Partially**: The application runs locally, but requires internet for:
- AI model API calls (unless using local models like Ollama)
- Web content scraping
- Some file processing features

**Fully offline**: Possible with local models (Ollama) for basic functionality.

### What file types does Open Notebook support?

**Documents**:
- PDF (text extraction)
- Microsoft Word (DOC, DOCX)
- Plain text (TXT)
- Markdown (MD)

**Web Content**:
- URLs (automatic web scraping)
- YouTube videos (transcript extraction)
- Web articles and blog posts

**Media**:
- Images (PNG, JPG, GIF, WebP) with OCR
- Audio files (MP3, WAV, M4A) with transcription
- Video files (MP4, AVI, MOV) for transcript extraction

**Other**:
- Direct text input
- CSV data
- Code files (with syntax highlighting)

### How much does it cost to run Open Notebook?

**Software**: Free (open source)
**AI API costs**: Pay-per-use to providers:
- OpenAI: ~$0.50-5 per 1M tokens depending on model
- Anthropic: ~$3-75 per 1M tokens depending on model
- Google: Often free tier available
- Local models: Free after initial setup

**Typical monthly costs**: $5-50 for moderate usage, depending on chosen models.

## AI Models and Providers

### Which AI provider should I choose?

**For beginners**: OpenAI (reliable, well-documented, good balance of cost/quality)
**For advanced users**: Mix of providers based on specific needs
**For privacy**: Local models (Ollama) or European providers (Mistral)
**For cost optimization**: DeepSeek, Google (free tier), or OpenRouter

### Can I use multiple AI providers simultaneously?

**Yes**: Open Notebook supports multiple providers. You can configure different providers for different tasks:
- OpenAI for chat
- Google for embeddings
- ElevenLabs for text-to-speech
- Anthropic for complex reasoning

### What are the best model combinations?

**Budget-friendly**:
- Language: `gpt-5-mini` (OpenAI) or `deepseek-chat` (DeepSeek)
- Embedding: `text-embedding-3-small` (OpenAI)
- TTS: `gpt-4o-mini-tts` (OpenAI)

**High-quality**:
- Language: `claude-3-7-sonnet` (Anthropic) or `gpt-4o` (OpenAI)
- Embedding: `text-embedding-3-large` (OpenAI)
- TTS: `eleven_turbo_v2_5` (ElevenLabs)

**Privacy-focused**:
- Language: Local Ollama models
- Embedding: Local embedding models
- TTS: Local TTS solutions

### How do I set up local models with Ollama?

1. **Install Ollama**: Download from https://ollama.ai
2. **Start Ollama**: `ollama serve`
3. **Download models**: `ollama pull llama2`
4. **Configure Open Notebook**:
   ```env
   OLLAMA_API_BASE=http://localhost:11434
   ```
5. **Select models**: In Models, choose Ollama models

### Why are my AI requests failing?

**Common causes**:
- Invalid API keys
- Insufficient credits/billing
- Model not available for your account
- Rate limiting
- Network connectivity issues

**Solutions**:
1. Verify API keys in provider dashboard
2. Check billing and usage limits
3. Try different models
4. Wait and retry for rate limits
5. Check internet connection

### How do I optimize AI costs?

**Model selection**:
- Use smaller models for simple tasks
- Use larger models only for complex reasoning
- Leverage free tiers when available

**Usage optimization**:
- Process documents in batches
- Use shorter prompts
- Cache results when possible
- Use local models for frequent tasks

**Provider diversity**:
- Use OpenRouter for expensive models
- Use free tier providers for testing
- Mix providers based on strength

## Data Management

### Where is my data stored?

**Local storage**: By default, all data is stored locally:
- Database: SurrealDB files in `surreal_data/`
- Uploads: Files in `notebook_data/`
- No external data transmission (except to chosen AI providers)

**Cloud storage**: Not implemented, but can be configured with external storage solutions.

### How do I backup my data?

**Manual backup**:
```bash
# Create backup
tar -czf backup-$(date +%Y%m%d).tar.gz notebook_data/ surreal_data/

# Restore backup
tar -xzf backup-20240101.tar.gz
```

**Automated backup**: Set up cron jobs or use your preferred backup solution to backup the data directories.

### Can I sync data between devices?

**Currently**: No built-in sync functionality.
**Workarounds**:
- Use shared network storage for data directories
- Manual backup/restore between devices
- Database replication (advanced)

### How do I migrate data between installations?

1. **Stop services**: `make stop-all`
2. **Copy data directories**: 
   ```bash
   cp -r surreal_data/ new_installation/
   cp -r notebook_data/ new_installation/
   ```
3. **Start new installation**
4. **Verify data integrity**

### What happens to my data if I delete a notebook?

**Soft deletion**: Notebooks are marked as archived, not permanently deleted.
**Hard deletion**: Currently not implemented in UI, but possible via API.
**Recovery**: Archived notebooks can be restored from the database.

### How do I clean up old data?

**Manual cleanup**:
- Delete unused notebooks through UI
- Remove old files from `notebook_data/`
- Clear browser cache

**Database cleanup**: Advanced users can query the database directly to remove old records.

## Best Practices

### How should I organize my notebooks?

**By topic**: Create separate notebooks for different research areas
**By project**: One notebook per project or course
**By source type**: Separate notebooks for different content types
**By time period**: Monthly or quarterly notebooks

### What's the optimal notebook size?

**Recommended**: 20-100 sources per notebook
**Performance**: Larger notebooks may have slower search
**Organization**: Better to have focused notebooks than everything in one

### How do I get the best search results?

**Use descriptive queries**: Instead of "data", use "data analysis methods"
**Combine keywords**: Use multiple related terms
**Use natural language**: Ask questions as you would to a human
**Refine iteratively**: Start broad, then get more specific

### How can I improve chat responses?

**Provide context**: Reference specific sources or topics
**Be specific**: Ask detailed questions rather than general ones
**Use follow-up questions**: Build on previous responses
**Include examples**: Show what kind of response you want

### What's the best way to process large documents?

**Break into sections**: Split large documents into smaller parts
**Use transformations**: Apply summarization before adding to notebook
**Batch processing**: Process multiple documents at once
**Use background jobs**: For heavy processing tasks

### How do I handle multiple languages?

**Model selection**: Choose models that support your languages
**Language-specific providers**: Some providers are better for certain languages
**Separate notebooks**: Consider separate notebooks for different languages
**Encoding**: Ensure proper text encoding for non-English content

### What are the security best practices?

**API keys**: Never share API keys publicly
**Password protection**: Use strong passwords for public deployments
**Network security**: Use HTTPS for production deployments
**Regular updates**: Keep Docker images updated
**Backup encryption**: Encrypt backups if they contain sensitive data

### How do I optimize performance?

**Hardware**:
- Use SSD storage for database
- Allocate sufficient RAM (4GB+ recommended)
- Use fast internet connection

**Configuration**:
- Choose appropriate models for your needs
- Optimize embedding dimensions
- Use efficient file formats

**Usage patterns**:
- Process documents in batches
- Use background jobs for heavy tasks
- Clear cache periodically

## Technical Questions

### Can I use Open Notebook programmatically?

**Yes**: Open Notebook provides a comprehensive REST API:
- Full API documentation at `/docs` endpoint
- Support for all UI functionality
- Authentication via API keys
- Webhook support for notifications

### How do I extend Open Notebook?

**Plugin system**: Add custom transformations and processors
**API integration**: Build custom applications using the API
**Source code**: Modify the open-source codebase
**Custom models**: Add support for new AI providers

### Can I run Open Notebook in production?

**Yes**: Designed for production use with:
- Docker deployment
- Horizontal scaling capability
- Security features
- Monitoring and logging

**Considerations**:
- Use production-grade database settings
- Implement proper backup strategy
- Configure monitoring and alerting
- Use HTTPS and security best practices

### How do I contribute to Open Notebook?

**Ways to contribute**:
- Report bugs and issues
- Suggest new features
- Contribute code improvements
- Improve documentation
- Help other users in the community

**Getting started**:
- Join Discord community
- Check GitHub issues
- Read contribution guidelines
- Start with small improvements

### What's the development roadmap?

**Current focus**:
- Stability and performance improvements
- Additional AI provider support
- Enhanced podcast generation
- Better mobile experience

**Future plans**:
- Multi-user support
- Advanced analytics
- Integration with external tools
- Cloud deployment options

## Troubleshooting

### Why do I get timeout errors even though transformations complete successfully?

**Cause**: The default client timeout (5 minutes) may be too short for slow AI providers or hardware.

**Quick fix**:
```bash
# Add to your .env file
API_CLIENT_TIMEOUT=600  # 10 minutes for slow hardware
```

**When this happens**:
- Using local Ollama models on CPU
- Using remote LM Studio over slow network
- First transformation after starting (model loading)
- Very large documents
- Slower hardware configurations

**Detailed solutions**: See [Common Issues - API Timeout Errors](./common-issues.md#api-timeout-errors-during-transformations)

**Note**: If transformations complete after you refresh the page, you only need to increase `API_CLIENT_TIMEOUT`, not `ESPERANTO_LLM_TIMEOUT`.

### My question isn't answered here. What should I do?

1. **Check the troubleshooting guide**: [Common Issues](./common-issues.md)
2. **Search existing issues**: GitHub repository issues
3. **Ask the community**: Discord server
4. **Create a GitHub issue**: For bugs or feature requests
5. **Check the documentation**: Other documentation sections

### How do I report a bug?

**Include**:
- Steps to reproduce
- Expected vs actual behavior
- Error messages and logs
- System information
- Configuration details (without API keys)

**Submit to**: GitHub Issues with bug report template

### How do I request a new feature?

**Process**:
1. Check if feature already exists or is planned
2. Discuss in Discord to gauge interest
3. Create detailed GitHub issue
4. Consider contributing implementation

### Where can I get help with installation?

**Resources**:
- [Installation Guide](../getting-started/installation.md)
- [Docker Deployment Guide](../deployment/docker.md)
- [ChatGPT Installation Assistant](https://chatgpt.com/g/g-68776e2765b48191bd1bae3f30212631-open-notebook-installation-assistant)
- Discord community support

### How do I stay updated with new releases?

**Methods**:
- Watch GitHub repository
- Join Discord for announcements
- Follow release notes
- Enable automatic Docker updates

---

*This FAQ is updated regularly based on community questions and feedback. If you have a question that's not covered here, please ask in our Discord community or create a GitHub issue.*