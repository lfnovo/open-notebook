# AI Providers - Configuration Guide

Complete setup instructions for each AI provider via the **Settings UI**.

> **New in v1.2**: All AI provider credentials are now managed through the Settings UI. Environment variables for API keys are deprecated.

---

## How Provider Setup Works

Open Notebook uses a **credential-based system** for managing AI providers:

1. **Get your API key** from the provider's website
2. **Open Settings** → **API Keys** → **Add Credential**
3. **Test the connection** to verify it works
4. **Discover & Register Models** to make them available
5. **Start using** the provider in your notebooks

> **Prerequisite**: You must set `OPEN_NOTEBOOK_ENCRYPTION_KEY` in your docker-compose.yml before storing credentials. See [API Configuration](../3-USER-GUIDE/api-configuration.md#encryption-setup) for details.

---

## Cloud Providers (Recommended for Most)

### OpenAI

**Cost:** ~$0.03-0.15 per 1K tokens (varies by model)

**Get Your API Key:**
1. Go to https://platform.openai.com/api-keys
2. Create account (if needed)
3. Create new API key (starts with "sk-proj-")
4. Add $5+ credits to account

**Configure in Open Notebook:**
1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select provider: **OpenAI**
4. Give it a name (e.g., "My OpenAI Key")
5. Paste your API key
6. Click **Save**, then **Test Connection**
7. Click **Discover Models** to find available models
8. Click **Register Models** to make them available

**Available Models (in Open Notebook):**
- `gpt-4o` — Best quality, fast (latest version)
- `gpt-4o-mini` — Fast, cheap, good for testing
- `o1` — Advanced reasoning model (slower, more expensive)
- `o1-mini` — Faster reasoning model

**Recommended:**
- For general use: `gpt-4o` (best balance)
- For testing/cheap: `gpt-4o-mini` (90% cheaper)
- For complex reasoning: `o1` (best for hard problems)

**Cost Estimate:**
```
Light use: $1-5/month
Medium use: $10-30/month
Heavy use: $50-100+/month
```

**Troubleshooting:**
- "Invalid API key" → Check key starts with "sk-proj-" and test the connection in Settings
- "Rate limit exceeded" → Wait or upgrade account
- "Model not available" → Try gpt-4o-mini instead, or re-discover models

---

### Anthropic (Claude)

**Cost:** ~$0.80-3.00 per 1M tokens (cheaper than OpenAI for long context)

**Get Your API Key:**
1. Go to https://console.anthropic.com/
2. Create account or login
3. Go to API keys section
4. Create new API key (starts with "sk-ant-")

**Configure in Open Notebook:**
1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select provider: **Anthropic**
4. Give it a name, paste your API key
5. Click **Save**, then **Test Connection**
6. Click **Discover Models** → **Register Models**

**Available Models:**
- `claude-sonnet-4-5-20250929` — Latest, best quality (recommended)
- `claude-3-5-sonnet-20241022` — Previous generation, still excellent
- `claude-3-5-haiku-20241022` — Fast, cheap
- `claude-opus-4-5-20251101` — Most powerful, expensive

**Recommended:**
- For general use: `claude-sonnet-4-5` (best overall, latest)
- For cheap: `claude-3-5-haiku` (80% cheaper)
- For complex: `claude-opus-4-5` (most capable)

**Cost Estimate:**
```
Sonnet: $3-20/month (typical use)
Haiku: $0.50-3/month
Opus: $10-50+/month
```

**Advantages:**
- Great long-context support (200K tokens)
- Excellent reasoning
- Fast processing

**Troubleshooting:**
- "Invalid API key" → Check it starts with "sk-ant-" and test in Settings
- "Overloaded" → Anthropic is busy, retry later
- "Model unavailable" → Re-discover models from the credential

---

### Google Gemini

**Cost:** ~$0.075-0.30 per 1K tokens (competitive with OpenAI)

**Get Your API Key:**
1. Go to https://aistudio.google.com/app/apikey
2. Create account or login
3. Create new API key

**Configure in Open Notebook:**
1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select provider: **Google Gemini**
4. Give it a name, paste your API key
5. Click **Save**, then **Test Connection**
6. Click **Discover Models** → **Register Models**

**Available Models:**
- `gemini-2.0-flash-exp` — Latest experimental, fastest (recommended)
- `gemini-2.0-flash` — Stable version, fast, cheap

**Recommended:**
- For general use: `gemini-2.0-flash-exp` (best value, latest)
- For cheap: `gemini-1.5-flash` (very cheap)
- For complex/long context: `gemini-1.5-pro-latest` (2M token context)

**Advantages:**
- Very long context (1M tokens)
- Multimodal (images, audio, video)
- Good for podcasts

**Troubleshooting:**
- "API key invalid" → Get fresh key from aistudio.google.com
- "Quota exceeded" → Free tier limited, upgrade account
- "Model not found" → Re-discover models from the credential

---

### Groq

**Cost:** ~$0.05 per 1M tokens (cheapest, but limited models)

**Get Your API Key:**
1. Go to https://console.groq.com/keys
2. Create account or login
3. Create new API key

**Configure in Open Notebook:**
1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select provider: **Groq**
4. Give it a name, paste your API key
5. Click **Save**, then **Test Connection**
6. Click **Discover Models** → **Register Models**

**Available Models:**
- `llama-3.3-70b-versatile` — Best on Groq (recommended)
- `llama-3.1-70b-versatile` — Fast, capable
- `mixtral-8x7b-32768` — Good alternative
- `gemma2-9b-it` — Small, very fast

**Recommended:**
- For quality: `llama-3.3-70b-versatile` (best overall)
- For speed: `gemma2-9b-it` (ultra-fast)
- For balance: `llama-3.1-70b-versatile`

**Advantages:**
- Ultra-fast inference
- Very cheap
- Great for transformations/batch work

**Disadvantages:**
- Limited model selection
- Smaller models than OpenAI/Anthropic

**Troubleshooting:**
- "Rate limited" → Free tier has limits, upgrade
- "Model not available" → Re-discover models from the credential

---

### OpenRouter

**Cost:** Varies by model ($0.05-15 per 1M tokens)

**Get Your API Key:**
1. Go to https://openrouter.ai/keys
2. Create account or login
3. Add credits to your account
4. Create new API key

**Configure in Open Notebook:**
1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select provider: **OpenRouter**
4. Give it a name, paste your API key
5. Click **Save**, then **Test Connection**
6. Click **Discover Models** → **Register Models**

**Available Models (100+ options):**
- OpenAI: `openai/gpt-4o`, `openai/o1`
- Anthropic: `anthropic/claude-sonnet-4.5`, `anthropic/claude-3.5-haiku`
- Google: `google/gemini-2.0-flash-exp`, `google/gemini-1.5-pro`
- Meta: `meta-llama/llama-3.3-70b-instruct`, `meta-llama/llama-3.1-405b-instruct`
- Mistral: `mistralai/mistral-large-2411`
- DeepSeek: `deepseek/deepseek-chat`
- And many more...

**Recommended:**
- For quality: `anthropic/claude-sonnet-4.5` (best overall)
- For speed/cost: `google/gemini-2.0-flash-exp` (very fast, cheap)
- For open-source: `meta-llama/llama-3.3-70b-instruct`
- For reasoning: `openai/o1`

**Advantages:**
- One API key for 100+ models
- Unified billing
- Easy model comparison
- Access to models that may have waitlists elsewhere

**Cost Estimate:**
```
Light use: $1-5/month
Medium use: $10-30/month
Heavy use: Depends on models chosen
```

**Troubleshooting:**
- "Invalid API key" → Check it starts with "sk-or-"
- "Insufficient credits" → Add credits at openrouter.ai
- "Model not available" → Check model ID spelling (use full path)

---

## Self-Hosted / Local

### Ollama (Recommended for Local)

**Cost:** Free (electricity only)

**Setup Ollama:**
1. Install Ollama: https://ollama.ai
2. Run Ollama in background: `ollama serve`
3. Download a model: `ollama pull mistral`

**Configure in Open Notebook:**
1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select provider: **Ollama**
4. Give it a name (e.g., "Local Ollama")
5. Enter the base URL:
   - Same machine (non-Docker): `http://localhost:11434`
   - Docker with Ollama on host: `http://host.docker.internal:11434`
   - Docker with Ollama container: `http://ollama:11434`
6. Click **Save**, then **Test Connection**
7. Click **Discover Models** → **Register Models**

See [Ollama Setup Guide](ollama.md) for detailed network configuration.

**Available Models:**
- `llama3.3:70b` — Best quality (requires 40GB+ RAM)
- `llama3.1:8b` — Recommended, balanced (8GB RAM)
- `qwen2.5:7b` — Excellent for code and reasoning
- `mistral:7b` — Good general purpose
- `phi3:3.8b` — Small, fast (4GB RAM)
- `gemma2:9b` — Google's model, balanced
- Many more: `ollama list` to see available

**Recommended:**
- For quality (with GPU): `llama3.3:70b` (best)
- For general use: `llama3.1:8b` (best balance)
- For speed/low memory: `phi3:3.8b` (very fast)
- For coding: `qwen2.5:7b` (excellent at code)

**Hardware Requirements:**
```
GPU (NVIDIA/AMD):
  8GB VRAM: Runs most models fine
  6GB VRAM: Works, slower
  4GB VRAM: Small models only

CPU-only:
  16GB+ RAM: Slow but works
  8GB RAM: Very slow
  4GB RAM: Not recommended
```

**Advantages:**
- Completely private (runs locally)
- Free (electricity only)
- No API key needed
- Works offline

**Disadvantages:**
- Slower than cloud (unless on GPU)
- Smaller models than cloud
- Requires local hardware

**Troubleshooting:**
- "Connection refused" → Ollama not running or wrong URL in credential
- "Model not found" → Download it: `ollama pull modelname`
- "Out of memory" → Use smaller model or add more RAM

---

### LM Studio (Local Alternative)

**Cost:** Free

**Setup LM Studio:**
1. Download LM Studio: https://lmstudio.ai
2. Open app
3. Download a model from library
4. Go to "Local Server" tab
5. Start server (default port: 1234)

**Configure in Open Notebook:**
1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select provider: **OpenAI-Compatible**
4. Give it a name (e.g., "LM Studio")
5. Enter the base URL: `http://host.docker.internal:1234/v1` (Docker) or `http://localhost:1234/v1` (local)
6. API key: `lm-studio` (placeholder, LM Studio doesn't require one)
7. Click **Save**, then **Test Connection**

**Advantages:**
- GUI interface (easier than Ollama CLI)
- Good model selection
- Privacy-focused
- Works offline

**Disadvantages:**
- Desktop only (Mac/Windows/Linux)
- Slower than cloud
- Requires local GPU

---

### Custom OpenAI-Compatible

For Text Generation UI, vLLM, or other OpenAI-compatible endpoints:

1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select provider: **OpenAI-Compatible**
4. Enter the base URL for your endpoint (e.g., `http://localhost:8000/v1`)
5. Enter API key if required
6. Optionally configure per-service URLs (LLM, Embedding, TTS, STT)
7. Click **Save**, then **Test Connection**

See [OpenAI-Compatible Setup](openai-compatible.md) for detailed instructions.

---

## Enterprise

### Azure OpenAI

**Cost:** Same as OpenAI (usage-based)

**Configure in Open Notebook:**
1. Create Azure OpenAI service in Azure portal
2. Deploy GPT-4/3.5-turbo model
3. Get your endpoint and key
4. Go to **Settings** → **API Keys**
5. Click **Add Credential**
6. Select provider: **Azure OpenAI**
7. Fill in: API Key, Endpoint, API Version
8. Optionally configure service-specific endpoints (LLM, Embedding)
9. Click **Save**, then **Test Connection**

**Advantages:**
- Enterprise support
- VPC integration
- Compliance (HIPAA, SOC2, etc.)

**Disadvantages:**
- More complex setup
- Higher overhead
- Requires Azure account

---

## Embeddings (For Search/Semantic Features)

By default, Open Notebook uses the LLM provider's embeddings. Embedding models are discovered and registered through the same credential system — when you discover models from a credential, embedding models are included alongside language models.

---

## Choosing Your Provider

**1. Don't want to run locally and don't want to mess around with different providers:**

Use OpenAI
- Cloud-based
- Good quality
- Reasonable cost
- Simplest setup, supports all modes (text, embedding, tts, stt, etc)

**For budget-conscious:** Groq, OpenRouter or Ollama
- Groq: Super cheap cloud
- Ollama: Free, but local
- OpenRouter: many open source models very accessible

**For privacy-first:** Ollama or LM Studio and Speaches ([TTS](local-tts.md), [STT](local-stt.md))
- Everything stays local
- Works offline
- No API keys sent anywhere

**For enterprise:** Azure OpenAI
- Compliance
- VPC integration
- Support

---

## Next Steps

1. **Choose your provider** from above
2. **Get API key** (if cloud) or install locally (if Ollama)
3. **Set `OPEN_NOTEBOOK_ENCRYPTION_KEY`** in your docker-compose.yml (required for storing credentials)
4. **Open Settings** → **API Keys** → **Add Credential**
5. **Test Connection** to verify it works
6. **Discover & Register Models** to make them available
7. **Verify it works** with a test chat

> **Multiple providers**: You can add credentials for as many providers as you want. Create separate credentials for different projects or team members.

Done!

---

## Legacy: Environment Variables (Deprecated)

> **Deprecated**: Configuring AI provider API keys via environment variables is deprecated. Use the Settings UI instead. Environment variables may still work as a fallback but are no longer the recommended approach.

If you are migrating from an older version that used environment variables, go to **Settings** → **API Keys** and click the **Migrate to Database** button to import your existing keys into the credential system.

---

## Related

- **[API Configuration](../3-USER-GUIDE/api-configuration.md)** — Detailed credential management guide
- **[Environment Reference](environment-reference.md)** - Complete list of all environment variables
- **[Advanced Configuration](advanced.md)** - Timeouts, SSL, performance tuning
- **[Ollama Setup](ollama.md)** - Detailed Ollama configuration guide
- **[OpenAI-Compatible](openai-compatible.md)** - LM Studio and other compatible providers
- **[Local TTS Setup](local-tts.md)** - Text-to-speech with Speaches
- **[Local STT Setup](local-stt.md)** - Speech-to-text with Speaches
- **[Troubleshooting](../6-TROUBLESHOOTING/quick-fixes.md)** - Common issues and fixes
