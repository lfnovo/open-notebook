# Open Notebook Installation Guide

This comprehensive guide will help you install and configure Open Notebook, an open-source, privacy-focused alternative to Google's Notebook LM. Whether you're a beginner or advanced user, this guide covers all installation methods and configuration options.

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Requirements](#system-requirements)
3. [Installation Methods](#installation-methods)
4. [Service Architecture](#service-architecture)
5. [Environment Configuration](#environment-configuration)
6. [Manual Installation](#manual-installation)
7. [Docker Installation](#docker-installation)
8. [AI Model Configuration](#ai-model-configuration)
9. [Verification and Testing](#verification-and-testing)
10. [Security Configuration](#security-configuration)
11. [Troubleshooting](#troubleshooting)

---

## Quick Start

For users who want to get started immediately:

### Docker (Recommended for Beginners)
```bash
# Create project directory
mkdir open-notebook && cd open-notebook

# Download configuration files
curl -O https://raw.githubusercontent.com/lfnovo/open-notebook/main/docker-compose.yml
curl -O https://raw.githubusercontent.com/lfnovo/open-notebook/main/.env.example

# Rename and configure environment
mv .env.example docker.env
# Edit docker.env with your API keys

# Start Open Notebook
docker compose up -d
```

### From Source (Developers)
```bash
# Clone and setup
git clone https://github.com/lfnovo/open-notebook
cd open-notebook
cp .env.example .env
# Edit .env with your API keys

# Install dependencies and start
uv sync
make start-all
```

Access Open Notebook at `http://localhost:8502`

---

## System Requirements

### Hardware Requirements
- **CPU**: 2+ cores recommended (4+ cores for better performance)
- **RAM**: Minimum 4GB (8GB+ recommended)
- **Storage**: 10GB+ available space
- **Network**: Stable internet connection for AI model access

### Operating System Support
- **macOS**: 10.15 (Catalina) or later
- **Linux**: Ubuntu 18.04+, Debian 9+, CentOS 7+, Fedora 30+
- **Windows**: Windows 10 or later (WSL2 recommended)

### Software Prerequisites
- **Python**: 3.9 or later (for source installation)
- **Docker**: Latest version (for Docker installation)
- **uv**: Python package manager (for source installation)

---

## Installation Methods

Open Notebook supports multiple installation methods. Choose the one that best fits your needs:

| Method | Best For | Difficulty | Pros | Cons |
|--------|----------|------------|------|------|
| **Docker Single-Container** | Beginners, simple deployments | Easy | One-click setup, isolated environment | Less control, harder to debug |
| **Docker Multi-Container** | Production deployments | Medium | Scalable, professional setup | More complex configuration |
| **Source Installation** | Developers, customization | Advanced | Full control, easy debugging | Requires Python knowledge |

---

## Service Architecture

Open Notebook consists of four main services that work together:

### 1. **SurrealDB Database** (Port 8000)
- **Purpose**: Stores notebooks, sources, notes, and metadata
- **Technology**: SurrealDB - a modern, multi-model database
- **Configuration**: Runs in Docker container with persistent storage

### 2. **FastAPI Backend** (Port 5055)
- **Purpose**: REST API for all application functionality
- **Features**: Interactive API documentation, authentication, data validation
- **Endpoints**: `/api/notebooks`, `/api/sources`, `/api/notes`, `/api/chat`

### 3. **Background Worker**
- **Purpose**: Processes long-running tasks asynchronously
- **Tasks**: Podcast generation, content transformations, embeddings
- **Technology**: Surreal Commands worker system

### 4. **React frontend** (Port 8502)
- **Purpose**: Web-based user interface
- **Features**: Notebooks, chat, sources, notes, search
- **Technology**: Next.js framework

### Service Communication Flow
```
User Browser → React frontend → FastAPI Backend → SurrealDB Database
                    ↓
            Background Worker ← Job Queue
```

---

## Environment Configuration

Open Notebook uses environment variables for configuration. Create a `.env` file (or `docker.env` for Docker) based on the template below:

### Core Configuration
```env
# Security (Optional - for public deployments)
OPEN_NOTEBOOK_PASSWORD=your_secure_password_here

# Database Configuration
SURREAL_URL="ws://localhost:8000/rpc"
SURREAL_USER="root"
SURREAL_PASSWORD="root"
SURREAL_NAMESPACE="open_notebook"
SURREAL_DATABASE="production"
```

### AI Provider Configuration

#### OpenAI (Recommended for beginners)
```env
# Provides: Language models, embeddings, TTS, STT
OPENAI_API_KEY=sk-your-openai-key-here
```

#### Anthropic (Claude models)
```env
# Provides: High-quality language models
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
```

#### Google (Gemini)
```env
# Provides: Large context models, embeddings, TTS
GEMINI_API_KEY=your-gemini-key-here
```

#### Vertex AI (Google Cloud)
```env
# Provides: Enterprise-grade AI models
VERTEX_PROJECT=your-google-cloud-project-name
GOOGLE_APPLICATION_CREDENTIALS=./google-credentials.json
VERTEX_LOCATION=us-east5
```

#### Additional Providers
```env
# DeepSeek - Cost-effective models
DEEPSEEK_API_KEY=your-deepseek-key-here

# Mistral - European AI provider
MISTRAL_API_KEY=your-mistral-key-here

# Groq - Fast inference
GROQ_API_KEY=your-groq-key-here

# xAI (Grok) - Cutting-edge models
XAI_API_KEY=your-xai-key-here

# ElevenLabs - High-quality voice synthesis
ELEVENLABS_API_KEY=your-elevenlabs-key-here

# Ollama - Local AI models
OLLAMA_API_BASE="http://localhost:11434"

# OpenRouter - Access to multiple models
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
OPENROUTER_API_KEY=your-openrouter-key-here

# Azure OpenAI
# Generic configuration (applies to all modalities)
AZURE_OPENAI_API_KEY=your-azure-key-here
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Mode-specific configuration (for different deployments per modality)
# AZURE_OPENAI_API_KEY_LLM=your-llm-key
# AZURE_OPENAI_ENDPOINT_LLM=https://llm-endpoint.openai.azure.com/
# AZURE_OPENAI_API_VERSION_LLM=2024-12-01-preview
# AZURE_OPENAI_API_KEY_EMBEDDING=your-embedding-key
# AZURE_OPENAI_ENDPOINT_EMBEDDING=https://embedding-endpoint.openai.azure.com/
# AZURE_OPENAI_API_VERSION_EMBEDDING=2024-12-01-preview

# OpenAI Compatible (LM Studio, etc.)
OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
# Optional - only if your endpoint requires authentication
OPENAI_COMPATIBLE_API_KEY=your-key-here
```

### Optional Services
```env
# Firecrawl - Enhanced web scraping
FIRECRAWL_API_KEY=your-firecrawl-key-here

# Jina - Advanced embeddings
JINA_API_KEY=your-jina-key-here

# Voyage AI - Specialized embeddings
VOYAGE_API_KEY=your-voyage-key-here

# LangSmith - Debugging and monitoring
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY=your-langsmith-key-here
LANGCHAIN_PROJECT="Open Notebook"
```

---

## Manual Installation

### Prerequisites Installation

#### macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install uv (Python package manager)
brew install uv

# Install Docker Desktop
brew install --cask docker
```

#### Ubuntu/Debian
```bash
# Update package list
sudo apt update


# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Docker
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

#### CentOS/RHEL/Fedora
```bash
# Install system dependencies
sudo dnf install -y file-devel python3-devel gcc

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Docker
sudo dnf install -y docker docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### Source Installation Steps

1. **Clone the Repository**
```bash
git clone https://github.com/lfnovo/open-notebook.git
cd open-notebook
```

2. **Configure Environment**
```bash
# Copy environment template
cp .env.example .env

# Edit environment file with your API keys
nano .env  # or use your preferred editor
```

3. **Install Python Dependencies**
```bash
# Install all required packages
uv sync

# Install additional system-specific packages
uv pip install python-magic
```

4. **Initialize Database**
```bash
# Start SurrealDB
make database
# Wait for database to be ready (about 10 seconds)
```

5. **Start All Services**
```bash
# Start all services at once
make start-all
```

This will start:
- SurrealDB database on port 8000
- FastAPI backend on port 5055
- Background worker for processing
- React frontend on port 8502

### Alternative: Start Services Individually

For development or debugging, you can start each service separately:

```bash
# Terminal 1: Database
make database

# Terminal 2: API Backend
make api

# Terminal 3: Background Worker
make worker

# Terminal 4: React frontend
make run
```

---

## Docker Installation

### Single-Container Deployment (Recommended for Beginners)

Perfect for personal use or platforms like PikaPods:

1. **Create Project Directory**
```bash
mkdir open-notebook
cd open-notebook
```

2. **Create Docker Compose File**
```bash
# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest-single
    ports:
      - "8502:8502"
      - "5055:5055"
    env_file:
      - ./docker.env
    pull_policy: always
    volumes:
      - ./notebook_data:/app/data
      - ./surreal_single_data:/mydata
    restart: always
EOF
```

3. **Create Environment File**
```bash
# Create docker.env with your API keys
cat > docker.env << 'EOF'
# REQUIRED: At least one AI provider
OPENAI_API_KEY=your-openai-key-here

# Database settings (don't change)
SURREAL_ADDRESS=localhost
SURREAL_PORT=8000
SURREAL_USER=root
SURREAL_PASS=root
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=production

# Optional: Password protection
# OPEN_NOTEBOOK_PASSWORD=your_secure_password
EOF
```

4. **Start Open Notebook**
```bash
docker compose up -d
```

### Multi-Container Deployment (Production)

For scalable production deployments:

1. **Download Configuration**
```bash
# Download the main docker-compose.yml
curl -O https://raw.githubusercontent.com/lfnovo/open-notebook/main/docker-compose.yml

# Copy environment template
curl -o docker.env https://raw.githubusercontent.com/lfnovo/open-notebook/main/.env.example
```

2. **Configure Environment**
```bash
# Edit docker.env with your API keys
nano docker.env
```

3. **Start Services**
```bash
# Start with multi-container profile
docker compose --profile multi up -d
```

### Docker Service Management

```bash
# Check service status
docker compose ps

# View logs
docker compose logs -f

# Stop services
docker compose down

# Update to latest version
docker compose pull
docker compose up -d

# Restart specific service
docker compose restart open_notebook
```

---

## AI Model Configuration

After installation, configure your AI models for optimal performance:

### 1. Access Model Settings
- Navigate to **Settings** → **Models** in the web interface
- Or visit `http://localhost:8502` and click the settings icon

### 2. Configure Model Categories

#### Language Models (Chat & Generation)
**Budget-Friendly Options:**
- `gpt-5-mini` (OpenAI) - Great value for most tasks
- `deepseek-chat` (DeepSeek) - Excellent quality-to-price ratio
- `gemini-2.0-flash` (Google) - Large context window

**Premium Options:**
- `gpt-4o` (OpenAI) - Excellent tool calling
- `claude-3.5-sonnet` (Anthropic) - High-quality reasoning
- `grok-3` (xAI) - Cutting-edge intelligence

#### Embedding Models (Search & Similarity)
**Recommended:**
- `text-embedding-3-small` (OpenAI) - $0.02 per 1M tokens
- `text-embedding-004` (Google) - Generous free tier
- `mistral-embed` (Mistral) - European alternative

#### Text-to-Speech (Podcast Generation)
**High Quality:**
- `eleven_turbo_v2_5` (ElevenLabs) - Best voice quality
- `gpt-4o-mini-tts` (OpenAI) - Good quality, reliable

**Budget Options:**
- `gemini-2.5-flash-preview-tts` (Google) - $10 per 1M tokens

#### Speech-to-Text (Audio Transcription)
**Recommended:**
- `whisper-1` (OpenAI) - Industry standard
- `scribe_v1` (ElevenLabs) - High-quality transcription

### 3. Provider-Specific Setup

#### OpenAI Setup
1. Visit https://platform.openai.com/
2. Create account and navigate to **API Keys**
3. Click **"Create new secret key"**
4. Add at least $5 in billing credits
5. Copy key to your `.env` file

#### Anthropic Setup
1. Visit https://console.anthropic.com/
2. Create account and navigate to **API Keys**
3. Generate new key
4. Add to environment variables

#### Google (Gemini) Setup
1. Visit https://makersuite.google.com/app/apikey
2. Create new API key
3. Add to environment variables

### 4. Model Recommendations by Use Case

#### Personal Research
```env
# Language: gpt-5-mini (OpenAI)
# Embedding: text-embedding-3-small (OpenAI)
# TTS: gpt-4o-mini-tts (OpenAI)
# STT: whisper-1 (OpenAI)
```

#### Professional Use
```env
# Language: claude-3.5-sonnet (Anthropic)
# Embedding: text-embedding-004 (Google)
# TTS: eleven_turbo_v2_5 (ElevenLabs)
# STT: whisper-1 (OpenAI)
```

#### Budget-Conscious
```env
# Language: deepseek-chat (DeepSeek)
# Embedding: text-embedding-004 (Google)
# TTS: gemini-2.5-flash-preview-tts (Google)
# STT: whisper-1 (OpenAI)
```

---

## Verification and Testing

### 1. Service Health Checks

#### Check All Services
```bash
# For source installation
make status

# For Docker
docker compose ps
```

#### Individual Service Tests
```bash
# Test database connection
curl http://localhost:8000/health

# Test API backend
curl http://localhost:5055/health

# Test React frontend
curl http://localhost:8502/healthz
```

### 2. Create Test Notebook

1. **Access Web Interface**
   - Open `http://localhost:8502`
   - You should see the Open Notebook home page

2. **Create First Notebook**
   - Click "Create New Notebook"
   - Name: "Test Notebook"
   - Description: "Testing installation"
   - Click "Create"

3. **Add Test Source**
   - Click "Add Source"
   - Select "Text" tab
   - Paste: "This is a test document for Open Notebook installation."
   - Click "Add Source"

4. **Test Chat Function**
   - Go to Chat tab
   - Ask: "What is this document about?"
   - You should receive a response about the test document

### 3. Feature Testing

#### Test Search Functionality
1. Add multiple sources to your notebook
2. Use the search bar to find specific content
3. Verify both full-text and semantic search work

#### Test Transformations
1. Select a source
2. Click "Transform" → "Summarize"
3. Verify transformation completes successfully

#### Test Podcast Generation
1. Add substantial content to your notebook
2. Navigate to "Podcast" tab
3. Click "Generate Podcast"
4. Wait for background processing to complete

---

## Security Configuration

### Password Protection

For public deployments, enable password protection:

```env
# Add to your .env or docker.env file
OPEN_NOTEBOOK_PASSWORD=your_secure_password_here
```

**Features:**
- **React frontend**: Password prompt on first access
- **REST API**: Requires `Authorization: Bearer your_password` header
- **Local Usage**: Optional (can be left empty)

### API Security

When using the REST API programmatically:

```bash
# Example API call with password
curl -H "Authorization: Bearer your_password" \
     http://localhost:5055/api/notebooks
```

### Network Security

For production deployments:

1. **Use HTTPS**: Configure reverse proxy (nginx, Cloudflare)
2. **Firewall Rules**: Restrict access to necessary ports only
3. **VPN Access**: Consider VPN for private networks
4. **Regular Updates**: Keep Docker images updated

```bash
# Update Docker images
docker compose pull
docker compose up -d
```

---

## Troubleshooting

### Common Installation Issues

#### Port Already in Use
```bash
# Error: Port 8502 is already in use
# Solution: Find and stop conflicting process
lsof -i :8502
kill -9 <PID>

# Or use different port
uv run --env-file .env cd frontend && npm run dev --server.port=8503
```

#### Permission Denied (Docker)
```bash
# Error: Permission denied accessing Docker
# Solution: Add user to docker group
sudo usermod -aG docker $USER
# Log out and log back in
```

#### Python/uv Installation Issues
```bash
# Error: uv command not found
# Solution: Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Error: Python version conflict
# Solution: Use uv's Python management
uv python install 3.11
uv python pin 3.11
```

### API and Database Issues

#### Database Connection Failed
```bash
# Check if SurrealDB is running
docker compose ps surrealdb

# Check database logs
docker compose logs surrealdb

# Restart database
docker compose restart surrealdb
```

#### API Backend Not Responding
```bash
# Check API logs
docker compose logs api

# For source installation
# Check if API process is running
pgrep -f "run_api.py"

# Restart API
make api
```

#### Worker Not Processing Jobs
```bash
# Check worker status
pgrep -f "surreal-commands-worker"

# Restart worker
make worker-restart

# Check worker logs
docker compose logs worker
```

### AI Provider Issues

#### OpenAI API Key Errors
```bash
# Error: Invalid API key
# Solution: Verify key format and billing
# 1. Check key starts with "sk-"
# 2. Verify billing credits in OpenAI dashboard
# 3. Check API key permissions
```

#### Model Not Available
```bash
# Error: Model not found
# Solution: Check model availability
# 1. Verify model name in provider documentation
# 2. Check API key permissions
# 3. Try alternative model
```

#### Rate Limiting Issues
```bash
# Error: Rate limit exceeded
# Solution: Implement backoff strategy
# 1. Reduce concurrent requests
# 2. Upgrade provider plan
# 3. Use multiple providers
```

### Performance Issues

#### Slow Response Times
```bash
# Check system resources
top
docker stats

# Optimize database
# Consider increasing Docker memory limits
# Use faster storage (SSD)
```

#### Memory Issues
```bash
# Error: Out of memory
# Solution: Increase Docker memory
# 1. Docker Desktop → Settings → Resources
# 2. Increase memory limit to 4GB+
# 3. Consider model optimization
```

### Data and Storage Issues

#### Persistent Data Loss
```bash
# Ensure volumes are properly mounted
docker compose config

# Check volume permissions
ls -la ./notebook_data
ls -la ./surreal_data

# Fix permissions if needed
sudo chown -R $USER:$USER ./notebook_data
sudo chown -R $USER:$USER ./surreal_data
```

### Getting Help

#### Community Support
- **Discord**: https://discord.gg/37XJPXfz2w
- **GitHub Issues**: https://github.com/lfnovo/open-notebook/issues
- **Installation Assistant**: https://chatgpt.com/g/g-68776e2765b48191bd1bae3f30212631-open-notebook-installation-assistant

#### Bug Reports
When reporting issues, include:
1. Installation method (Docker/source)
2. Operating system and version
3. Error messages and logs
4. Steps to reproduce
5. Environment configuration (without API keys)

#### Log Collection
```bash
# Collect all logs
docker compose logs > open-notebook-logs.txt

# For source installation
make status > status.txt
```

---

## Next Steps

After successful installation:

1. **Read the User Guide**: Learn about features and workflows
2. **Check Model Providers**: Explore different AI providers for your needs
3. **Configure Transformations**: Set up custom content processing
4. **Explore API**: Use the REST API for integrations
5. **Join Community**: Connect with other users for tips and support

### Advanced Configuration

For advanced users:
- **Custom Prompts**: Customize AI behavior with Jinja templates
- **API Integration**: Build custom applications using the REST API
- **Multi-User Setup**: Configure for team usage
- **Backup Strategy**: Set up automated backups

### Performance Optimization

- **Model Selection**: Choose optimal models for your use case
- **Caching**: Configure appropriate cache settings
- **Resource Limits**: Tune Docker resource allocation
- **Monitoring**: Set up logging and monitoring

Welcome to Open Notebook! 🚀