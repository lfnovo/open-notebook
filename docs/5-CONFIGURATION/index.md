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

Setup: Get API key → Add credential in Settings UI → Done

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


### AI Provider (Credentials)

We need access to LLMs in order for the app to work. AI provider credentials are configured via the **Settings UI**:

1. Set `OPEN_NOTEBOOK_ENCRYPTION_KEY` in your environment (required for storing credentials)
2. Start services
3. Go to **Settings → API Keys → Add Credential**
4. Select your provider, paste your API key
5. **Test Connection** → **Discover Models** → **Register Models**

```
# Required in your .env or docker-compose.yml:
OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-key
```

> **Ollama users**: Add an Ollama credential in Settings → API Keys with the correct base URL. See [Ollama Setup](ollama.md) for network configuration help.

> **LM Studio / OpenAI-Compatible**: Add an OpenAI-Compatible credential in Settings → API Keys. See [OpenAI-Compatible Guide](openai-compatible.md).


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
OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-key
# Everything else uses defaults
# Then configure AI provider in Settings → API Keys
```

### Scenario 2: Docker on Remote Server
```env
# In docker.env:
OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-key
API_URL=http://your-server-ip:5055
```

### Scenario 3: Behind Reverse Proxy (Nginx/Cloudflare)
```env
# In docker.env:
OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-key
API_URL=https://your-domain.com
# The reverse proxy handles HTTPS
```

### Scenario 4: Using Ollama Locally
```env
# In .env:
OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-key
# Then add Ollama credential in Settings → API Keys
```

### Scenario 5: Using Azure OpenAI
```env
# In docker.env:
OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-key
# Then add Azure OpenAI credential in Settings → API Keys
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

### Method 1: Settings UI (For AI Provider Credentials)

The recommended way to configure AI providers:

```
1. Open Open Notebook in your browser
2. Go to Settings → API Keys
3. Click "Add Credential"
4. Select provider, enter API key
5. Click Save, then Test Connection
6. Click Discover Models → Register Models
```

No file editing, no restarts. Credentials stored securely (encrypted) in database.

→ **[Full Guide: API Configuration](../3-USER-GUIDE/api-configuration.md)**

### Method 2: Edit `.env` File (Infrastructure Settings)

For database, network, and encryption key settings:

```bash
1. Open .env in your editor
2. Set OPEN_NOTEBOOK_ENCRYPTION_KEY and database vars
3. Save
4. Restart services
```

### Method 3: Set Docker Environment (Deployment)

```bash
# In docker-compose.yml:
services:
  api:
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-key
      - API_URL=https://your-domain.com
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
| No credential configured | Models not available | Add credential in Settings → API Keys |
| Missing encryption key | Can't save credentials | Set OPEN_NOTEBOOK_ENCRYPTION_KEY |
| Wrong database URL | Can't start API | Check SURREAL_URL format |
| Expose port 5055 | "Can't connect to server" | Expose 5055 in docker-compose |
| Typo in env var | Settings ignored | Check spelling (case-sensitive!) |
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
1. Set `OPEN_NOTEBOOK_ENCRYPTION_KEY` in your environment
2. Start services
3. Add AI provider credential in Settings → API Keys
4. Done!

Everything else is optional optimization.
