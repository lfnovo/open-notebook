# AI Providers - Configuration Reference

Complete setup instructions for each AI provider. Pick the one you're using.

---

## Configuration Methods

| Method | Best For | Guide |
|--------|----------|-------|
| **Settings UI** | Most users | [API Configuration](../3-USER-GUIDE/api-configuration.md) |
| **Environment Variables** | DevOps, automation | This page |

**Recommended**: Use the Settings UI for quick setup. Environment variables are better for automated deployments.

---

## Cloud Providers (Recommended for Most)

### OpenAI

**Cost:** ~$0.03-0.15 per 1K tokens (varies by model)

**Setup:**
```bash
1. Go to https://platform.openai.com/api-keys
2. Create account (if needed)
3. Create new API key (starts with "sk-proj-")
4. Add $5+ credits to account
5. Add to .env:
   OPENAI_API_KEY=sk-proj-...
6. Restart services
```

**Environment Variable:**
```
OPENAI_API_KEY=sk-proj-xxxxx
```

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
- "Invalid API key" → Check key starts with "sk-proj-"
- "Rate limit exceeded" → Wait or upgrade account
- "Model not available" → Try gpt-4o-mini instead

---

### Anthropic (Claude)

**Cost:** ~$0.80-3.00 per 1M tokens (cheaper than OpenAI for long context)

**Setup:**
```bash
1. Go to https://console.anthropic.com/
2. Create account or login
3. Go to API keys section
4. Create new API key (starts with "sk-ant-")
5. Add to .env:
   ANTHROPIC_API_KEY=sk-ant-...
6. Restart services
```

**Environment Variable:**
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

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
- "Invalid API key" → Check it starts with "sk-ant-"
- "Overloaded" → Anthropic is busy, retry later
- "Model unavailable" → Check model name is correct

---

### Google Gemini

**Cost:** ~$0.075-0.30 per 1K tokens (competitive with OpenAI)

**Setup:**
```bash
1. Go to https://aistudio.google.com/app/apikey
2. Create account or login
3. Create new API key
4. Add to .env:
   GOOGLE_API_KEY=AIzaSy...
5. Restart services
```

**Environment Variable:**
```
GOOGLE_API_KEY=AIzaSy...
# Optional: override default endpoint
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta/models
```

**Available Models:**
- `gemini-2.0-flash-exp` — Latest experimental, fastest (recommended)
- `gemini-2.0-flash` — Stable version, fast, cheap
- `gemini-1.5-pro-latest` — More capable, longer context
- `gemini-1.5-flash` — Previous generation, very cheap

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
- "Model not found" → Check model name spelling

---

### Groq

**Cost:** ~$0.05 per 1M tokens (cheapest, but limited models)

**Setup:**
```bash
1. Go to https://console.groq.com/keys
2. Create account or login
3. Create new API key
4. Add to .env:
   GROQ_API_KEY=gsk_...
5. Restart services
```

**Environment Variable:**
```
GROQ_API_KEY=gsk_xxxxx
```

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
- "Model not available" → Check supported models list

---

### OpenRouter

**Cost:** Varies by model ($0.05-15 per 1M tokens)

**Setup:**
```bash
1. Go to https://openrouter.ai/keys
2. Create account or login
3. Add credits to your account
4. Create new API key
5. Add to .env:
   OPENROUTER_API_KEY=sk-or-...
6. Restart services
```

**Environment Variable:**
```
OPENROUTER_API_KEY=sk-or-xxxxx
```

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

**Setup:**
```bash
1. Install Ollama: https://ollama.ai
2. Run Ollama in background:
   ollama serve

3. Download a model:
   ollama pull mistral
   # or llama2, neural-chat, phi, etc.

4. Add to .env:
   OLLAMA_API_BASE=http://localhost:11434
   # If on different machine:
   # OLLAMA_API_BASE=http://10.0.0.5:11434

5. Restart services
```

**Environment Variable:**
```
OLLAMA_API_BASE=http://localhost:11434
```

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
- "Connection refused" → Ollama not running or wrong port
- "Model not found" → Download it: `ollama pull modelname`
- "Out of memory" → Use smaller model or add more RAM

---

### LM Studio (Local Alternative)

**Cost:** Free

**Setup:**
```bash
1. Download LM Studio: https://lmstudio.ai
2. Open app
3. Download a model from library
4. Go to "Local Server" tab
5. Start server (default port: 1234)
6. Add to .env:
   OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
   OPENAI_COMPATIBLE_API_KEY=not-needed
7. Restart services
```

**Environment Variables:**
```
OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
OPENAI_COMPATIBLE_API_KEY=lm-studio  # Just a placeholder
```

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

```bash
Add to .env:
OPENAI_COMPATIBLE_BASE_URL=http://your-endpoint/v1
OPENAI_COMPATIBLE_API_KEY=your-api-key
```

If you need different endpoints for different modalities:

```bash
# Language model
OPENAI_COMPATIBLE_BASE_URL_LLM=http://localhost:8000/v1
OPENAI_COMPATIBLE_API_KEY_LLM=sk-...

# Embeddings
OPENAI_COMPATIBLE_BASE_URL_EMBEDDING=http://localhost:8001/v1
OPENAI_COMPATIBLE_API_KEY_EMBEDDING=sk-...

# TTS (text-to-speech)
OPENAI_COMPATIBLE_BASE_URL_TTS=http://localhost:8002/v1
OPENAI_COMPATIBLE_API_KEY_TTS=sk-...
```

---

## Enterprise

### Azure OpenAI

**Cost:** Same as OpenAI (usage-based)

**Setup:**
```bash
1. Create Azure OpenAI service in Azure portal
2. Deploy GPT-4/3.5-turbo model
3. Get your endpoint and key
4. Add to .env:
   AZURE_OPENAI_API_KEY=your-key
   AZURE_OPENAI_ENDPOINT=https://your-name.openai.azure.com/
   AZURE_OPENAI_API_VERSION=2024-12-01-preview
5. Restart services
```

**Environment Variables:**
```
AZURE_OPENAI_API_KEY=xxxxx
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Optional: Different deployments for different modalities
AZURE_OPENAI_API_KEY_LLM=xxxxx
AZURE_OPENAI_ENDPOINT_LLM=https://your-instance.openai.azure.com/
AZURE_OPENAI_API_VERSION_LLM=2024-12-01-preview
```

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

By default, Open Notebook uses the LLM provider's embeddings. To use a different provider:

### OpenAI Embeddings (Default)
```
# Uses OpenAI's embedding model automatically
# Requires OPENAI_API_KEY
# No separate configuration needed
```

### Custom Embeddings
```
# For other embedding providers (future feature)
EMBEDDING_PROVIDER=openai  # or custom
```

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

**For privacy-first:** Ollama or LM Studio and [Speaches](local-tts.md)
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
3. **Add to .env**
4. **Restart services**
5. **Go to Settings → Models** in Open Notebook
6. **Verify it works** with a test chat

Done!

---

## Related

- **[Environment Reference](environment-reference.md)** - Complete list of all environment variables
- **[Advanced Configuration](advanced.md)** - Timeouts, SSL, performance tuning
- **[Ollama Setup](ollama.md)** - Detailed Ollama configuration guide
- **[OpenAI-Compatible](openai-compatible.md)** - LM Studio and other compatible providers
- **[Troubleshooting](../6-TROUBLESHOOTING/quick-fixes.md)** - Common issues and fixes
