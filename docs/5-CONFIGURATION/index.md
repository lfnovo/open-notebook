# Configuration

Open Notebook is configured in two places:

1. **Environment variables** for infrastructure: the encryption key, the database connection, the API URL, timeouts. The complete list is the [Environment Reference](environment-reference.md).
2. **The web UI** for everything else: AI provider credentials and models in **Manage → Models**, content processing engines in **Settings**.

---

## Where environment variables go

### Docker Compose

The shipped `docker-compose.yml` reads four variables from a `.env` file next to it: `OPEN_NOTEBOOK_ENCRYPTION_KEY`, `OPEN_NOTEBOOK_PASSWORD`, `SURREAL_USER` and `SURREAL_PASSWORD`. Everything else goes under the `open_notebook` service's `environment:` block. Then run:

```bash
docker compose up -d
```

`docker compose restart` keeps the old environment, so it does not apply changes.

```text
# .env — these four are the ones the shipped compose file reads
OPEN_NOTEBOOK_ENCRYPTION_KEY=<generated-key>
```

```yaml
services:
  open_notebook:
    environment:
      - API_URL=https://notebook.example.com
```

Replace `<generated-key>` with a value you generate yourself, for example with `openssl rand -hex 32` (on Windows, see [Set your encryption key](../1-INSTALLATION/docker-compose.md#step-2-set-your-encryption-key)). Don't reuse an example value.

Editing those four lines in `docker-compose.yml` is a valid alternative. The compose file does not load the rest of `.env` into the container (there is no `env_file:`).

### From source

Put backend variables in `.env` in the project root (start from `.env.example`) and restart the API and the worker (`make api` and `make worker-start` load it). The exception is `OPEN_NOTEBOOK_WORKER_MAX_TASKS`, which `make worker-start` reads from your shell: `export` it first.

Frontend variables (`API_URL`, `INTERNAL_API_URL`, `NEXT_PUBLIC_*`) are not read from the root `.env`; see [Environment Reference → How to set a variable](environment-reference.md#how-to-set-a-variable).

---

## The settings that matter

### Encryption key (required)

```yaml
- OPEN_NOTEBOOK_ENCRYPTION_KEY=<generated-key>
```

Encrypts the provider API keys you save in Manage → Models. Generate the value yourself, for example with `openssl rand -hex 32`. With the shipped compose file, put it in `.env`. Without it you can't save credentials. Replace the `change-me-to-a-secret-string` placeholder, and don't change the value later: credentials saved with the old key become unreadable. See [Security](security.md#api-key-encryption).

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

Providers are connected in **Manage → Models**: add a configuration, test it, add models and set the default models. Follow [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider) for the steps.

Details for each provider: [AI Providers](ai-providers.md). Local options: [Ollama](ollama.md), [oMLX](omlx.md), [OpenAI-Compatible](openai-compatible.md) (LM Studio, vLLM, llama.cpp…), [Local speech with Speaches](local-tts.md).

### API URL (usually not needed)

The browser finds the API automatically at `<the host you opened>:5055`. Set `API_URL` only when that's wrong: behind a reverse proxy (`API_URL=https://notebook.example.com`) or when the API is published on another port. See [Reverse Proxy](reverse-proxy.md#how-the-browser-finds-the-api).

### Password

Set `OPEN_NOTEBOOK_PASSWORD` for anything reachable beyond your own machine. With the shipped compose file, put it in `.env`. Without it, authentication is off. See [Security](security.md).

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
| Other variable added to `.env` only (Docker) | Setting has no effect | Put it under `open_notebook` → `environment:`. The compose file only reads `OPEN_NOTEBOOK_ENCRYPTION_KEY`, `OPEN_NOTEBOOK_PASSWORD`, `SURREAL_USER` and `SURREAL_PASSWORD` from `.env` |
| `docker compose restart` after editing | Old values still used | `docker compose up -d` |
| No encryption key | "Encryption key not configured" in **Manage → Models** | Set `OPEN_NOTEBOOK_ENCRYPTION_KEY` |
| Encryption key changed | "Decryption Error" on saved credentials | Restore the old key, or delete and re-create the credentials |
| No default chat model | Chat fails with "No model configured for default for type=chat" | Manage → Models → Default Model Assignments |
| Port 5055 not reachable from the browser | "Unable to Connect to API Server" | Publish 5055, or set `API_URL` behind a proxy |
| `SURREAL_URL` uses `localhost` inside Docker | API won't start, "Database is not reachable yet" in the log | Use the service name: `ws://surrealdb:8000/rpc` |

More in [Troubleshooting](../6-TROUBLESHOOTING/index.md).
