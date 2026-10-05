# Advanced Configuration

Performance tuning, ports, logging, backups and container management. Every variable mentioned here is described in the [Environment Reference](environment-reference.md); this page explains when to change them.

With Docker Compose, variables go under the `open_notebook` service's `environment:` block and take effect with `docker compose up -d` (`docker compose restart` keeps the old environment).

---

## Performance Tuning

### Worker concurrency

`OPEN_NOTEBOOK_WORKER_MAX_TASKS` (default `5`) is how many background jobs run at once: source processing, embeddings, insights, transformations and podcasts.

| Setup | Value |
|-------|-------|
| Local model on a single GPU (Ollama, LM Studio) | `1` |
| Cloud provider with tight rate limits | `2`–`3` |
| Cloud provider with plenty of quota | `5` (default) or more |

Higher values process bulk uploads faster but send more parallel requests to your models and cause more SurrealDB transaction conflicts. Conflicts are retried automatically (source processing up to 15 times).

The value is read when the worker starts. In Docker, recreate the container (`docker compose up -d`). From source, `export` it in your shell before `make worker-start`.

### Model call timeout

`ESPERANTO_LLM_TIMEOUT` (default `180` seconds) limits each language-model call and applies to every provider, Ollama included. When a call runs out of time, the user sees an error and the job or chat message fails.

- Slow local models (large models on CPU, first load of a model): raise it, for example `ESPERANTO_LLM_TIMEOUT=420`.
- Keep it **below 600**. The web UI waits 10 minutes for a response (`NEXT_PUBLIC_API_TIMEOUT_MS`), and that value is compiled into the published images. Reverse proxies need read timeouts of at least 600 seconds too (see [Reverse Proxy → Timeouts](reverse-proxy.md#timeouts)).

Speech has its own timeouts: `ESPERANTO_TTS_TIMEOUT` (300 s, podcast audio) and `CCORE_STT_TIMEOUT` (3600 s, transcription of audio and video sources).

### Podcast audio

`TTS_BATCH_SIZE` (default `5`) is how many text-to-speech requests a podcast sends in parallel. Lower it to `1` or `2` for self-hosted TTS servers and providers with strict concurrency limits; generation gets slower but stops failing on rate limits.

### Embeddings

For CPU-only or strict OpenAI-compatible embedding servers, lower `OPEN_NOTEBOOK_EMBEDDING_BATCH_SIZE` (default `50`). Chunking is controlled by `OPEN_NOTEBOOK_CHUNK_SIZE` (400 tokens) and `OPEN_NOTEBOOK_CHUNK_OVERLAP` (15%). After changing chunking or the embedding model, rebuild embeddings from the **Advanced** page.

---

## Ports

| Service | Port | Notes |
|---------|------|-------|
| Web UI | 8502 (Docker), 3000 (`npm run dev` from source) | |
| API | 5055 | |
| SurrealDB | 8000 | Published on `127.0.0.1` only in the shipped compose file |

### Changing the web UI port

Change the host side of the mapping:

```yaml
services:
  open_notebook:
    ports:
      - "8001:8502"   # UI now at http://localhost:8001
      - "5055:5055"
```

The API address is still auto-detected as `<host>:5055`, so nothing else changes.

### Changing the API port

```yaml
services:
  open_notebook:
    ports:
      - "8502:8502"
      - "5056:5055"   # API published on 5056
    environment:
      - API_URL=http://localhost:5056   # the address the browser uses
```

Auto-detection assumes port 5055, so set `API_URL` whenever the API is published elsewhere. Inside the container the API always listens on 5055.

### Changing the SurrealDB port

Only the host side of the mapping changes. Containers talk to each other on the compose network, where SurrealDB stays on 8000, so `SURREAL_URL=ws://surrealdb:8000/rpc` stays as it is:

```yaml
services:
  surrealdb:
    ports:
      - "127.0.0.1:8001:8000"   # host tools (Surrealist, surreal sql) now use 8001
```

---

## SSL for Self-Signed Providers

If a provider endpoint (Ollama behind a proxy, an internal OpenAI-compatible server) uses a certificate your container doesn't trust, mount the CA bundle and point `ESPERANTO_SSL_CA_BUNDLE` at it:

```yaml
services:
  open_notebook:
    environment:
      - ESPERANTO_SSL_CA_BUNDLE=/certs/ca-bundle.pem
    volumes:
      - /path/to/ca-bundle.pem:/certs/ca-bundle.pem:ro
```

This covers model calls and the credential **Test Connection** and model discovery. `ESPERANTO_SSL_VERIFY=false` turns verification off entirely; use it only for short tests on a trusted network.

---

## Logging & Debugging

### Application logs

All three processes (API, worker, frontend) log to the container output:

```bash
docker compose logs -f open_notebook
docker compose logs --since 10m open_notebook | grep -iE "error|warning"
```

Set `LOGURU_LEVEL=INFO` (or `WARNING`) to hide debug lines from the API and worker. The worker log includes content-core's extraction messages, which is where the full reason for a failed source appears.

### SurrealDB logs

The database log level is the `--log` argument in the `surrealdb` service's `command:` (`info` in the shipped compose file; `debug` and `trace` are more verbose).

```bash
docker compose logs -f surrealdb
```

### LangSmith tracing

To inspect the LangGraph workflows (chat, Ask, transformations):

```yaml
environment:
  - LANGSMITH_TRACING=true
  - LANGSMITH_API_KEY=your-key
  - LANGSMITH_PROJECT=open-notebook   # optional; default "default"
```

Traces include your prompts and source content. The older `LANGCHAIN_*` names also work.

---

## Content Extraction Engines

Which engine extracts URLs and documents is chosen in **Settings → Content Processing** (see [Content Processing Engines](../3-USER-GUIDE/content-processing-engines.md)). Engines that need configuration:

- **Firecrawl:** `FIRECRAWL_API_KEY`, optionally `FIRECRAWL_API_URL` for a self-hosted instance.
- **Jina:** `JINA_API_KEY` (optional).
- **Crawl4AI:** `OPEN_NOTEBOOK_ENABLE_CRAWL4AI=true` installs it in the container on first start; or point `CRAWL4AI_API_URL` (and `CRAWL4AI_API_TOKEN`) at a remote Crawl4AI server.
- **Docling:** `OPEN_NOTEBOOK_ENABLE_DOCLING=true` installs it on first start.
- **YouTube blocked:** `CCORE_YOUTUBE_PROXY` or `CCORE_YOUTUBE_COOKIES_FILE`.

Details and defaults: [Environment Reference → Content extraction](environment-reference.md#content-extraction).

---

## Using Several Providers

Each provider gets its own credential in **Manage → Models**, and every registered model is tied to the credential it came from. A common split:

- Chat and transformations from one provider (for example Anthropic, which has no embedding models)
- Embeddings from another (OpenAI, Google, Voyage AI, Mistral, Ollama…)
- Text-to-speech from a third (ElevenLabs, or a local Speaches server through OpenAI Compatible)

Then pick a model for each role under **Default Model Assignments** on the same page.

To use several OpenAI-compatible servers (say, LM Studio for chat and Speaches for speech), add one **OpenAI Compatible** credential per server, each with its own **Base URL**. See [OpenAI-Compatible Providers](openai-compatible.md).

---

## Backup & Restore

### What to back up

With the shipped compose file, everything lives in two directories next to `docker-compose.yml`:

| Host directory | Container path | Contents |
|----------------|----------------|----------|
| `./notebook_data` | `/app/data` (open_notebook) | Uploaded files, podcast audio, chat checkpoints, caches |
| `./surreal_data` | `/mydata` (surrealdb) | The SurrealDB database |

The single-container image keeps the database in `./surreal_single_data` instead (see `examples/docker-compose-single.yml`). Also keep `OPEN_NOTEBOOK_ENCRYPTION_KEY` somewhere safe and separate: without it, the stored provider keys in a restored database can't be decrypted.

### Backup

```bash
# Stop for a consistent copy of the database
docker compose down
tar -czf open-notebook-$(date +%Y%m%d-%H%M%S).tar.gz notebook_data/ surreal_data/
docker compose up -d
```

Take a backup before every upgrade. Some upgrades change data in ways older versions can't read (for example the v1.15.0 credential encryption, see [Security](security.md#upgrading-to-pbkdf2-v1150)), and restoring a backup is the only way back.

A daily cron job:

```bash
#!/bin/bash
# backup.sh
cd /path/to/open-notebook            # the directory with docker-compose.yml
BACKUP_DIR=/path/to/backups
DATE=$(date +%Y%m%d-%H%M%S)

docker compose down
tar -czf "$BACKUP_DIR/open-notebook-$DATE.tar.gz" notebook_data/ surreal_data/
docker compose up -d

# Keep the last 7 days
find "$BACKUP_DIR" -name "open-notebook-*.tar.gz" -mtime +7 -delete
```

```bash
0 2 * * * /path/to/backup.sh >> /var/log/open-notebook-backup.log 2>&1
```

### Restore

```bash
docker compose down
mv notebook_data notebook_data.old && mv surreal_data surreal_data.old
tar -xzf open-notebook-20260115-020000.tar.gz
docker compose up -d
```

Restore with the same image version you backed up from, or a newer one. Database migrations run automatically on startup and only move forward.

### Moving to another server

Copy the backup archive and your `docker-compose.yml` (with the same `OPEN_NOTEBOOK_ENCRYPTION_KEY`), extract the archive next to it, and run `docker compose up -d`.

---

## Container Management

The shipped compose file has two services: `surrealdb` and `open_notebook`. The API, worker and frontend are processes inside `open_notebook`, so they are started, stopped and logged together.

```bash
docker compose up -d                    # start, or apply changes to docker-compose.yml
docker compose ps                       # status
docker compose logs -f open_notebook    # app logs (API, worker, frontend)
docker compose logs -f surrealdb        # database logs
docker compose restart open_notebook    # restart without changing configuration
docker compose down                     # stop (data in ./notebook_data and ./surreal_data stays)
docker compose pull && docker compose up -d   # update to the latest image (back up first)
docker stats                            # CPU and memory per container
```

`docker compose down -v` does not delete your data either: the shipped file uses bind mounts, not named volumes. To start from scratch, stop the stack and delete `./notebook_data` and `./surreal_data` yourself.

---

## Related

- [Environment Reference](environment-reference.md) — every variable, default and consumer
- [Security](security.md) — password, encryption key, CORS
- [Reverse Proxy](reverse-proxy.md) — HTTPS and custom domains
- [Troubleshooting](../6-TROUBLESHOOTING/index.md)
