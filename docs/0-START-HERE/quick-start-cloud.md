# Quick Start - Cloud AI Providers (5 minutes)

Get Open Notebook running with **Anthropic, Google, Groq, or other cloud providers**. Same simplicity as OpenAI, with more choices.

## Prerequisites

1. **Docker Desktop** installed
   - [Download here](https://www.docker.com/products/docker-desktop/)
   - Already have it? Skip to step 2

2. **API Key** from your chosen provider:
   - **OpenRouter** (100+ models, one key): https://openrouter.ai/keys
   - **Anthropic (Claude)**: https://console.anthropic.com/
   - **Google (Gemini)**: https://aistudio.google.com/
   - **Groq** (fast, free tier): https://console.groq.com/
   - **Mistral**: https://console.mistral.ai/
   - **DeepSeek**: https://platform.deepseek.com/
   - **xAI (Grok)**: https://console.x.ai/

## Step 1: Create Configuration (1 min)

Create a new folder `open-notebook` and add this file:

**docker-compose.yml**:
```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:v2
    command: start --user root --pass password --bind 0.0.0.0:8000 rocksdb:/mydata/mydatabase.db
    ports:
      - "8000:8000"
    volumes:
      - ./surreal_data:/mydata

  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    pull_policy: always
    ports:
      - "8502:8502"  # Web UI
      - "5055:5055"  # API
    environment:
      # Choose ONE provider (uncomment your choice):

      # OpenRouter - 100+ models with one API key
      - OPENROUTER_API_KEY=sk-or-...

      # Anthropic (Claude) - Excellent reasoning
      # - ANTHROPIC_API_KEY=sk-ant-...

      # Google (Gemini) - Large context, cost-effective
      # - GOOGLE_API_KEY=...

      # Groq - Ultra-fast inference, free tier available
      # - GROQ_API_KEY=gsk_...

      # Mistral - European provider, good quality
      # - MISTRAL_API_KEY=...

      # Database (required)
      - SURREAL_URL=ws://surrealdb:8000/rpc
      - SURREAL_USER=root
      - SURREAL_PASSWORD=password
      - SURREAL_NAMESPACE=open_notebook
      - SURREAL_DATABASE=open_notebook
    volumes:
      - ./notebook_data:/app/data
    depends_on:
      - surrealdb
    restart: always

```

**Edit the file:**
- Uncomment ONE provider and add your API key
- Comment out or remove the others

---

## Step 2: Start Services (1 min)

Open terminal in your `open-notebook` folder:

```bash
docker compose up -d
```

Wait 15-20 seconds for services to start.

---

## Step 3: Access Open Notebook (instant)

Open your browser:
```
http://localhost:8502
```

You should see the Open Notebook interface!

---

## Step 4: Configure Your Model (1 min)

1. Go to **Settings** (gear icon)
2. Navigate to **Models**
3. Select your provider's model:

| Provider | Recommended Model | Notes |
|----------|-------------------|-------|
| **OpenRouter** | `anthropic/claude-3.5-sonnet` | Access 100+ models |
| **Anthropic** | `claude-3-5-sonnet-latest` | Best reasoning |
| **Google** | `gemini-2.0-flash` | Large context, fast |
| **Groq** | `llama-3.3-70b-versatile` | Ultra-fast |
| **Mistral** | `mistral-large-latest` | Strong European option |

4. Click **Save**

---

## Step 5: Create Your First Notebook (1 min)

1. Click **New Notebook**
2. Name: "My Research"
3. Click **Create**

---

## Step 6: Add Content & Chat (2 min)

1. Click **Add Source**
2. Choose **Web Link**
3. Paste any article URL
4. Wait for processing
5. Go to **Chat** and ask questions!

---

## Verification Checklist

- [ ] Docker is running
- [ ] You can access `http://localhost:8502`
- [ ] Models are configured for your provider
- [ ] You created a notebook
- [ ] Chat works

**All checked?** You're ready to research!

---

## Provider Comparison

| Provider | Speed | Quality | Context | Cost |
|----------|-------|---------|---------|------|
| **OpenRouter** | Varies | Varies | Varies | Varies (100+ models) |
| **Anthropic** | Medium | Excellent | 200K | $$$ |
| **Google** | Fast | Very Good | 1M+ | $$ |
| **Groq** | Ultra-fast | Good | 128K | $ (free tier) |
| **Mistral** | Fast | Good | 128K | $$ |
| **DeepSeek** | Medium | Very Good | 64K | $ |

---

## Using Multiple Providers

You can enable multiple providers simultaneously:

```yaml
environment:
  - OPENROUTER_API_KEY=sk-or-...
  - ANTHROPIC_API_KEY=sk-ant-...
  - GOOGLE_API_KEY=...
  - GROQ_API_KEY=gsk_...
```

Then switch between them in **Settings** > **Models** as needed.

---

## Troubleshooting

### "Model not found" Error

1. Verify your API key is correct (no extra spaces)
2. Check you have credits/access for the model
3. Restart: `docker compose restart api`

### "Cannot connect to server"

```bash
docker ps  # Check all services running
docker compose logs  # View logs
docker compose restart  # Restart everything
```

### Provider-Specific Issues

**Anthropic**: Ensure key starts with `sk-ant-`
**Google**: Use AI Studio key, not Cloud Console
**Groq**: Free tier has rate limits; upgrade if needed

---

## Cost Estimates

Approximate costs per 1K tokens:

| Provider | Input | Output |
|----------|-------|--------|
| Anthropic (Sonnet) | $0.003 | $0.015 |
| Google (Flash) | $0.0001 | $0.0004 |
| Groq (Llama 70B) | Free tier available | - |
| Mistral (Large) | $0.002 | $0.006 |

Check provider websites for current pricing.

---

## Next Steps

1. **Add Your Content**: PDFs, web links, documents
2. **Explore Features**: Podcasts, transformations, search
3. **Full Documentation**: [See all features](../3-USER-GUIDE/index.md)

---

**Need help?** Join our [Discord community](https://discord.gg/37XJPXfz2w)!
