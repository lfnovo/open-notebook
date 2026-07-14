# Quick Start - External Ollama

Run Open Notebook with a **separately installed Ollama** (not via Docker). This avoids Docker running the Ollama service while you use your own local Ollama installation.

## Prerequisites

1. **Docker Desktop** installed (for SurrealDB and Open Notebook)
   - [Download here](https://www.docker.com/products/docker-desktop/)

2. **Ollama** installed separately
   - [Download here](https://ollama.ai/)
   - Verify: run `ollama --version`

3. **Models downloaded** in Ollama:
   ```bash
   ollama pull mistral
   ollama pull nomic-embed-text
   ```

---

## Step 1: Start Ollama (1 min)

Start the Ollama server:

```bash
# Default: runs on http://localhost:11434
ollama serve
```

Keep this terminal open. Ollama will run in the background.

**Optional: Start Ollama on a custom port or network interface:**
```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

---

## Step 2: Create Configuration (1 min)

Create a new folder `open-notebook-external-ollama` and add these files:

**docker-compose.yml**:
```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:v2
    command: start --user root --pass password rocksdb:/mydata/mydatabase.db
    user: root
    ports:
      # Localhost only — the database uses default credentials, so never
      # publish this port on 0.0.0.0
      - "127.0.0.1:8000:8000"
    volumes:
      - ./surreal_data:/mydata

  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    pull_policy: always
    ports:
      - "8502:8502"  # Web UI (React frontend)
      - "5055:5055"  # API (required!)
    environment:
      # Encryption key for credential storage (required)
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=change-me-to-a-secret-string

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

**Note:** No Ollama service in Docker — we use the host's Ollama.

---

## Step 3: Connect Open Notebook to Host Ollama (1 min)

When Open Notebook runs inside Docker, it cannot reach `localhost:11434` on your host directly. Use the special hostname:

| Host OS | Ollama URL in Open Notebook |
|---------|----------------------------|
| Linux | `http://host.containers.internal:11434` |
| macOS | `http://host.docker.internal:11434` |
| Windows | `http://host.docker.internal:11434` |

---

## Step 4: Start Open Notebook (1 min)

Open terminal in your `open-notebook-external-ollama` folder:

```bash
docker compose up -d
```

Wait 10-15 seconds for services to start.

---

## Step 5: Configure Ollama Provider (1 min)

1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select provider: **Ollama**
4. Give it a name (e.g., "Local Ollama")
5. Enter the base URL:
   - **Windows/macOS:** `http://host.docker.internal:11434`
   - **Linux:** `http://host.containers.internal:11434`
6. Click **Save**
7. Click **Test Connection** — should show success
8. Click **Discover Models** → **Register Models**

---

## Step 6: Configure Models (1 min)

1. Go to **Settings** → **Models**
2. Set:
   - **Language Model**: `ollama/mistral` (or whichever model you downloaded)
   - **Embedding Model**: `ollama/nomic-embed-text`
3. Click **Save**

---

## Step 7: Access Open Notebook (instant)

Open your browser:
```
http://localhost:8502
```

---

## Verification Checklist

- [ ] Ollama is running (`ollama serve` in terminal)
- [ ] Docker is running
- [ ] You can access `http://localhost:8502`
- [ ] Ollama credential is configured with host URL and tested
- [ ] Models are registered
- [ ] Chat works

---

## Troubleshooting

### "Connection failed" when testing Ollama credential

1. Verify Ollama is running:
   ```bash
   curl http://localhost:11434/api/version
   ```

2. Check firewall allows local connections on port 11434

3. For Windows/macOS, ensure `host.docker.internal` is reachable from inside the container:
   ```bash
   docker exec <open_notebook_container> curl http://host.docker.internal:11434/api/version
   ```

### Ollama not starting

```bash
# Check Ollama logs
ollama list

# Pull a model again
ollama pull mistral
```

### "Address already in use" for SurrealDB

```bash
docker compose down
docker compose up -d
```

---

## Why External Ollama?

| Approach | Ollama in Docker | Ollama External |
|----------|-----------------|-----------------|
| **Resource isolation** | Separated | Shares with host |
| **GPU access** | Requires Docker GPU setup | Native GPU access |
| **Model management** | Via `docker exec` | Via terminal directly |
| **Memory usage** | Isolated from host | Shared with host apps |

**External Ollama** is recommended if you:
- Already have Ollama installed and configured
- Want GPU access without Docker GPU passthrough complexity
- Prefer managing models via command line directly

---

## Going Further

- **Add more models**: Run `ollama pull <model>`, then re-discover from Open Notebook
- **Check Ollama status**: `ollama list` shows downloaded models
- **Customize Ollama**: Edit `~/.ollama/config.yaml` for advanced settings

---

**Need Help?** Join our [Discord community](https://discord.gg/37XJPXfz2w)
