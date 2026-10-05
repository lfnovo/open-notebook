# Configuration

Open Notebook is configured in two places:

1. **Environment variables** for infrastructure: the encryption key, the database connection, the API URL, timeouts. The complete list is the [Environment Reference](environment-reference.md).
2. **The web UI** for everything else: AI provider credentials and models in **Manage → Models**, content processing engines in **Settings**.

---

## Where environment variables go

### Docker Compose

Put them under the `open_notebook` service's `environment:` block in `docker-compose.yml`, then run:

```bash
docker compose up -d
```

`docker compose restart` keeps the old environment, so it does not apply changes.

```yaml
services:
  open_notebook:
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=a-long-random-string
      - API_URL=https://notebook.example.com
```

The shipped `docker-compose.yml` doesn't load an env file into the container. A `.env` file next to it only fills the `${...}` placeholders in the compose file (`SURREAL_USER`, `SURREAL_PASSWORD`), so a variable that exists only in `.env` never reaches Open Notebook. To keep settings in a file, add `env_file: .env` to the `open_notebook` service.

### From source

Put them in `.env` in the project root (start from `.env.example`) and restart the API and the worker. The exception is `OPEN_NOTEBOOK_WORKER_MAX_TASKS`, which `make worker-start` reads from your shell: `export` it first.

---

## The settings that matter

### Encryption key (required)

```yaml
- OPEN_NOTEBOOK_ENCRYPTION_KEY=a-long-random-string
```

Encrypts the provider API keys you save in Manage → Models. Without it you can't save credentials. Replace the `change-me-to-a-secret-string` placeholder from the shipped file, and don't change the value later: credentials saved with the old key become unreadable. See [Security](security.md#api-key-encryption).

### Database

```yaml
- SURREAL_URL=ws://surrealdb:8000/rpc
- SURREAL_USER=root
- SURREAL_PASSWORD=root
- SURREAL_NAMESPACE=open_notebook
- SURREAL_DATABASE=open_notebook
```

The shipped compose file already sets these. The hostname in `SURREAL_URL` depends on where SurrealDB runs; see [Database](database.md). Change the user and password before exposing the instance (set `SURREAL_USER`/`SURREAL_PASSWORD` in `.env`; the compose file applies them to both services).

### AI providers (in the UI)

1. Open **Manage → Models**.
2. In your provider's section, click **Add Configuration**, enter the API key (and Base URL if needed), and save.
3. Click **Test** on the new configuration to check the connection.
4. Click **Models** to open **Discover Models**, pick a model type, select models and click **Add Selected**.
5. Under **Default Model Assignments**, choose the models for chat, embeddings and so on, or click **Auto-assign Defaults**.

Details for each provider: [AI Providers](ai-providers.md). Local options: [Ollama](ollama.md), [oMLX](omlx.md), [OpenAI-Compatible](openai-compatible.md) (LM Studio, vLLM, llama.cpp…), [Local speech with Speaches](local-tts.md).

### API URL (usually not needed)

The browser finds the API automatically at `<the host you opened>:5055`. Set `API_URL` only when that's wrong: behind a reverse proxy (`API_URL=https://notebook.example.com`) or when the API is published on another port. See [Reverse Proxy](reverse-proxy.md#how-the-browser-finds-the-api).

### Password

Set `OPEN_NOTEBOOK_PASSWORD` for anything reachable beyond your own machine. Without it, authentication is off. See [Security](security.md).

---

## Configuration pages

| Page | Covers |
|------|--------|
| [Environment Reference](environment-reference.md) | Every environment variable: default, which process reads it, what it does |
| [AI Providers](ai-providers.md) | Supported providers, what each one offers, setup notes |
| [Ollama](ollama.md) | Local models with Ollama: networking, context window, timeouts |
| [oMLX](omlx.md) | Apple Silicon MLX server |
| [OpenAI-Compatible](openai-compatible.md) | LM Studio, vLLM, llama.cpp and other OpenAI-style servers |
| [Local speech (Speaches)](local-tts.md) | Local text-to-speech and speech-to-text |
| [Local speech-to-text](local-stt.md) | Whisper model choice and long audio |
| [Database](database.md) | SurrealDB connection settings |
| [Security](security.md) | Password, credential encryption, CORS, hardening |
| [Reverse Proxy](reverse-proxy.md) | nginx, Caddy, Traefik, custom domains, HTTPS |
| [Advanced](advanced.md) | Concurrency, timeouts, ports, logging, backups |
| [MCP Integration](mcp-integration.md) | Using Open Notebook from MCP clients |

---

## Common mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Variable added to `.env` only (Docker) | Setting has no effect | Put it under `open_notebook` → `environment:` |
| `docker compose restart` after editing | Old values still used | `docker compose up -d` |
| No encryption key | "Encryption key not configured" on the Models page | Set `OPEN_NOTEBOOK_ENCRYPTION_KEY` |
| Encryption key changed | "Decryption Error" on saved credentials | Restore the old key, or delete and re-create the credentials |
| No default chat model | Chat fails with "No model configured for default for type=chat" | Manage → Models → Default Model Assignments |
| Port 5055 not reachable from the browser | "Unable to Connect to API Server" | Publish 5055, or set `API_URL` behind a proxy |
| `SURREAL_URL` uses `localhost` inside Docker | API won't start, "Database is not reachable yet" in the log | Use the service name: `ws://surrealdb:8000/rpc` |

More in [Troubleshooting](../6-TROUBLESHOOTING/index.md).
