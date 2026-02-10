# Complete Environment Reference

Comprehensive list of all environment variables available in Open Notebook.

---

## API Configuration

| Variable | Required? | Default | Description |
|----------|-----------|---------|-------------|
| `API_URL` | No | Auto-detected | URL where frontend reaches API (e.g., http://localhost:5055) |
| `INTERNAL_API_URL` | No | http://localhost:5055 | Internal API URL for Next.js server-side proxying |
| `API_CLIENT_TIMEOUT` | No | 300 | Client timeout in seconds (how long to wait for API response) |
| `OPEN_NOTEBOOK_PASSWORD` | No | None | Password to protect Open Notebook instance |
| `OPEN_NOTEBOOK_ENCRYPTION_KEY` | **Yes** | None | Secret string to encrypt credentials stored in database (any string works). **Required** for the credential system. Supports Docker secrets via `_FILE` suffix. |
| `HOSTNAME` | No | `0.0.0.0` (in Docker) | Network interface for Next.js to bind to. Default `0.0.0.0` ensures accessibility from reverse proxies |

> **Important**: `OPEN_NOTEBOOK_ENCRYPTION_KEY` is required for storing AI provider credentials via the Settings UI. Without it, you cannot save credentials. If you change or lose this key, all stored credentials become unreadable.

---

## Database: SurrealDB

| Variable | Required? | Default | Description |
|----------|-----------|---------|-------------|
| `SURREAL_URL` | Yes | ws://surrealdb:8000/rpc | SurrealDB WebSocket connection URL |
| `SURREAL_USER` | Yes | root | SurrealDB username |
| `SURREAL_PASSWORD` | Yes | root | SurrealDB password |
| `SURREAL_NAMESPACE` | Yes | open_notebook | SurrealDB namespace |
| `SURREAL_DATABASE` | Yes | open_notebook | SurrealDB database name |

---

## Database: Retry Configuration

| Variable | Required? | Default | Description |
|----------|-----------|---------|-------------|
| `SURREAL_COMMANDS_RETRY_ENABLED` | No | true | Enable retries on failure |
| `SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS` | No | 3 | Maximum retry attempts |
| `SURREAL_COMMANDS_RETRY_WAIT_STRATEGY` | No | exponential_jitter | Retry wait strategy (exponential_jitter/exponential/fixed/random) |
| `SURREAL_COMMANDS_RETRY_WAIT_MIN` | No | 1 | Minimum wait time between retries (seconds) |
| `SURREAL_COMMANDS_RETRY_WAIT_MAX` | No | 30 | Maximum wait time between retries (seconds) |

---

## Database: Concurrency

| Variable | Required? | Default | Description |
|----------|-----------|---------|-------------|
| `SURREAL_COMMANDS_MAX_TASKS` | No | 5 | Maximum concurrent database tasks |

---

## LLM Timeouts

| Variable | Required? | Default | Description |
|----------|-----------|---------|-------------|
| `ESPERANTO_LLM_TIMEOUT` | No | 60 | LLM inference timeout in seconds |
| `ESPERANTO_SSL_VERIFY` | No | true | Verify SSL certificates (false = development only) |
| `ESPERANTO_SSL_CA_BUNDLE` | No | None | Path to custom CA certificate bundle |

---

## Text-to-Speech (TTS)

| Variable | Required? | Default | Description |
|----------|-----------|---------|-------------|
| `TTS_BATCH_SIZE` | No | 5 | Concurrent TTS requests (1-5, depends on provider) |

---

## Content Extraction

| Variable | Required? | Default | Description |
|----------|-----------|---------|-------------|
| `FIRECRAWL_API_KEY` | No | None | Firecrawl API key for advanced web scraping |
| `JINA_API_KEY` | No | None | Jina AI API key for web extraction |

**Setup:**
- Firecrawl: https://firecrawl.dev/
- Jina: https://jina.ai/

---

## Network / Proxy

| Variable | Required? | Default | Description |
|----------|-----------|---------|-------------|
| `HTTP_PROXY` | No | None | HTTP proxy URL for outbound HTTP requests |
| `HTTPS_PROXY` | No | None | HTTPS proxy URL for outbound HTTPS requests |
| `NO_PROXY` | No | None | Comma-separated list of hosts to bypass proxy |

Route all outbound HTTP requests through a proxy server. Useful for corporate/firewalled environments.

The underlying libraries (esperanto, content-core, podcast-creator) automatically detect proxy settings from these standard environment variables.

**Affects:**
- AI provider API calls (OpenAI, Anthropic, Google, Groq, etc.)
- Content extraction from URLs (web scraping, YouTube transcripts)
- Podcast generation (LLM and TTS provider calls)

**Format:** `http://[user:pass@]host:port` or `https://[user:pass@]host:port`

**Examples:**
```bash
# Basic proxy
HTTP_PROXY=http://proxy.corp.com:8080
HTTPS_PROXY=http://proxy.corp.com:8080

# Authenticated proxy
HTTP_PROXY=http://user:password@proxy.corp.com:8080
HTTPS_PROXY=http://user:password@proxy.corp.com:8080

# Bypass proxy for local hosts
NO_PROXY=localhost,127.0.0.1,.local
```

---

## Debugging & Monitoring

| Variable | Required? | Default | Description |
|----------|-----------|---------|-------------|
| `LANGCHAIN_TRACING_V2` | No | false | Enable LangSmith tracing |
| `LANGCHAIN_ENDPOINT` | No | https://api.smith.langchain.com | LangSmith endpoint |
| `LANGCHAIN_API_KEY` | No | None | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | Open Notebook | LangSmith project name |

**Setup:** https://smith.langchain.com/

---

## Environment Variables by Use Case

### Minimal Setup (New Installation)
```
OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-key
SURREAL_URL=ws://surrealdb:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=password
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=open_notebook
```
Then configure AI providers via **Settings → API Keys** in the browser.

### Production Deployment
```
OPEN_NOTEBOOK_ENCRYPTION_KEY=your-strong-secret-key
OPEN_NOTEBOOK_PASSWORD=your-secure-password
API_URL=https://mynotebook.example.com
SURREAL_USER=production_user
SURREAL_PASSWORD=secure_password
```

### Self-Hosted Behind Reverse Proxy
```
OPEN_NOTEBOOK_ENCRYPTION_KEY=your-secret-key
API_URL=https://mynotebook.example.com
```

### Corporate Environment (Behind Proxy)
```
OPEN_NOTEBOOK_ENCRYPTION_KEY=your-secret-key
HTTP_PROXY=http://proxy.corp.com:8080
HTTPS_PROXY=http://proxy.corp.com:8080
NO_PROXY=localhost,127.0.0.1
```

### High-Performance Deployment
```
OPEN_NOTEBOOK_ENCRYPTION_KEY=your-secret-key
SURREAL_COMMANDS_MAX_TASKS=10
TTS_BATCH_SIZE=5
API_CLIENT_TIMEOUT=600
```

### Debugging
```
OPEN_NOTEBOOK_ENCRYPTION_KEY=your-secret-key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-key
```

---

## Validation

Check if a variable is set:

```bash
# Check single variable
echo $OPEN_NOTEBOOK_ENCRYPTION_KEY

# Check multiple
env | grep -E "OPEN_NOTEBOOK|API_URL"

# Print all config
env | grep -E "^[A-Z_]+=" | sort
```

---

## Notes

- **Case-sensitive:** `OPEN_NOTEBOOK_ENCRYPTION_KEY` ≠ `open_notebook_encryption_key`
- **No spaces:** `OPEN_NOTEBOOK_ENCRYPTION_KEY=my-key` not `OPEN_NOTEBOOK_ENCRYPTION_KEY = my-key`
- **Quote values:** Use quotes for values with spaces: `API_URL="http://my server:5055"`
- **Restart required:** Changes take effect after restarting services
- **Secrets:** Don't commit encryption keys or passwords to git
- **AI Providers:** Configure via **Settings → API Keys** in the browser (not via env vars)
- **Migration:** Use Settings UI to migrate existing env vars to the credential system. See [API Configuration](../3-USER-GUIDE/api-configuration.md#migrating-from-environment-variables)

---

## Quick Setup Checklist

- [ ] Set `OPEN_NOTEBOOK_ENCRYPTION_KEY` in docker-compose.yml
- [ ] Set database credentials (`SURREAL_*`)
- [ ] Start services
- [ ] Open browser → Go to **Settings → API Keys**
- [ ] **Add Credential** for your AI provider
- [ ] **Test Connection** to verify
- [ ] **Discover & Register Models**
- [ ] Set `API_URL` if behind reverse proxy
- [ ] Change `SURREAL_PASSWORD` in production
- [ ] Try a test chat

Done!

---

## Legacy: AI Provider Environment Variables (Deprecated)

> **Deprecated**: The following AI provider API key environment variables are deprecated. Configure providers via the Settings UI instead. These variables may still work as a fallback but are no longer recommended.

If you have these variables configured from a previous installation, click the **Migrate to Database** button in **Settings → API Keys** to import them into the credential system, then remove them from your configuration.

| Variable | Provider | Replacement |
|----------|----------|-------------|
| `OPENAI_API_KEY` | OpenAI | Settings → API Keys → Add OpenAI Credential |
| `ANTHROPIC_API_KEY` | Anthropic | Settings → API Keys → Add Anthropic Credential |
| `GOOGLE_API_KEY` | Google Gemini | Settings → API Keys → Add Google Credential |
| `GEMINI_API_BASE_URL` | Google Gemini | Configure in Google Gemini credential |
| `VERTEX_PROJECT` | Vertex AI | Settings → API Keys → Add Vertex AI Credential |
| `VERTEX_LOCATION` | Vertex AI | Configure in Vertex AI credential |
| `GOOGLE_APPLICATION_CREDENTIALS` | Vertex AI | Configure in Vertex AI credential |
| `GROQ_API_KEY` | Groq | Settings → API Keys → Add Groq Credential |
| `MISTRAL_API_KEY` | Mistral | Settings → API Keys → Add Mistral Credential |
| `DEEPSEEK_API_KEY` | DeepSeek | Settings → API Keys → Add DeepSeek Credential |
| `XAI_API_KEY` | xAI | Settings → API Keys → Add xAI Credential |
| `OLLAMA_API_BASE` | Ollama | Settings → API Keys → Add Ollama Credential |
| `OPENROUTER_API_KEY` | OpenRouter | Settings → API Keys → Add OpenRouter Credential |
| `OPENROUTER_BASE_URL` | OpenRouter | Configure in OpenRouter credential |
| `VOYAGE_API_KEY` | Voyage AI | Settings → API Keys → Add Voyage AI Credential |
| `ELEVENLABS_API_KEY` | ElevenLabs | Settings → API Keys → Add ElevenLabs Credential |
| `OPENAI_COMPATIBLE_BASE_URL` | OpenAI-Compatible | Settings → API Keys → Add OpenAI-Compatible Credential |
| `OPENAI_COMPATIBLE_API_KEY` | OpenAI-Compatible | Configure in OpenAI-Compatible credential |
| `OPENAI_COMPATIBLE_BASE_URL_LLM` | OpenAI-Compatible | Configure per-service URL in credential |
| `OPENAI_COMPATIBLE_API_KEY_LLM` | OpenAI-Compatible | Configure per-service key in credential |
| `OPENAI_COMPATIBLE_BASE_URL_EMBEDDING` | OpenAI-Compatible | Configure per-service URL in credential |
| `OPENAI_COMPATIBLE_API_KEY_EMBEDDING` | OpenAI-Compatible | Configure per-service key in credential |
| `OPENAI_COMPATIBLE_BASE_URL_STT` | OpenAI-Compatible | Configure per-service URL in credential |
| `OPENAI_COMPATIBLE_API_KEY_STT` | OpenAI-Compatible | Configure per-service key in credential |
| `OPENAI_COMPATIBLE_BASE_URL_TTS` | OpenAI-Compatible | Configure per-service URL in credential |
| `OPENAI_COMPATIBLE_API_KEY_TTS` | OpenAI-Compatible | Configure per-service key in credential |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI | Settings → API Keys → Add Azure OpenAI Credential |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI | Configure in Azure OpenAI credential |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI | Configure in Azure OpenAI credential |
| `AZURE_OPENAI_API_KEY_LLM` | Azure OpenAI | Configure per-service in credential |
| `AZURE_OPENAI_ENDPOINT_LLM` | Azure OpenAI | Configure per-service in credential |
| `AZURE_OPENAI_API_VERSION_LLM` | Azure OpenAI | Configure per-service in credential |
| `AZURE_OPENAI_API_KEY_EMBEDDING` | Azure OpenAI | Configure per-service in credential |
| `AZURE_OPENAI_ENDPOINT_EMBEDDING` | Azure OpenAI | Configure per-service in credential |
| `AZURE_OPENAI_API_VERSION_EMBEDDING` | Azure OpenAI | Configure per-service in credential |
