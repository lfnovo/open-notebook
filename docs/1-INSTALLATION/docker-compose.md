# Docker Compose Installation (Recommended)

Multi-container setup with separate services. **Best for most users.**

> **Alternative Registry:** All images are available on both Docker Hub (`lfnovo/open_notebook`) and GitHub Container Registry (`ghcr.io/lfnovo/open-notebook`). Use GHCR if Docker Hub is blocked or you prefer GitHub-native workflows.

## Prerequisites

- **Docker Desktop** installed ([Download](https://www.docker.com/products/docker-desktop/))
- **5-10 minutes** of your time
- **API key** for at least one AI provider (OpenAI recommended for beginners)

## Step 1: Create Configuration (2 min)

Create a folder `open-notebook` and add this file:

**docker-compose.yml**:
```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:v2
    command: start --user root --pass password --bind 0.0.0.0:8000 rocksdb:/mydata/mydatabase.db
    user: root  # Required for bind mounts on Linux (SurrealDB runs as non-root by default)
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
      # Encryption key for credential storage (required)
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=change-me-to-a-secret-string

      # Database
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
- Replace `change-me-to-a-secret-string` with your own secret (any string works)

---

## Step 2: Start Services (2 min)

Open terminal in the `open-notebook` folder:

```bash
docker compose up -d
```

Wait 15-20 seconds for all services to start:
```
✅ surrealdb running on :8000
✅ open_notebook running on :8502 (UI) and :5055 (API)
```

Check status:
```bash
docker compose ps
```

---

## Step 3: Verify Installation (1 min)

**API Health:**
```bash
curl http://localhost:5055/health
# Should return: {"status": "healthy"}
```

**Frontend Access:**
Open browser to:
```
http://localhost:8502
```

You should see the Open Notebook interface!

---

## Step 4: Configure AI Provider (2 min)

1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select your provider (e.g., OpenAI, Anthropic, Google)
4. Give it a name, paste your API key
5. Click **Save**
6. Click **Test Connection** — should show success
7. Click **Discover Models** → **Register Models**

Your models are now available!

> **Need an API key?** Get one from your chosen provider:
> - **OpenAI**: https://platform.openai.com/api-keys
> - **Anthropic**: https://console.anthropic.com/
> - **Google**: https://aistudio.google.com/
> - **Groq**: https://console.groq.com/

---

## Step 5: First Notebook (2 min)

1. Click **New Notebook**
2. Name: "My Research"
3. Description: "Getting started"
4. Click **Create**

Done! You now have a fully working Open Notebook instance.

---

## Configuration

### Adding Ollama (Free Local Models)

Add to `docker-compose.yml`:

```yaml
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    restart: always

volumes:
  surreal_data:
  ollama_models:
```

Restart and pull a model:
```bash
docker compose restart
docker exec open_notebook-ollama-1 ollama pull mistral
```

Then configure Ollama in the Settings UI:
1. Go to **Settings** → **API Keys**
2. Click **Add Credential** → Select **Ollama**
3. Enter base URL: `http://ollama:11434`
4. Click **Save**, then **Test Connection**
5. Click **Discover Models** → **Register Models**

---

## Environment Variables Reference

| Variable | Purpose | Example |
|----------|---------|---------|
| `OPEN_NOTEBOOK_ENCRYPTION_KEY` | Encryption key for credentials | `my-secret-key` |
| `SURREAL_URL` | Database connection | `ws://surrealdb:8000/rpc` |
| `SURREAL_USER` | Database user | `root` |
| `SURREAL_PASSWORD` | Database password | `password` |
| `API_URL` | API external URL | `http://localhost:5055` |

See [Environment Reference](../5-CONFIGURATION/environment-reference.md) for complete list.

---

## Common Tasks

### Stop Services
```bash
docker compose down
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
```

### Restart Services
```bash
docker compose restart
```

### Update to Latest Version
```bash
docker compose down
docker compose pull
docker compose up -d
```

### Remove All Data
```bash
docker compose down -v
```

---

## Troubleshooting

### "Cannot connect to API" Error

1. Check if Docker is running:
```bash
docker ps
```

2. Check if services are running:
```bash
docker compose ps
```

3. Check API logs:
```bash
docker compose logs api
```

4. Wait longer - services can take 20-30 seconds to start on first run

---

### Port Already in Use

If you get "Port 8502 already in use", change the port:

```yaml
ports:
  - "8503:8502"  # Use 8503 instead
  - "5055:5055"  # Keep API port same
```

Then access at `http://localhost:8503`

---

### Credential Issues

1. Go to **Settings** → **API Keys**
2. Click **Test Connection** on the credential
3. If it fails, verify key at provider's website
4. Check you have credits in your account
5. Delete and re-create the credential if needed

---

### Database Connection Issues

Check SurrealDB is running:
```bash
docker compose logs surrealdb
```

Reset database:
```bash
docker compose down -v
docker compose up -d
```

### Database Permission Denied (Linux)

If you see `Permission denied` or `Failed to create RocksDB directory` in SurrealDB logs:

```bash
docker compose logs surrealdb | grep -i permission
```

This happens because SurrealDB runs as a non-root user but Docker creates bind mount directories as root. Add `user: root` to the surrealdb service:

```yaml
surrealdb:
  image: surrealdb/surrealdb:v2
  user: root  # Fix for Linux bind mount permissions
  # ... rest of config
```

Then restart:
```bash
docker compose down -v
docker compose up -d
```

---

## Next Steps

1. **Add Content**: Sources, notebooks, documents
2. **Configure Models**: Settings → Models (choose your preferences)
3. **Explore Features**: Chat, search, transformations
4. **Read Guide**: [User Guide](../3-USER-GUIDE/index.md)

---

## Production Deployment

For production use, see:
- [Security Hardening](../5-CONFIGURATION/security.md)
- [Reverse Proxy](../5-CONFIGURATION/reverse-proxy.md)

---

## Getting Help

- **Discord**: [Community support](https://discord.gg/37XJPXfz2w)
- **Issues**: [GitHub Issues](https://github.com/lfnovo/open-notebook/issues)
- **Docs**: [Full documentation](../index.md)
