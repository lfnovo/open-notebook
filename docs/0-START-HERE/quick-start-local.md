# Quick Start - Local & Private (5 minutes)

Get Open Notebook running with **100% local AI** using Ollama. No cloud API keys needed, completely private.

## Prerequisites

1. **Docker Desktop** installed
   - [Download here](https://www.docker.com/products/docker-desktop/)
   - Already have it? Skip to step 2

2. **Local LLM** - Choose one:
   - **Ollama** (recommended): [Download here](https://ollama.ai/)
   - **LM Studio** (GUI alternative): [Download here](https://lmstudio.ai)

## Step 1: Choose Your Setup (1 min)

### 🏠 Local Machine (Same Computer)
Everything runs on your machine. Recommended for testing/learning.

### 🌐 Remote Server (Raspberry Pi, NAS, Cloud VM)
Run on a different computer, access from another. Needs network configuration.

---

## Step 2: Create Configuration (1 min)

Create a new folder `open-notebook-local` and add this file:

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
    image: lfnovo/open_notebook:v1-latest-single
    pull_policy: always
    ports:
      - "8502:8502"  # Web UI (React frontend)
      - "5055:5055"  # API (required!)
    environment:
      # NO API KEYS NEEDED - Using Ollama (free, local)
      - OLLAMA_API_BASE=http://ollama:11434

      # Database (required)
      - SURREAL_URL=ws://surrealdb:8000/rpc
      - SURREAL_USER=root
      - SURREAL_PASSWORD=password
      - SURREAL_NAMESPACE=open_notebook
      - SURREAL_DATABASE=open_notebook
    volumes:
      - ./notebook_data:/app/data
      - ./surreal_data:/mydata
    depends_on:
      - surrealdb
    restart: always

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ./ollama_models:/root/.ollama
    environment:
      # Optional: set GPU support if available
      - OLLAMA_NUM_GPU=0
    restart: always

```

**That's it!** No API keys, no secrets, completely private.

---

## Step 3: Start Services (1 min)

Open terminal in your `open-notebook-local` folder:

```bash
docker compose up -d
```

Wait 10-15 seconds for all services to start.

---

## Step 4: Download a Model (2-3 min)

Ollama needs at least one language model. Pick one:

```bash
# Fastest & smallest (recommended for testing)
docker exec open_notebook-ollama-1 ollama pull mistral

# OR: Better quality but slower
docker exec open_notebook-ollama-1 ollama pull neural-chat

# OR: Even better quality, more VRAM needed
docker exec open_notebook-ollama-1 ollama pull llama2
```

This downloads the model (will take 1-5 minutes depending on your internet).

---

## Step 5: Access Open Notebook (instant)

Open your browser:
```
http://localhost:8502
```

You should see the Open Notebook interface.

---

## Step 6: Configure Local Model (1 min)

1. Click **Settings** (top right) → **Models**
2. Set:
   - **Language Model**: `ollama/mistral` (or whichever model you downloaded)
   - **Embedding Model**: `ollama/nomic-embed-text` (auto-downloads if missing)
3. Click **Save**

---

## Step 7: Create Your First Notebook (1 min)

1. Click **New Notebook**
2. Name: "My Private Research"
3. Click **Create**

---

## Step 8: Add Local Content (1 min)

1. Click **Add Source**
2. Choose **Text**
3. Paste some text or a local document
4. Click **Add**

---

## Step 9: Chat With Your Content (1 min)

1. Go to **Chat**
2. Type: "What did you learn from this?"
3. Click **Send**
4. Watch as the local Ollama model responds!

---

## Verification Checklist

- [ ] Docker is running
- [ ] You can access `http://localhost:8502`
- [ ] Models are configured
- [ ] You created a notebook
- [ ] Chat works with local model

**All checked?** 🎉 You have a completely **private, offline** research assistant!

---

## Advantages of Local Setup

✅ **No API costs** - Free forever
✅ **No internet required** - True offline capability
✅ **Privacy first** - Your data never leaves your machine
✅ **No subscriptions** - No monthly bills

**Trade-off:** Slower than cloud models (depends on your CPU/GPU)

---

## Troubleshooting

### "ollama: command not found"

Docker image name might be different:
```bash
docker ps  # Find the Ollama container name
docker exec <container_name> ollama pull mistral
```

### Model Download Stuck

Check internet connection and restart:
```bash
docker compose restart ollama
```

Then retry the model pull command.

### "Address already in use" Error

```bash
docker compose down
docker compose up -d
```

### Low Performance

Check if GPU is available:
```bash
# Show available GPUs
docker exec open_notebook-ollama-1 ollama ps

# Enable GPU in docker-compose.yml:
# - OLLAMA_NUM_GPU=1
```

Then restart: `docker compose restart ollama`

### Adding More Models

```bash
# List available models
docker exec open_notebook-ollama-1 ollama list

# Pull additional model
docker exec open_notebook-ollama-1 ollama pull neural-chat
```

---

## Next Steps

**Now that it's running:**

1. **Add Your Own Content**: PDFs, documents, articles (see 3-USER-GUIDE)
2. **Explore Features**: Podcasts, transformations, search
3. **Full Documentation**: [See all features](../3-USER-GUIDE/index.md)
4. **Scale Up**: Deploy to a server with better hardware for faster responses
5. **Benchmark Models**: Try different models to find the speed/quality tradeoff you prefer

---

## Alternative: Using LM Studio Instead of Ollama

**Prefer a GUI?** LM Studio is easier for non-technical users:

1. Download LM Studio: https://lmstudio.ai
2. Open the app, download a model from the library
3. Go to "Local Server" tab, start server (port 1234)
4. Update your docker-compose.yml:
   ```yaml
   environment:
     - OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:1234/v1
     - OPENAI_COMPATIBLE_API_KEY=not-needed
   ```
5. Configure in Settings → Models → Select your LM Studio model

**Note**: LM Studio runs outside Docker, use `host.docker.internal` to connect.

---

## Going Further

- **Switch models**: Change in Settings → Models anytime
- **Add more models**:
  - Ollama: Run `ollama pull <model>`
  - LM Studio: Download from the app library
- **Deploy to server**: Same docker-compose.yml works anywhere
- **Use cloud hybrid**: Keep some local models, add OpenAI/Anthropic for complex tasks

---

## Common Model Choices

| Model | Speed | Quality | VRAM | Best For |
|-------|-------|---------|------|----------|
| **mistral** | Fast | Good | 4GB | Testing, general use |
| **neural-chat** | Medium | Better | 6GB | Balanced, recommended |
| **llama2** | Slow | Best | 8GB+ | Complex reasoning |
| **phi** | Very Fast | Fair | 2GB | Minimal hardware |

---

**Need Help?** Join our [Discord community](https://discord.gg/37XJPXfz2w) - many users run local setups!
