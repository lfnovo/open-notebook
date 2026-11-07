# Environment Variable Reference

The complete list of environment variables Open Notebook and its libraries read. Other pages link here instead of keeping their own lists. AI provider keys are not configured here: add them in **Manage → Models** (see [AI Providers](ai-providers.md)).

---

## How to set a variable

**Docker Compose:** add it under the `open_notebook` service's `environment:` block in `docker-compose.yml`, then run `docker compose up -d`. `docker compose restart` keeps the old environment, so it does not apply changes.

```yaml
services:
  open_notebook:
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=<generated-key>
      - ESPERANTO_LLM_TIMEOUT=300
```

Replace `<generated-key>` with a value you generate yourself, for example with `openssl rand -hex 32` (on Windows, see [Set your encryption key](../1-INSTALLATION/docker-compose.md#step-2-set-your-encryption-key)). Don't reuse an example value.

The shipped `docker-compose.yml` does not load an env file into the container. A `.env` file next to it only fills the `${...}` placeholders in the compose file (`SURREAL_USER`, `SURREAL_PASSWORD`). If you prefer a file, add `env_file: .env` to the `open_notebook` service yourself.

**From source:** put backend variables in `.env` in the project root and restart the API and the worker (`make api`, `make worker-start` both load `.env`). The exception is `OPEN_NOTEBOOK_WORKER_MAX_TASKS`: `make worker-start` reads it from your shell before `.env` is loaded, so `export` it.

Variables read by the frontend (`API_URL`, `INTERNAL_API_URL`, `NEXT_PUBLIC_*`, `NEXT_ALLOWED_DEV_ORIGINS`) are different: `make frontend` runs `npm run dev` inside `frontend/`, and Next.js only loads env files from that directory (`frontend/.env.local`, `frontend/.env`), not the root `.env`. Put them in `frontend/.env.local` or export them in the shell before `make frontend`, then restart it. `NEXT_PUBLIC_*` values are compiled in, so they take effect on the next `npm run dev` or `npm run build`. Most local setups need none of them: without `API_URL`, the browser calls the API directly at `<the host you opened>:5055` (auto-detected, see [Reverse Proxy](reverse-proxy.md#how-the-browser-finds-the-api)). `INTERNAL_API_URL` (default `http://localhost:5055`) only matters for requests that reach the Next.js server's `/api/*` forwarding, for example when `API_URL` points at the frontend's own public URL behind a reverse proxy.

### The "Read by" column

| Value | Meaning |
|-------|---------|
| API | The FastAPI process (port 5055) |
| Worker | The background worker that processes sources, embeddings, insights and podcasts |
| API + Worker | Both. In the Docker image they share the container environment |
| Frontend | The Next.js server, at runtime |
| Frontend build | Compiled into the frontend when it is built. Setting it on the published image does nothing |
| Container | The image's entrypoint or supervisord, at container start |

---

## Security and access

| Variable | Default | Read by | Description |
|----------|---------|---------|-------------|
| `OPEN_NOTEBOOK_ENCRYPTION_KEY` | none | API + Worker | Secret used to encrypt AI provider keys in the database. Use a unique high-entropy value you generate, for example with `openssl rand -hex 32`; the PBKDF2 stretching can't protect a guessable one. **Required** to save credentials in Manage → Models. If you change or lose it, stored keys can no longer be decrypted. Do not keep the `change-me-to-a-secret-string` value from the shipped compose file. See [Security](security.md#api-key-encryption) |
| `OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE` | none | API + Worker | Path to a file holding the encryption key (Docker secrets). Checked before `OPEN_NOTEBOOK_ENCRYPTION_KEY` |
| `OPEN_NOTEBOOK_PASSWORD` | none | API | Password for the UI and the REST API. Unset means authentication is off. See [Security](security.md) |
| `OPEN_NOTEBOOK_PASSWORD_FILE` | none | API | Path to a file holding the password (Docker secrets). Checked before `OPEN_NOTEBOOK_PASSWORD` |
| `CORS_ORIGINS` | `*` | API | Comma-separated origins allowed to call the API, e.g. `https://notebook.example.com`. The API logs a warning at startup while it is unset. Restart the API after changing it. See [Security](security.md#cors-origins) |

---

## Database (SurrealDB)

Set all five `SURREAL_*` variables explicitly, as the shipped compose file does. The API and the job queue (the surreal-commands library) fall back to different defaults when they are missing: the API uses `open_notebook` for namespace and database, the job queue uses `test`. With mismatched defaults, jobs are written where the worker never looks.

| Variable | Default when unset | Read by | Description |
|----------|--------------------|---------|-------------|
| `SURREAL_URL` | built from `SURREAL_ADDRESS`/`SURREAL_PORT` | API + Worker | WebSocket URL, e.g. `ws://surrealdb:8000/rpc` (compose) or `ws://localhost:8000/rpc` (from source). See [Database](database.md) |
| `SURREAL_USER` | none in the API (sign-in fails); `test` in the job queue | API + Worker | SurrealDB user. Must match the `--user` the database was started with |
| `SURREAL_PASSWORD` | `root` in the API; `test` in the job queue | API + Worker | SurrealDB password. Must match `--pass`. Change it before exposing the instance |
| `SURREAL_NAMESPACE` | `open_notebook` in the API; `test` in the job queue | API + Worker | SurrealDB namespace |
| `SURREAL_DATABASE` | `open_notebook` in the API; `test` in the job queue | API + Worker | SurrealDB database |
| `SURREAL_ADDRESS`, `SURREAL_PORT` | `localhost`, `8000` | API + Worker | Legacy fallback used only when `SURREAL_URL` is unset. `SURREAL_ADDRESS` may already include the port. Prefer `SURREAL_URL` |
| `SURREAL_PASS` | none | API + Worker | Legacy alias of `SURREAL_PASSWORD` |

With Docker Compose, `SURREAL_USER` and `SURREAL_PASSWORD` are the two values you can keep in `.env`: the compose file passes them to both the `surrealdb` and `open_notebook` services.

---

## Network, ports and URLs

| Variable | Default | Read by | Description |
|----------|---------|---------|-------------|
| `API_URL` | auto-detected | Frontend | The API address **as the browser reaches it**. When unset, the frontend uses the host the page was loaded from plus port 5055 (`http://<host>:5055`). Set it behind a reverse proxy (`https://notebook.example.com`, no `/api` suffix) or when the API is not on port 5055. See [Reverse Proxy](reverse-proxy.md#how-the-browser-finds-the-api) |
| `NEXT_PUBLIC_API_URL` | none | Frontend, Frontend build | Older name for `API_URL`, used only when `API_URL` is unset |
| `INTERNAL_API_URL` | `http://localhost:5055` | Frontend | Where the Next.js server forwards `/api/*` requests. Only change it if the API is not in the same container |
| `API_HOST` | `0.0.0.0` in the image; `127.0.0.1` from source | API | Interface the API binds to. Set `::` for IPv6 dual-stack |
| `API_PORT` | `5055` | API (from source only) | Port for `run_api.py` (`make api`). The Docker image always uses 5055; change the host side of the port mapping instead |
| `API_RELOAD` | `true` | API (from source only) | Auto-reload on code changes when started with `run_api.py` |
| `FRONTEND_BIND_HOST` | `0.0.0.0` | Container | Interface the Next.js server binds to inside the container. Replaces `HOSTNAME`, which runtimes such as Podman overwrite |
| `NEXT_ALLOWED_DEV_ORIGINS` | none | Frontend (dev server only) | Comma-separated hostnames allowed to reach `npm run dev` from another machine (LAN IP, custom hostname) |
| `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` | `100` | API | Largest request body the API accepts. Larger requests get `413 Request body exceeds the maximum allowed upload size`. By default the browser uploads straight to the API (port 5055), so this is the app's only limit. When `API_URL` points at the frontend's own URL, uploads go through the Next.js `/api/*` forwarding instead, which is capped at 100 MB in the build. A reverse proxy's own limit (nginx `client_max_body_size`) also applies |

### Outbound proxy

| Variable | Default | Read by | Description |
|----------|---------|---------|-------------|
| `HTTP_PROXY` | none | API + Worker | Proxy for outbound HTTP (AI providers, URL extraction, podcast TTS) |
| `HTTPS_PROXY` | none | API + Worker | Proxy for outbound HTTPS |
| `NO_PROXY` | none | API + Worker | Hosts that bypass the proxy. Must include the SurrealDB host |

`NO_PROXY` must list the internal database hosts (`surrealdb`, `host.docker.internal`, `localhost`). The SurrealDB client connects over a websocket, and `websockets` 15+ sends even `ws://` connections through a configured proxy, which then rejects the internal host with HTTP 403 and the API and worker fail to start. Open Notebook adds `host.docker.internal,surrealdb,localhost,127.0.0.1` and the host from `SURREAL_URL` to `NO_PROXY` at startup as a safety net, but set them explicitly too.

```bash
HTTP_PROXY=http://user:password@proxy.corp.com:8080
HTTPS_PROXY=http://user:password@proxy.corp.com:8080
NO_PROXY=localhost,127.0.0.1,host.docker.internal,surrealdb,.local
```

---

## Timeouts

| Variable | Default | Read by | Description |
|----------|---------|---------|-------------|
| `ESPERANTO_LLM_TIMEOUT` | `180` | API + Worker | Seconds each language-model call may take: chat, Ask, transformations, insights, podcast outline and transcript. Applies to every provider, Ollama included. Open Notebook sets 180 when unset (the library default is 60). Keep it below 600 so the call fails with a clear error before the web UI gives up |
| `NEXT_PUBLIC_API_TIMEOUT_MS` | `600000` | Frontend build | How long the web UI waits for an API response, in milliseconds. `0` disables it. Compiled into the frontend, so the published images always wait 10 minutes |
| `ESPERANTO_EMBEDDING_TIMEOUT` | `60` | API + Worker | Seconds per embedding request |
| `ESPERANTO_RERANKER_TIMEOUT` | `60` | API + Worker | Seconds per reranker request (library setting; Open Notebook does not use rerankers today) |
| `ESPERANTO_TTS_TIMEOUT` | `300` | Worker | Seconds per text-to-speech request during podcast generation. Raise it for slow self-hosted TTS |
| `ESPERANTO_STT_TIMEOUT` | `300` | API + Worker | Seconds per speech-to-text request made directly through Esperanto. Source transcription uses `CCORE_STT_TIMEOUT` instead |
| `CCORE_STT_TIMEOUT` | `3600` | Worker | Seconds per speech-to-text request when transcribing audio and video sources |

---

## SSL for AI providers

| Variable | Default | Read by | Description |
|----------|---------|---------|-------------|
| `ESPERANTO_SSL_CA_BUNDLE` | none | API + Worker | Path (inside the container) to a CA bundle that signs your provider's certificate. Applies to model calls and to Test Connection / model discovery |
| `ESPERANTO_SSL_VERIFY` | `true` | API + Worker | `false` turns off certificate verification. Development only |

---

## Worker and background jobs

| Variable | Default | Read by | Description |
|----------|---------|---------|-------------|
| `OPEN_NOTEBOOK_WORKER_MAX_TASKS` | `5` | Container / `make worker-start` | Jobs the worker runs at once. Set `1` for a local model on a single GPU. Passed to the worker as `--max-tasks` at launch |
| `TTS_BATCH_SIZE` | `5` | Worker | Text-to-speech requests sent in parallel per podcast. Lower it (for example `1` or `2`) for rate-limited or single-threaded TTS servers |
| `SURREAL_COMMANDS_RETRY_ENABLED` | `false` | Worker | Turns on the job queue's global retry policy. See the note below |
| `SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS` | `3` | Worker | Global policy: attempts, including the first |
| `SURREAL_COMMANDS_RETRY_WAIT_STRATEGY` | `exponential` | Worker | Global policy: `exponential`, `exponential_jitter`, `fixed` or `random` |
| `SURREAL_COMMANDS_RETRY_WAIT_MIN` | `1` | Worker | Global policy: minimum wait between attempts, seconds |
| `SURREAL_COMMANDS_RETRY_WAIT_MAX` | `60` | Worker | Global policy: maximum wait, seconds |
| `SURREAL_COMMANDS_RETRY_WAIT_TIME` | `1` | Worker | Global policy: wait for the `fixed` strategy, seconds |
| `SURREAL_COMMANDS_RETRY_WAIT_MULTIPLIER` | `2` | Worker | Global policy: exponential backoff multiplier |
| `SURREAL_COMMANDS_RETRY_LOG_LEVEL` | `info` | Worker | Global policy: log level for retry messages (`debug`, `info`, `warning`, `error`, `none`) |

> **The `SURREAL_COMMANDS_RETRY_*` variables rarely change anything.** Each Open Notebook job declares its own retry policy, and a job's own policy overrides the global one: source processing retries up to 15 times, embeddings, insights and transformations up to 5, and podcast generation runs once. Only jobs without a policy of their own (today, the "rebuild embeddings" coordinator) follow the global settings. Errors that can't succeed on retry, such as a failed extraction or a missing model, are never retried.

---

## Embeddings and chunking

| Variable | Default | Read by | Description |
|----------|---------|---------|-------------|
| `OPEN_NOTEBOOK_CHUNK_SIZE` | `400` | API + Worker | Tokens per chunk when splitting content for embedding. Minimum 100 |
| `OPEN_NOTEBOOK_CHUNK_OVERLAP` | 15% of the chunk size | API + Worker | Tokens shared between consecutive chunks |
| `OPEN_NOTEBOOK_MIN_CHUNK_SIZE` | `5` | API + Worker | Chunks shorter than this (in tokens) are dropped before embedding. Some providers, such as llama.cpp, return null vectors for one-character chunks. `0` disables the filter |
| `OPEN_NOTEBOOK_EMBEDDING_BATCH_SIZE` | `50` | API + Worker | Texts per embedding request. Lower it for CPU-only or strict OpenAI-compatible embedding servers |

Changing chunk settings affects new embeddings only. Rebuild existing embeddings from the **Advanced** page afterwards.

---

## Content extraction

Open Notebook passes these to the content-core library, which runs extraction in the worker. Which engine is used is chosen in **Settings → Content Processing** (see [Content Processing Engines](../3-USER-GUIDE/content-processing-engines.md)).

| Variable | Default | Read by | Description |
|----------|---------|---------|-------------|
| `FIRECRAWL_API_KEY` | none | Worker | Firecrawl API key for the `firecrawl` URL engine |
| `FIRECRAWL_API_URL` | `https://api.firecrawl.dev` | Worker | Base URL of a self-hosted Firecrawl |
| `CCORE_FIRECRAWL_PROXY` | `auto` | Worker | Firecrawl proxy mode: `basic`, `stealth` or `auto` |
| `CCORE_FIRECRAWL_WAIT_FOR` | `3000` | Worker | Milliseconds Firecrawl waits for JavaScript before capturing the page |
| `JINA_API_KEY` | none | Worker | Jina Reader API key for the `jina` URL engine. Optional: without it, requests are sent unauthenticated |
| `CRAWL4AI_API_URL` | none | Worker, API | Base URL of a remote Crawl4AI server. When set, the `crawl4ai` engine uses it and no local install is needed |
| `CRAWL4AI_API_TOKEN` | none | Worker | Bearer token for that server. Crawl4AI Docker 0.9.0 and later reject unauthenticated connections |
| `CCORE_YOUTUBE_PROXY` | none | Worker | Proxy for YouTube transcript requests, e.g. `http://user:pass@proxy:port`. Use a residential proxy; YouTube blocks datacenter IPs |
| `CCORE_YOUTUBE_COOKIES_FILE` | none | Worker | Path inside the container to a Netscape-format `cookies.txt` exported from a browser signed in to YouTube. A missing or unreadable file fails YouTube sources with a configuration error |
| `CCORE_AUDIO_SEGMENT_MINUTES` | `10` | Worker | Long audio and video is split into segments of this many minutes before transcription. `0` sends the file whole (for self-hosted speech-to-text without an upload limit) |
| `CCORE_AUDIO_CONCURRENCY` | `3` | Worker | Segments transcribed in parallel (1 to 10) |

The speech-to-text model, the URL and document engines and the preferred YouTube transcript languages come from Open Notebook's settings, so the matching `CCORE_*` variables (`CCORE_AUDIO_MODEL`, `CCORE_URL_ENGINE`, `CCORE_YOUTUBE_LANGUAGES` and so on) are overridden and have no effect.

YouTube cookies with Docker Compose:

```yaml
services:
  open_notebook:
    environment:
      - CCORE_YOUTUBE_COOKIES_FILE=/app/data/youtube-cookies.txt
    volumes:
      - ./notebook_data:/app/data   # put youtube-cookies.txt in ./notebook_data
```

### Optional heavy runtimes

Off by default to keep the image small. When set to `true`, the container installs the runtime on startup before the app starts; downloads are cached on the `/app/data` volume, so only the first start is slow. See [Content Processing Engines → Optional engines](../3-USER-GUIDE/content-processing-engines.md#optional-engines-docling--crawl4ai).

| Variable | Default | Read by | Description |
|----------|---------|---------|-------------|
| `OPEN_NOTEBOOK_ENABLE_DOCLING` | `false` | Container | Install Docling: enables the `docling` document engine, OCR and image sources. Large download |
| `OPEN_NOTEBOOK_ENABLE_CRAWL4AI` | `false` | Container | Install local Crawl4AI and a Chromium browser: enables the `crawl4ai` URL engine. Not needed when `CRAWL4AI_API_URL` is set |

If an engine is selected in Settings but its runtime is missing, extraction falls back to `auto` and the worker logs `Configured ... engine '...' is selected in Content Settings but its runtime is not available in this container`.

### Cache locations (set by the image)

| Variable | Image value | Description |
|----------|-------------|-------------|
| `TIKTOKEN_CACHE_DIR` | `/app/tiktoken-cache` | Token-counting encoding cache. From source it defaults to `./data/tiktoken-cache` |
| `UV_CACHE_DIR` | `/app/data/.cache/uv` | Package cache for the optional runtimes |
| `PLAYWRIGHT_BROWSERS_PATH` | `/app/data/.cache/playwright` | Chromium download for local Crawl4AI |
| `HF_HOME` | `/app/data/.cache/huggingface` | Model cache for Docling |

---

## Logging and tracing

| Variable | Default | Read by | Description |
|----------|---------|---------|-------------|
| `LOGURU_LEVEL` | `DEBUG` | API + Worker | Minimum level of the API and worker logs (`INFO`, `WARNING`, ...) |
| `LANGSMITH_TRACING` (or `LANGCHAIN_TRACING_V2`) | off | API + Worker | `true` sends LangChain/LangGraph traces to LangSmith |
| `LANGSMITH_API_KEY` (or `LANGCHAIN_API_KEY`) | none | API + Worker | LangSmith API key |
| `LANGSMITH_ENDPOINT` (or `LANGCHAIN_ENDPOINT`) | `https://api.smith.langchain.com` | API + Worker | LangSmith endpoint |
| `LANGSMITH_PROJECT` (or `LANGCHAIN_PROJECT`) | `default` | API + Worker | LangSmith project name |

Tracing sends prompts and source content to LangSmith. Setup: https://smith.langchain.com/

SurrealDB's own log level is the `--log` argument in the `surrealdb` service's `command:` (`info` in the shipped compose file).

---

## Legacy: AI provider variables (deprecated)

> **Deprecated.** Configure providers in **Manage → Models**. These variables still work as a fallback (the database is read first, then the environment), but there is no guarantee they keep working, and new automation should not be built on them. A declarative provisioning contract for headless deployments is being discussed in [#765](https://github.com/lfnovo/open-notebook/discussions/765).

If you have them set, **Manage → Models** shows **Environment Variables Detected** with a **Migrate to Database** button. Migration creates a credential named "Default (Migrated from env)" per provider. It copies only the variables marked "yes" below; the others keep working only as an environment fallback and must be re-entered by hand if you remove them.

| Variable | Provider | Copied by Migrate to Database |
|----------|----------|-------------------------------|
| `OPENAI_API_KEY` | OpenAI | yes |
| `ANTHROPIC_API_KEY` | Anthropic | yes |
| `GOOGLE_API_KEY` or `GEMINI_API_KEY` | Google AI | yes (`GOOGLE_API_KEY` wins) |
| `GEMINI_API_BASE_URL` | Google AI | no |
| `GROQ_API_KEY` | Groq | yes |
| `MISTRAL_API_KEY` | Mistral AI | yes |
| `DEEPSEEK_API_KEY` | DeepSeek | yes |
| `XAI_API_KEY` | xAI | yes |
| `OPENROUTER_API_KEY` | OpenRouter | yes |
| `OPENROUTER_BASE_URL` | OpenRouter | no |
| `DASHSCOPE_API_KEY` | DashScope (Qwen) | yes |
| `MINIMAX_API_KEY`, `MINIMAX_BASE_URL` | MiniMax | yes (base URL into the credential's Base URL) |
| `NOVITA_API_KEY` | Novita | yes |
| `SILICONFLOW_API_KEY`, `SILICONFLOW_BASE_URL` | SiliconFlow | yes (base URL into the credential's Base URL) |
| `ZAI_API_KEY`, `ZAI_BASE_URL` | Z.ai | yes (base URL into the credential's Base URL) |
| `PPQ_API_KEY` | PayPerQ | yes |
| `COHERE_API_KEY` | Cohere | yes |
| `VOYAGE_API_KEY` | Voyage AI | yes |
| `ELEVENLABS_API_KEY` | ElevenLabs | yes |
| `DEEPGRAM_API_KEY` | Deepgram | yes |
| `OLLAMA_API_BASE` | Ollama | yes |
| `OMLX_API_BASE`, `OMLX_API_KEY` | oMLX | yes |
| `VERTEX_PROJECT`, `VERTEX_LOCATION`, `GOOGLE_APPLICATION_CREDENTIALS` | Google Vertex AI | yes |
| `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION` | Azure OpenAI | yes |
| `AZURE_OPENAI_ENDPOINT_LLM`, `_EMBEDDING`, `_STT`, `_TTS` | Azure OpenAI | yes |
| `AZURE_OPENAI_API_KEY_LLM`, `_EMBEDDING`, `_STT`, `_TTS` | Azure OpenAI | no |
| `AZURE_OPENAI_API_VERSION_LLM`, `_EMBEDDING`, `_STT`, `_TTS` | Azure OpenAI | no |
| `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_API_KEY` | OpenAI Compatible | yes |
| `OPENAI_COMPATIBLE_BASE_URL_LLM`, `_EMBEDDING`, `_STT`, `_TTS` | OpenAI Compatible | no |
| `OPENAI_COMPATIBLE_API_KEY_LLM`, `_EMBEDDING`, `_STT`, `_TTS` | OpenAI Compatible | no |
| `ANTHROPIC_COMPATIBLE_BASE_URL`, `ANTHROPIC_COMPATIBLE_API_KEY` | Anthropic Compatible | yes |

---

## Variables that do nothing

These appear in older guides, examples or forum posts. Nothing in Open Notebook or its libraries reads them:

| Variable | Use instead |
|----------|-------------|
| `API_CLIENT_TIMEOUT` | `ESPERANTO_LLM_TIMEOUT` (backend) and, when building the frontend yourself, `NEXT_PUBLIC_API_TIMEOUT_MS` |
| `SURREAL_COMMANDS_MAX_TASKS` | `OPEN_NOTEBOOK_WORKER_MAX_TASKS` |
| `CHUNK_SIZE`, `CHUNK_OVERLAP` | `OPEN_NOTEBOOK_CHUNK_SIZE`, `OPEN_NOTEBOOK_CHUNK_OVERLAP` |
| `LOGLEVEL`, `RUST_LOG` | `LOGURU_LEVEL` for the app; `--log` in the `surrealdb` command for the database |
| `HOSTNAME` (to change the frontend bind address) | `FRONTEND_BIND_HOST` |

---

## Checking what the container sees

```bash
# One non-secret variable
docker compose exec open_notebook printenv OPEN_NOTEBOOK_WORKER_MAX_TASKS

# Every variable set in the container, names only (no values, so no secrets are printed)
docker compose exec open_notebook sh -c 'printenv | cut -d= -f1 | sort'
```

Don't print `OPEN_NOTEBOOK_ENCRYPTION_KEY`, `OPEN_NOTEBOOK_PASSWORD` or `SURREAL_PASSWORD` into output you share in an issue or a chat.

Variable names are case-sensitive. In `docker-compose.yml` list syntax, don't put spaces around `=` and don't quote the value unless the quotes should be part of it.
