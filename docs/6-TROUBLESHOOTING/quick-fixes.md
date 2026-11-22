# Quick Fixes - The Most Common Problems

The problems people hit most often, with the short fix and a link to the full entry. Commands assume the shipped `docker-compose.yml` (services `surrealdb` and `open_notebook`).

Two rules apply to every fix that changes a setting:

- Settings go under the `open_notebook` service's `environment:` block. A variable that is only in `.env` doesn't reach the container.
- Apply changes with `docker compose up -d`. `docker compose restart` keeps the old environment.

---

## #1: "Unable to Connect to API Server"

The UI loads but can't reach the API.

```bash
curl http://localhost:5055/health     # expect {"status":"healthy"}
docker compose ps                     # open_notebook must be Up
```

If the API answers locally but not from the browser: port 5055 must be reachable from your machine, or, behind a reverse proxy, `API_URL` must be set to your public URL. → [Connection Issues](connection-issues.md#unable-to-connect-to-api-server)

---

## #2: Chat fails with "No model configured for default for type=chat"

No models are assigned yet. Follow [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider) in **Manage → Models** through step 4 (**Auto-assign Defaults** under Default Model Assignments). → [AI & Chat Issues](ai-chat-issues.md#no-model-configured-for-default-for-typechat)

---

## #3: "Encryption key not configured"

You can't save provider credentials until `OPEN_NOTEBOOK_ENCRYPTION_KEY` is set in the `open_notebook` environment. → [AI & Chat Issues](ai-chat-issues.md#encryption-key-not-configured)

---

## #4: "Cannot process file" or "Unsupported format"

- Rejected on upload with "… (detected type: …)": the file type can't be extracted. Convert it (PDF, DOCX, TXT…). Images and scanned PDFs need `OPEN_NOTEBOOK_ENABLE_DOCLING=true`.
- Rejected with "Request body exceeds the maximum allowed upload size": the file is over `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` (default 100 MB). Raise it; if `API_URL` points at the frontend's own address, the frontend proxy also caps uploads at 100 MB.
- Uploaded, then **Failed**: the reason is in the worker log and the source's status. → [Processing Issues → Failed sources](processing-issues.md#failed-sources)

---

## #5: Sources stay "Queued"

The background worker isn't processing jobs. → [Processing Issues](processing-issues.md#sources-stay-queued-waiting-to-be-processed)

---

## #6: "The AI provider took too long to respond"

A model call took longer than `ESPERANTO_LLM_TIMEOUT` (180 seconds by default). Use a faster model or less context, or raise the timeout (below 600):

```yaml
services:
  open_notebook:
    environment:
      - ESPERANTO_LLM_TIMEOUT=420
```

On v1.15.0 the same timeout shows as "Could not connect to the AI provider…" after a long wait. → [AI & Chat Issues](ai-chat-issues.md#the-ai-provider-took-too-long-to-respond)

---

## #7: Search returns nothing

- "Vector search requires an embedding model. Only text search is available.": assign an **Embedding Model** in Manage → Models.
- Embedding model assigned, still nothing: sources added before it was set (or after you changed it) have no matching embeddings. Rebuild them from the **Advanced** page.

→ [Processing Issues → Search](processing-issues.md#search-and-ask)

---

## #8: "Podcast generation failed"

Open **Podcasts → Episodes**; the failed episode shows the error and a **Retry** button.

- "Speaker profile 'X' has no voice model configured": the speaker profiles that ship with Open Notebook have no text-to-speech model. Edit them in **Podcasts → Profiles** and pick one.
- `Voice name ... not supported` or `Requested entity was not found`: the profile's Voice ID isn't valid for its TTS model (the seeded profiles use OpenAI voice names).
- Messages with a `NOTE:` explain the cause.

→ [Processing Issues → Podcast failures](processing-issues.md#podcast-failures)

---

## #9: Settings changes have no effect

You edited `.env` (not read by the container), or ran `docker compose restart` (keeps the old environment). Put the variable under `open_notebook` → `environment:` and run `docker compose up -d`. Check what the container sees:

```bash
# Names only, so no secrets end up on screen
docker compose exec open_notebook sh -c 'printenv | cut -d= -f1 | grep -E "OPEN_NOTEBOOK|API_URL|ESPERANTO"'
docker compose exec open_notebook printenv API_URL ESPERANTO_LLM_TIMEOUT   # values of non-secret settings
```

---

## #10: Ollama can't be reached

Test shows "Cannot connect to Ollama. Check if Ollama server is running." From Docker, the Base URL must be `http://host.docker.internal:11434` (Linux also needs `extra_hosts`), and on Linux Ollama must listen on `0.0.0.0`. That exposes its unauthenticated API on every interface, so allow port 11434 only from this host and its Docker networks. → [Ollama](../5-CONFIGURATION/ollama.md#which-base-url-to-use)

---

## #11: Slow first start or download timeouts

The published image has its Python dependencies installed. Downloads at startup happen only when `OPEN_NOTEBOOK_ENABLE_DOCLING` or `OPEN_NOTEBOOK_ENABLE_CRAWL4AI` is set; the log shows `[entrypoint] Installing ...`. On slow networks that first start can take a long time. If the install fails, the log says `[entrypoint] WARNING: ... install FAILED` and the app starts without that engine; restart to try again. The Python packages are installed with `uv`, so its standard variables work in the `open_notebook` environment: `UV_HTTP_TIMEOUT` (seconds per download) for slow connections, and `UV_DEFAULT_INDEX` to use a PyPI mirror (for example `https://pypi.tuna.tsinghua.edu.cn/simple` in mainland China).

---

## Resetting

- **Update:** `docker compose pull && docker compose up -d`. Back up first ([Advanced → Backup & Restore](../5-CONFIGURATION/advanced.md#backup--restore)).
- **Start from scratch:** `docker compose down`, then delete `./notebook_data` and `./surreal_data`. `docker compose down -v` does not delete them: they are bind mounts, not volumes.

---

## Still stuck?

- Look up your exact message in the [Troubleshooting index](index.md).
- Ask in [Discord](https://discord.gg/37XJPXfz2w) or [GitHub Discussions](https://github.com/lfnovo/open-notebook/discussions/categories/q-a).
