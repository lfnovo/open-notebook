# Configuration - Essential Settings

Configuration is how you customize Open Notebook for your specific setup. This section covers what you need to know.

---

## What Needs Configuration?

Three things:

1. **AI Provider** — Which LLM/embedding service you're using (OpenAI, Anthropic, Ollama, etc.)
2. **Database** — How to connect to SurrealDB (usually pre-configured)
3. **Server** — API URL, ports, timeouts (usually auto-detected)

---

## Quick Decision: Which Provider?

### Option 1: Cloud Provider (Fastest)
- **OpenRouter (recommended)** (access to all models with one key)
- **OpenAI** (GPT)
- **Anthropic** (Claude)
- **Google Gemini** (multi-modal, long context)
- **Groq** (ultra-fast inference)

Setup: Get API key → Set env var → Done

→ Go to **[AI Providers Guide](ai-providers.md)**

### Option 2: Local (Free & Private)
- **Ollama** (open-source models, on your machine)

→ Go to **[Ollama Setup](ollama.md)**

### Option 3: OpenAI-Compatible
- **LM Studio** (local)
- **Custom endpoints**

→ Go to **[OpenAI-Compatible Guide](openai-compatible.md)**

---

## Configuration File

Use the right file depending on your setup.

### `.env` (Local Development)

You will only use .env if you are running Open Notebook locally.

```
Located in: project root
Use for: Development on your machine
Format: KEY=value, one per line
```

### `docker.env` (Docker Deployment)

You will use this file to hold your environment variables if you are using docker-compose and prefer not to put the variables directly in the compose file. 
```
Located in: project root (or ./docker)
Use for: Docker deployments
Format: Same as .env
Loaded by: docker-compose.yml
```

---

## Most Important Settings

All of the settings provided below are to be placed inside your environment file (.env or docker.env depending on your setup).


###  Surreal Database

This is the database used by the app.

```
SURREAL_URL=ws://surrealdb:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root  # Change in production!
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=open_notebook
```

> The only thing that is critical to not miss is the hostname in the `SURREAL_URL`. Check what URL to use based on your deployment, [here](database.md).


### AI Provider (API Key or URL)

We need access to LLMs in order for the app to work. You can use any of the support AI Providers by adding their API Keys. 

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OPENROUTER_API_KEY=...
```

Or, if you are planning to use only local providers, you can setup Ollama by configuring it's base URL. This will get you set and ready with text and embeddings in one go: 

```
OLLAMA_BASE_URL=http://localhost:11434
```

> A lot of people screw up on the Ollama BASE URL by not knowing how to point to their Ollama installation. if you are having trouble connecting to Ollama, see [here](ollama.md).

You can also use LM Studio locally if you prefer by using it as an OpenAI compatible endpoint. 

```
OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
OPENAI_COMPATIBLE_BASE_URL_EMBEDDING=http://localhost:1234/v1
```

> For more installation on using OpenAI compatible endpoints, see [here](openai-compatible.md).


### API URL (If Behind Reverse Proxy)
You only need to worry about this if you are deploying on a proxy or if you are changing port information. Otherwise, skip this.

```
API_URL=https://your-domain.com
# Usually auto-detected. Only set if needed.
```

Auto-detection works for most setups.

---

## Configuration by Scenario

### Scenario 1: Docker on Localhost (Default)
```env
# In docker.env:
OPENAI_API_KEY=sk-...
# Everything else uses defaults
# Done!
```

### Scenario 2: Docker on Remote Server
```env
# In docker.env:
OPENAI_API_KEY=sk-...
API_URL=http://your-server-ip:5055
```

### Scenario 3: Behind Reverse Proxy (Nginx/Cloudflare)
```env
# In docker.env:
OPENAI_API_KEY=sk-...
API_URL=https://your-domain.com
# The reverse proxy handles HTTPS
```

### Scenario 4: Using Ollama Locally
```env
# In .env:
OLLAMA_API_BASE=http://localhost:11434
# No API key needed
```

### Scenario 5: Using Azure OpenAI
```env
# In docker.env:
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

---

## Configuration Sections

### [AI Providers](ai-providers.md)
- OpenAI configuration
- Anthropic configuration
- Google Gemini configuration
- Groq configuration
- Ollama configuration
- Azure OpenAI configuration
- OpenAI-compatible configuration

### [Database](database.md)
- SurrealDB setup
- Connection strings
- Database vs. namespace
- Running your own SurrealDB

### [Advanced](advanced.md)
- Ports and networking
- Timeouts and concurrency
- SSL/security
- Retry configuration
- Worker concurrency
- Language models & embeddings
- Speech-to-text & text-to-speech
- Debugging and logging

### [Reverse Proxy](reverse-proxy.md)
- Nginx, Caddy, Traefik configs
- Custom domain setup
- SSL/HTTPS configuration
- Coolify and other platforms

### [Security](security.md)
- Password protection
- API authentication
- Production hardening
- Firewall configuration

### [Local TTS](local-tts.md)
- Speaches setup for local text-to-speech
- GPU acceleration
- Voice options
- Docker networking

### [Local STT](local-stt.md)
- Speaches setup for local speech-to-text
- Whisper model options
- GPU acceleration
- Docker networking

### [Ollama](ollama.md)
- Setting up and pointing to an Ollama server
- Downloading models
- Using embedding

### [OpenAI-Compatible Providers](openai-compatible.md)
- LM Studio, vLLM, Text Generation WebUI
- Connection configuration
- Docker networking
- Troubleshooting

### [Complete Reference](environment-reference.md)
- All environment variables
- Grouped by category
- What each one does
- Default values

---

## How to Add Configuration

### Method 1: Settings UI (Recommended for API Keys)

The easiest way to configure API keys:

```
1. Open Open Notebook in your browser
2. Go to Settings → API Keys
3. Find your provider
4. Enter API key
5. Click Save
6. Click Test Connection to verify
```

No file editing, no restarts. Keys stored securely in database.

**Note:** While the Settings UI is recommended for API keys, some settings (like SurrealDB connection, server ports) still require environment variables or docker-compose configuration.

→ **[Full Guide: API Configuration](../3-USER-GUIDE/api-configuration.md)**

### Method 2: Edit `.env` File (Development)

```bash
1. Open .env in your editor
2. Find the section for your provider
3. Uncomment and fill in your API key
4. Save
5. Restart services
```

### Method 3: Set Docker Environment (Deployment)

```bash
# In docker-compose.yml:
services:
  api:
    environment:
      - OPENAI_API_KEY=sk-...
      - API_URL=https://your-domain.com
```

### Method 4: Export Environment Variables

```bash
# In your terminal:
export OPENAI_API_KEY=sk-...
export API_URL=https://your-domain.com

# Then start services
docker compose up
```

### Method 5: Use docker.env File

```bash
1. Create/edit docker.env
2. Add your configuration
3. docker-compose automatically loads it
4. docker compose up
```

---

## Verification

After configuration, verify it works:

```
1. Open your notebook
2. Go to Settings → Models
3. You should see your configured provider
4. Try a simple Chat question
5. If it responds, configuration is correct!
```

---

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Forget API key | Models not available | Add OPENAI_API_KEY (or your provider) |
| Wrong database URL | Can't start API | Check SURREAL_URL format |
| Expose port 5055 | "Can't connect to server" | Expose 5055 in docker-compose |
| Typo in env var | Settings ignored | Check spelling (case-sensitive!) |
| Quote mismatch | Value cut off | Use quotes: OPENAI_API_KEY="sk-..." |
| Don't restart | Old config still used | Restart services after env changes |

---

## What Comes After Configuration

Once configured:

1. **[Quick Start](../0-START-HERE/index.md)** — Run your first notebook
2. **[Installation](../1-INSTALLATION/index.md)** — Multi-route deployment guides
3. **[User Guide](../3-USER-GUIDE/index.md)** — How to use each feature

---

## Getting Help

- **Configuration error?** → Check [Troubleshooting](../6-TROUBLESHOOTING/quick-fixes.md)
- **Provider-specific issue?** → Check [AI Providers](ai-providers.md)
- **Need complete reference?** → See [Environment Reference](environment-reference.md)

---

## Summary

**Minimal configuration to run:**
1. Choose an AI provider (or use Ollama locally)
2. Set API key in .env or docker.env
3. Start services
4. Done!

Everything else is optional optimization.
