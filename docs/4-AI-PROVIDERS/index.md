# AI Providers - Setup & Configuration

Open Notebook supports 15+ AI providers. This section helps you choose and configure yours.

---

## Quick Decision: Which Provider?

### Cloud Providers (Easiest)

**OpenAI (Recommended)**
- Models: GPT-4o, GPT-4o-mini
- Cost: ~$0.03-0.15 per 1K tokens
- Speed: Very fast
- Setup: 5 minutes
- Best for: Most users (best quality/price balance)

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#openai)

**Anthropic (Claude)**
- Models: Claude 3.5 Sonnet, Haiku, Opus
- Cost: ~$0.80-3.00 per 1M tokens
- Speed: Fast
- Setup: 5 minutes
- Best for: Long context, reasoning
- Advantage: 200K token context

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#anthropic-claude)

**Google Gemini**
- Models: Gemini 2.0 Flash, 1.5 Pro
- Cost: ~$0.075-0.30 per 1K tokens
- Speed: Very fast
- Setup: 5 minutes
- Best for: Multimodal (images, audio, video)
- Advantage: 1M token context

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#google-gemini)

**Groq (Ultra-Fast)**
- Models: Mixtral, Llama 3.3
- Cost: ~$0.05 per 1M tokens (cheapest)
- Speed: Ultra-fast (fastest available)
- Setup: 5 minutes
- Best for: Budget-conscious, transformations
- Disadvantage: Limited model selection

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#groq)

**OpenRouter (100+ Models)**
- Models: Access to OpenAI, Anthropic, Google, Llama, Mistral, and 100+ more
- Cost: Pay-per-model (varies)
- Speed: Varies by model
- Setup: 5 minutes
- Best for: Model comparison, testing many models, unified billing
- Advantage: One API key for all models

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#openrouter)

### Local / Self-Hosted (Free)

**Ollama (Recommended for Local)**
- Models: Mistral, Llama 2, Phi, Neural Chat
- Cost: Free (electricity only)
- Speed: Depends on hardware (slow on CPU, fast on GPU)
- Setup: 10 minutes
- Best for: Privacy-first, offline use
- Privacy: 100% local, nothing leaves your machine

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#ollama-local)

**LM Studio (Alternative)**
- GUI-based local LLM runner
- Cost: Free
- Speed: Depends on hardware
- Setup: 15 minutes (GUI easier than Ollama CLI)
- Best for: Non-technical users
- Privacy: 100% local

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#lm-studio-local-alternative)

### Enterprise

**Azure OpenAI**
- Same as OpenAI but on Azure
- Cost: Same as OpenAI
- Setup: 10 minutes (more complex)
- Best for: Enterprise, compliance (HIPAA, SOC2)

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#azure-openai)

---

## Comparison Table

| Provider | Speed | Cost | Quality | Privacy | Setup | Models |
|----------|-------|------|---------|---------|-------|--------|
| **OpenAI** | Very Fast | $$ | Excellent | Low | 5 min | Many |
| **Anthropic** | Fast | $$ | Excellent | Low | 5 min | Few |
| **Google** | Very Fast | $$ | Good | Low | 5 min | Few |
| **Groq** | Ultra Fast | $ | Good | Low | 5 min | Few |
| **OpenRouter** | Varies | Varies | Varies | Low | 5 min | 100+ |
| **Ollama** | Slow-Medium | Free | Good | Max | 10 min | Many |
| **LM Studio** | Slow-Medium | Free | Good | Max | 15 min | Many |
| **Azure** | Very Fast | $$ | Excellent | High | 10 min | Many |

---

## Choosing Your Provider

### I want the easiest setup
→ **OpenAI** — Most popular, best community support

### I have unlimited budget
→ **OpenAI** — Best quality

### I want to save money
→ **Groq** — Cheapest cloud ($0.05 per 1M tokens)

### I want privacy/offline
→ **Ollama** — Free, local, private

### I want a GUI (not CLI)
→ **LM Studio** — Desktop app

### I'm in an enterprise
→ **Azure OpenAI** — Compliance, support

### I need long context (200K+ tokens)
→ **Anthropic** — Best long-context model

### I need multimodal (images, audio, video)
→ **Google Gemini** — Best multimodal support

### I want access to many models with one API key
→ **OpenRouter** — 100+ models, unified billing

---

## Setup Paths

### Path 1: OpenAI (Most Common)

```
1. Go to https://platform.openai.com/api-keys
2. Create account, add $5+ credit
3. Create API key
4. Add to .env: OPENAI_API_KEY=sk-...
5. Restart services
6. Done!
```

**Time:** 5 minutes
**Cost:** Pay as you go (~$1-5/month light use)

### Path 2: Local Ollama (Privacy)

```
1. Download Ollama: https://ollama.ai
2. Run: ollama serve
3. Download model: ollama pull mistral
4. Add to .env: OLLAMA_API_BASE=http://localhost:11434
5. Restart services
6. Done!
```

**Time:** 10 minutes
**Cost:** Free (electricity only)
**Requirement:** 8GB RAM minimum (16GB+ recommended)

### Path 3: Anthropic (Better Reasoning)

```
1. Go to https://console.anthropic.com/
2. Create account, add payment method
3. Create API key
4. Add to .env: ANTHROPIC_API_KEY=sk-ant-...
5. Restart services
6. Done!
```

**Time:** 5 minutes
**Cost:** Pay as you go (~$2-20/month typical use)

### Path 4: OpenRouter (100+ Models)

```
1. Go to https://openrouter.ai/keys
2. Create account, add credit
3. Create API key
4. Add to .env: OPENROUTER_API_KEY=sk-or-...
5. Restart services
6. Done!
```

**Time:** 5 minutes
**Cost:** Varies by model ($0.05-15 per 1M tokens)

---

## Model Recommendations by Task

### General Chat
- OpenAI: `gpt-4o` (best) or `gpt-4o-mini` (cheap)
- Anthropic: `claude-3-5-sonnet` (best)
- Google: `gemini-2.0-flash` (balanced)
- Groq: `mixtral-8x7b-32768` (fast)
- Ollama: `mistral` (balanced)

### Long Documents (200K+ tokens)
- Anthropic: `claude-3-5-sonnet` (200K context)
- Google: `gemini-1.5-pro` (1M context)
- OpenAI: `gpt-4-turbo` (128K context)

### Fast/Cheap Operations
- Groq: Ultra-fast, very cheap
- OpenAI: `gpt-4o-mini` (fast, cheap)
- Anthropic: `claude-3-5-haiku` (cheap)

### Multimodal (Images/Audio/Video)
- Google: `gemini-2.0-flash` (best multimodal)
- OpenAI: `gpt-4o` (good multimodal)

### Local/Offline
- Ollama: `mistral` (best local balance)
- LM Studio: `mistral` or `llama2`

---

## Complete Configuration Reference

For detailed environment variable setup, see:
→ [Complete Configuration Reference](../5-CONFIGURATION/environment-reference.md)

For detailed AI provider configuration, see:
→ [AI Providers Configuration](../5-CONFIGURATION/ai-providers.md)

---

## Testing Your Setup

Once configured:

```
1. Start Open Notebook
2. Go to Settings → Models
3. Select your configured provider
4. Try a Chat question
5. If it responds, you're good!
```

---

## Cost Estimator

### OpenAI
```
Light use (10 chats/day): $1-5/month
Medium use (50 chats/day): $10-30/month
Heavy use (all-day use): $50-100+/month
```

### Anthropic
```
Light use: $1-3/month
Medium use: $5-20/month
Heavy use: $20-50+/month
```

### Groq
```
Light use: $0-1/month
Medium use: $2-5/month
Heavy use: $5-20/month
```

### Ollama
```
Any use: Free (electricity only)
8GB GPU running 24/7: ~$10/month electricity
```

---

## Switching Providers

You can switch providers anytime:

```
1. Edit .env
2. Change/add API key
3. Restart services
4. Go to Settings → Models
5. Select new provider
6. Done!
```

Your existing notebooks and data stay the same.

---

## Provider-Specific Guides

For detailed setup instructions per provider, see:
→ [5-CONFIGURATION/ai-providers.md](../5-CONFIGURATION/ai-providers.md)

Includes:
- OpenAI
- Anthropic
- Google Gemini
- Groq
- OpenRouter
- Mistral
- DeepSeek
- xAI
- Ollama
- LM Studio
- OpenAI-Compatible
- Azure OpenAI

---

## Troubleshooting

**"Models not showing in Settings"**
- API key missing or wrong
- Restart services after changing .env
- Check the key is set correctly: `echo $OPENAI_API_KEY`

**"API key invalid"**
- Copy fresh key from provider's dashboard
- Check no extra spaces: `OPENAI_API_KEY="sk-..."`
- Verify key format matches provider

**"Rate limit exceeded"**
- You're hitting provider's rate limits
- Wait a bit, retry
- For cloud: upgrade account or reduce request rate

**"Connection refused" (Ollama)**
- Ollama not running: `ollama serve`
- Wrong port: Check `OLLAMA_API_BASE`
- Not on localhost: Use IP instead

---

## Next Steps

1. **Pick a provider** from above
2. **Follow setup guide** in [5-CONFIGURATION/ai-providers.md](../5-CONFIGURATION/ai-providers.md)
3. **Add API key** to .env
4. **Restart services**
5. **Test in Settings → Models**
6. **Start using!**

---

## Support

- **Provider issues?** Check their documentation
- **Setup problems?** See [6-TROUBLESHOOTING](../6-TROUBLESHOOTING/index.md)
- **Need help?** Join [Discord community](https://discord.gg/37XJPXfz2w)
