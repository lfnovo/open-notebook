# Troubleshooting

Find your problem by the message you see, then follow the link. If you don't have a message, start with [Quick Fixes](quick-fixes.md).

---

## By message

### In the browser

| Message | Where to look |
|---------|---------------|
| "Unable to Connect to API Server" | [Connection Issues](connection-issues.md#unable-to-connect-to-api-server) |
| "Unable to connect to server. Please check if the API is running." (login page) | [Connection Issues](connection-issues.md#unable-to-connect-to-api-server) |
| "Database Connection Failed" | [Connection Issues](connection-issues.md#database-connection-failed) |
| "Invalid password" | [Connection Issues → Login problems](connection-issues.md#login-problems) |
| "Encryption key not configured" | [AI & Chat Issues](ai-chat-issues.md#encryption-key-not-configured) |
| "Decryption Error" on a credential | [AI & Chat Issues](ai-chat-issues.md#decryption-error) |
| "Environment Variables Detected" | [AI & Chat Issues](ai-chat-issues.md#environment-variables-detected) |
| "No model configured for default for type=…" | [AI & Chat Issues](ai-chat-issues.md#no-model-configured-for-default-for-typechat) |
| "Model is not a LanguageModel: …" | [AI & Chat Issues](ai-chat-issues.md#model-is-not-a-languagemodel-) |
| "The AI provider took too long to respond…" | [AI & Chat Issues](ai-chat-issues.md#the-ai-provider-took-too-long-to-respond) |
| "Could not connect to the AI provider…" | [AI & Chat Issues](ai-chat-issues.md#could-not-connect-to-the-ai-provider-please-check-your-network-connection-and-provider-url) (on v1.15.0 this can also be a timeout) |
| "Authentication failed. Please check your API key…" | [AI & Chat Issues](ai-chat-issues.md#authentication-failed-please-check-your-api-key-in-settings---credentials) |
| "Rate limit exceeded…" | [AI & Chat Issues](ai-chat-issues.md#rate-limit-exceeded-please-wait-a-moment-and-try-again) |
| "Content too large for the selected model…" | [AI & Chat Issues](ai-chat-issues.md#content-too-large-for-the-selected-model) |
| "The AI provider is temporarily unavailable…" | [AI & Chat Issues](ai-chat-issues.md#the-ai-provider-is-temporarily-unavailable-please-try-again-in-a-few-minutes) |
| "The model returned an empty response…" | [AI & Chat Issues](ai-chat-issues.md#the-model-returned-an-empty-response-try-again-or-pick-a-different-model-if-this-keeps-happening) |
| "AI service error: …" | [AI & Chat Issues](ai-chat-issues.md#ai-service-error-) |
| "timeout of 600000ms exceeded" | [AI & Chat Issues](ai-chat-issues.md#timeout-of-600000ms-exceeded) |
| "Cannot connect to server. Check the URL is correct." (Test button) | [AI & Chat Issues → Test fails](ai-chat-issues.md#test-fails) |
| "Cannot connect to Ollama. Check if Ollama server is running." | [Ollama](../5-CONFIGURATION/ollama.md#troubleshooting) |
| "No models found from this provider" | [AI & Chat Issues](ai-chat-issues.md#no-models-found-from-this-provider) |
| Source stuck at "Queued" | [Processing Issues](processing-issues.md#sources-stay-queued-waiting-to-be-processed) |
| Source shows "Failed" | [Processing Issues → Failed sources](processing-issues.md#failed-sources) |
| "Request body exceeds the maximum allowed upload size" | [Processing Issues → Uploads](processing-issues.md#uploads-rejected) |
| "… (detected type: …)" on upload | [Processing Issues → Uploads](processing-issues.md#uploads-rejected) |
| "This feature requires an embedding model…" / "Vector search requires an embedding model…" | [Processing Issues → Search](processing-issues.md#search-and-ask) |
| "The strategy model returned no search terms…" (Ask) | [Processing Issues → Search](processing-issues.md#ask-fails-with-the-strategy-model-returned-no-search-terms-for-this-question) |
| "This source has no text content to transform" | [Processing Issues](processing-issues.md#this-source-has-no-text-content-to-transform) |
| Podcast episode "Failed" | [Processing Issues → Podcast failures](processing-issues.md#podcast-failures) |
| CORS error in the browser console | [Connection Issues](connection-issues.md#cors-errors-in-the-browser-console) |
| `502 Bad Gateway` / `504 Gateway Timeout` | [Reverse Proxy](../5-CONFIGURATION/reverse-proxy.md#troubleshooting) |

### In the logs

Read the logs with `docker compose logs open_notebook` (API, worker and frontend together) and `docker compose logs surrealdb`.

| Log line | Where to look |
|----------|---------------|
| `Database is not reachable yet (attempt n/12)` | [Connection Issues](connection-issues.md#database-connection-failed) |
| `OPEN_NOTEBOOK_ENCRYPTION_KEY not set. API key encryption will fail…` | [AI & Chat Issues](ai-chat-issues.md#encryption-key-not-configured) |
| `Failed to decrypt credential …` | [AI & Chat Issues](ai-chat-issues.md#decryption-error) |
| `content-core extraction failed (…)` | [Processing Issues → Failed sources](processing-issues.md#failed-sources) |
| `Configured … engine '…' is selected in Content Settings but its runtime is not available` | [Processing Issues](processing-issues.md#the-selected-engine-isnt-used) |
| `gave up: worker entered FATAL state` / `exited: worker` | [Processing Issues](processing-issues.md#sources-stay-queued-waiting-to-be-processed) |
| `[entrypoint] WARNING: ... install FAILED` | [Quick Fixes #11](quick-fixes.md#11-slow-first-start-or-download-timeouts) |
| `CORS_ORIGINS is not set — API accepts cross-origin requests from any origin` | A reminder, not an error. See [Security → CORS Origins](../5-CONFIGURATION/security.md#cors-origins) |
| `[SSL: CERTIFICATE_VERIFY_FAILED]` | [Connection Issues → SSL errors](connection-issues.md#ssl-errors-with-a-provider) |

---

## Guides

| Guide | Covers |
|-------|--------|
| [Quick Fixes](quick-fixes.md) | The most common problems, short answers |
| [Connection Issues](connection-issues.md) | The UI can't reach the API, the API can't reach the database, login, CORS, proxies |
| [AI & Chat Issues](ai-chat-issues.md) | Model setup, provider errors, timeouts, credentials and the encryption key, answer quality |
| [Processing Issues](processing-issues.md) | Queued and failed sources, uploads, search and embeddings, transformations, podcasts |
| [FAQ](faq.md) | Questions that aren't errors: data location, backups, costs, offline use |

---

## First checks

```bash
docker compose ps                                  # surrealdb and open_notebook both Up?
curl -s http://localhost:5055/health               # {"status":"healthy"}
curl -s http://localhost:5055/api/config           # "dbStatus": "online"
docker compose logs --since 10m open_notebook | grep -iE "error|warning|critical"
docker compose exec open_notebook printenv | grep -E "OPEN_NOTEBOOK|SURREAL|API_URL|ESPERANTO"
```

Settings belong under the `open_notebook` service's `environment:` block and take effect with `docker compose up -d`; `docker compose restart` keeps the old environment, and a variable that is only in `.env` doesn't reach the container. All variables: [Environment Reference](../5-CONFIGURATION/environment-reference.md).

---

## Getting help

1. Search [GitHub Issues](https://github.com/lfnovo/open-notebook/issues) for your exact message.
2. Ask in [Discord](https://discord.gg/37XJPXfz2w) or [GitHub Discussions](https://github.com/lfnovo/open-notebook/discussions/categories/q-a).
3. For a reproducible bug, open an issue with: the exact message, steps to reproduce, the relevant part of `docker compose logs open_notebook` (remove keys and passwords), your Open Notebook version, how you run it (Docker, single container, from source) and the provider you use.

Security problems: don't open a public issue, see [SECURITY.md](../../SECURITY.md).
