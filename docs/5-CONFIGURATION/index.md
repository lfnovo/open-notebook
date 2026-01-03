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
- **OpenAI** (GPT-4o, GPT-4o-mini)
- **Anthropic** (Claude Sonnet, Haiku)
- **Google Gemini** (multi-modal, long context)
- **Groq** (ultra-fast inference)

Setup: Get API key → Set env var → Done

Cost: $0.01-0.10 per 1K tokens

→ Go to **[AI Providers Guide](ai-providers.md)**

### Option 2: Local (Free & Private)
- **Ollama** (open-source models, on your machine)
- **LM Studio** (desktop app)
- **OpenAI-compatible** (LM Studio, etc.)

Setup: Install/run locally → Set endpoint → Done

Cost: Free (electricity only)

→ Go to **[Ollama Setup](ai-providers.md#ollama-recommended-for-local)**

### Option 3: OpenAI-Compatible
- **LM Studio** (local)
- **Text Generation UI** (local)
- **Custom endpoints**

Setup: Point to your endpoint → Set API key → Done

Cost: Depends on service

→ Go to **[OpenAI-Compatible Guide](ai-providers.md)**

---

## Three Configuration Files

### `.env` (Local Development)
```
Located in: project root
Use for: Development on your machine
Format: KEY=value, one per line
```

### `docker.env` (Docker Deployment)
```
Located in: project root (or ./docker)
Use for: Docker deployments
Format: Same as .env
Loaded by: docker-compose.yml
```

### `.env.local` (Next.js Frontend)
```
Located in: frontend/
Use for: Frontend-specific settings
Currently: Just NEXT_PUBLIC_API_URL
```

---

## Most Important Settings

### For Every Setup

**1. Surreal Database**
```
SURREAL_URL=ws://surrealdb:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root  # Change in production!
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=staging  # or "production"
```

Usually pre-configured. Only change if using different database.

**2. AI Provider API Key**
```
Pick ONE:
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
GROQ_API_KEY=...
# Or for Ollama: No key needed
```

Required. You must set at least one.

**3. API URL (If Behind Reverse Proxy)**
```
API_URL=https://your-domain.com
# Usually auto-detected. Only set if needed.
```

Optional. Auto-detection works for most setups.

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

### [Server](server.md)
- API_URL (when and how)
- Ports and networking
- Timeouts and concurrency
- SSL/security

### [Advanced](advanced.md)
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

### Method 1: Edit `.env` File (Development)

```bash
1. Open .env in your editor
2. Find the section for your provider
3. Uncomment and fill in your API key
4. Save
5. Restart services
```

### Method 2: Set Docker Environment (Deployment)

```bash
# In docker-compose.yml:
services:
  api:
    environment:
      - OPENAI_API_KEY=sk-...
      - API_URL=https://your-domain.com
```

### Method 3: Export Environment Variables

```bash
# In your terminal:
export OPENAI_API_KEY=sk-...
export API_URL=https://your-domain.com

# Then start services
docker compose up
```

### Method 4: Use docker.env File

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
