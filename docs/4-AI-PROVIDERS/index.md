# AI Providers - Comparison & Selection Guide

Open Notebook supports 17+ AI providers. This guide helps you **choose the right provider** for your needs.

> 💡 **Just want to set up a provider?** Skip to the [Configuration Guide](../5-CONFIGURATION/ai-providers.md) for detailed setup instructions.

---

## Quick Decision: Which Provider?

### Cloud Providers (Easiest)

**OpenAI (Recommended)**
- Cost: ~$0.03-0.15 per 1K tokens
- Speed: Very fast
- Quality: Excellent
- Best for: Most users (best quality/price balance)

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#openai)

**Anthropic (Claude)**
- Cost: ~$0.80-3.00 per 1M tokens
- Speed: Fast
- Quality: Excellent
- Best for: Long context (200K tokens), reasoning, latest AI
- Advantage: Superior long-context handling

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#anthropic-claude)

**Google Gemini**
- Cost: ~$0.075-0.30 per 1K tokens
- Speed: Very fast
- Quality: Good to excellent
- Best for: Multimodal (images, audio, video)
- Advantage: Longest context (up to 2M tokens)

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#google-gemini)

**Groq (Ultra-Fast)**
- Cost: ~$0.05 per 1M tokens (cheapest)
- Speed: Ultra-fast (fastest available)
- Quality: Good
- Best for: Budget-conscious, transformations, speed-critical tasks
- Disadvantage: Limited model selection

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#groq)

**OpenRouter (100+ Models)**
- Cost: Pay-per-model (varies widely)
- Speed: Varies by model
- Quality: Varies by model
- Best for: Model comparison, testing, unified billing
- Advantage: One API key for 100+ models from different providers

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#openrouter)

**DashScope (Qwen)**
- Cost: ~$0.01-0.06 per 1K tokens
- Speed: Fast
- Quality: Good
- Best for: Users in Asia, Alibaba Cloud ecosystem
- Advantage: Competitive pricing, strong multilingual support

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#dashscope-qwen)

**MiniMax**
- Cost: Varies by model
- Speed: Fast
- Quality: Good
- Best for: Long context tasks (204K tokens)
- Advantage: Very long context window

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#minimax)

### Local / Self-Hosted (Free)

**Ollama (Recommended for Local)**
- Cost: Free (electricity only)
- Speed: Depends on hardware (slow on CPU, fast on GPU)
- Quality: Good (open-source models)
- Setup: 10 minutes
- Best for: Privacy-first, offline use
- Privacy: 100% local, nothing leaves your machine

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#ollama-recommended-for-local)

**LM Studio (Alternative)**
- Cost: Free (electricity only)
- Speed: Depends on hardware
- Quality: Good (same models as Ollama)
- Setup: 15 minutes (GUI interface)
- Best for: Non-technical users who prefer GUI over CLI
- Privacy: 100% local

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#lm-studio-local-alternative)

### Enterprise

**Azure OpenAI**
- Cost: Same as OpenAI (usage-based)
- Speed: Very fast
- Quality: Excellent (same models as OpenAI)
- Setup: 10 minutes (more complex)
- Best for: Enterprise, compliance (HIPAA, SOC2), VPC integration

→ [Setup Guide](../5-CONFIGURATION/ai-providers.md#azure-openai)

---

## Comparison Table

| Provider | Speed | Cost | Quality | Privacy | Setup | Context |
|----------|-------|------|---------|---------|-------|---------|
| **OpenAI** | Very Fast | $$ | Excellent | Low | 5 min | 128K |
| **Anthropic** | Fast | $$ | Excellent | Low | 5 min | 200K |
| **Google** | Very Fast | $$ | Good-Excellent | Low | 5 min | 2M |
| **Groq** | Ultra Fast | $ | Good | Low | 5 min | 32K |
| **OpenRouter** | Varies | Varies | Varies | Low | 5 min | Varies |
| **DashScope** | Fast | $ | Good | Low | 5 min | Varies |
| **MiniMax** | Fast | $$ | Good | Low | 5 min | 204K |
| **Ollama** | Slow-Medium | Free | Good | Max | 10 min | Varies |
| **LM Studio** | Slow-Medium | Free | Good | Max | 15 min | Varies |
| **Azure** | Very Fast | $$ | Excellent | High | 10 min | 128K |

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

## Ready to Set Up Your Provider?

Now that you've chosen a provider, follow the detailed setup instructions:

→ **[AI Providers Configuration Guide](../5-CONFIGURATION/ai-providers.md)**

This guide includes:
- Step-by-step setup instructions for each provider via the Settings UI
- How to add credentials, test connections, and discover models
- Model selection and recommendations
- Provider-specific troubleshooting
- Hardware requirements (for local providers)
- Cost optimization tips

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

## Next Steps

1. **You've chosen a provider** (from this comparison guide)
2. **Follow the setup guide**: [AI Providers Configuration](../5-CONFIGURATION/ai-providers.md)
3. **Add your credential** in Settings → API Keys
4. **Test your connection** and discover models
5. **Start using Open Notebook!**

---

## Need Help?

- **Setup issues?** See [AI Providers Configuration](../5-CONFIGURATION/ai-providers.md) for detailed troubleshooting per provider
- **General problems?** Check [Troubleshooting Guide](../6-TROUBLESHOOTING/index.md)
- **Questions?** Join [Discord community](https://discord.gg/37XJPXfz2w)
