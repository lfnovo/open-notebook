# AI & Chat Issues - Models, Credentials & Errors

Errors from AI providers, model setup and the credential system. Each entry starts with the message you see; in chat it appears as a red notification, in background jobs (insights, transformations, podcasts) in the job's error.

Background jobs retry transient provider errors (rate limits, provider outages) a few times on their own; configuration errors, oversized content and empty answers are not retried. Chat and Ask don't retry: send the message again.

---

## Model setup

### "No model configured for default for type=chat"

Full message: `No model configured for default for type=chat. Please go to Manage → Models and configure a default model for 'chat'.` The type can also be `transformation`, `tools` or another role.

**Cause:** no model is assigned to that role. A fresh install has none.

**Fix:** **Manage → Models → Default Model Assignments**: choose a model for each role, or click **Auto-assign Defaults**. If the lists are empty, you haven't registered models yet: follow [Connect a provider](../4-AI-PROVIDERS/index.md#connect-a-provider).

### "Model is not a LanguageModel: …"

Full message: `Model is not a LanguageModel: <model>. Please check that the model configured for '<role>' is a language model, not an embedding or speech model.`

**Cause:** an embedding, text-to-speech or speech-to-text model is assigned to a language role (Chat, Transformation, Tools or Large Context Model). This happens when a model was registered under the wrong **Model Type**.

**Fix:** assign a language model to that role. If a model is registered with the wrong type, delete it in Manage → Models and add it again with the right Model Type.

### A model that worked now fails with "model not found" or "does not exist"

The model was removed from the provider (retired, or deleted from Ollama). Discover Models on the configuration to see what is available now, add a replacement, and re-assign the defaults that used the old one.

---

## Provider errors

### "The AI provider took too long to respond"

Full message: `The AI provider took too long to respond. Try again, use a faster model, or raise ESPERANTO_LLM_TIMEOUT (180 seconds by default).`

v1.15.0 shows `Could not connect to the AI provider. Please check your network connection and provider URL.` for this same timeout; if that message appears after a long wait rather than immediately, it is a timeout.

**Cause:** one model call took longer than `ESPERANTO_LLM_TIMEOUT` (180 seconds by default, applied to every provider including Ollama). Typical with large local models on CPU, the first request while a model loads, very large contexts, or reasoning models that think for minutes.

**Fix:**

1. Try a faster model, or include less content (see [Content too large](#content-too-large-for-the-selected-model)).
2. Raise the limit in the `open_notebook` service and apply with `docker compose up -d` (`restart` keeps the old value):
   ```yaml
   environment:
     - ESPERANTO_LLM_TIMEOUT=420   # keep below 600
   ```
   Stay below 600 seconds: the web UI stops waiting after 10 minutes, and that limit can't be changed on the published image.
3. With one local GPU, also set `OPEN_NOTEBOOK_WORKER_MAX_TASKS=1` so background jobs don't compete for it.

More for Ollama: [Ollama → Timeouts](../5-CONFIGURATION/ollama.md#timeouts-with-slow-models).

### "timeout of 600000ms exceeded"

The browser gave up after 10 minutes. Something is slower than the UI allows, usually because `ESPERANTO_LLM_TIMEOUT` was raised above 600 or a reverse proxy holds the request. Lower `ESPERANTO_LLM_TIMEOUT` below 600 so the server fails first with a clear message, and check proxy timeouts ([Reverse Proxy → Timeouts](../5-CONFIGURATION/reverse-proxy.md#timeouts)).

### "Could not connect to the AI provider. Please check your network connection and provider URL."

Shown immediately (not after a long wait), the provider can't be reached at all.

- Local servers (Ollama, LM Studio, Speaches): the configuration's **Base URL** must be reachable from inside the container. `localhost` there is the container itself; use `host.docker.internal` or the compose service name. See [Ollama](../5-CONFIGURATION/ollama.md#which-base-url-to-use) and [OpenAI-Compatible](../5-CONFIGURATION/openai-compatible.md#base-url-from-inside-docker).
- Cloud providers: the server has no internet access, or needs `HTTP_PROXY`/`HTTPS_PROXY` ([Environment Reference](../5-CONFIGURATION/environment-reference.md#outbound-proxy)).
- Self-signed HTTPS endpoint: set `ESPERANTO_SSL_CA_BUNDLE` ([Advanced → SSL](../5-CONFIGURATION/advanced.md#ssl-for-self-signed-providers)).

The **Test** button on the configuration gives a more specific reason ("Cannot connect to server. Check the URL is correct.", "Connection timed out. Check if server is accessible.").

### "Authentication failed. Please check your API key in Manage -> Models."

**Cause:** the provider rejected the key (wrong, revoked, or for another region or project). v1.15.0 shows the same message with the outdated path "Settings -> Credentials".

**Fix:** in Manage → Models, click **Test** on the provider's configuration. If it reports "Invalid API key", create a new key with the provider and edit the configuration (leave the key field blank to keep the old one; type a new one to replace it). For MiniMax and SiliconFlow, check that the key's region matches the **Base URL** ([AI Providers](../5-CONFIGURATION/ai-providers.md#minimax)).

### "Rate limit exceeded. Please wait a moment and try again."

The provider returned HTTP 429: too many requests, or the account is out of quota or credit. Wait and retry, check the account's billing, or lower `OPEN_NOTEBOOK_WORKER_MAX_TASKS` so bulk processing sends fewer requests at once.

### "Content too large for the selected model"

Full message: `Content too large for the selected model. Try using a smaller selection or a model with a larger context window.`

**Cause:** the prompt (sources in context plus chat history) exceeds the model's context window.

**Fix:**

- In notebook chat, include fewer sources, or switch them from "Full content" to "Insights only".
- Use a model with a larger window. Open Notebook switches to the **Large Context Model** automatically when the content exceeds about 105,000 tokens, so assign a model with a large window to that role under Default Model Assignments.
- Start a new chat session to drop a long history.

**Ollama doesn't report this error.** When a prompt exceeds the credential's **Context Window (num_ctx)** (8192 tokens by default), Ollama silently drops the start of the prompt. Answers then ignore your sources or earlier messages. Raise **Context Window (num_ctx)** on the Ollama configuration in Manage → Models if your hardware allows; see [Ollama → Context window](../5-CONFIGURATION/ollama.md#context-window-num_ctx).

### "The request payload is too large for the AI provider"

The provider rejected the request size (HTTP 413). Reduce the content, as above, or use a provider with larger limits.

### "The AI provider is temporarily unavailable. Please try again in a few minutes."

The provider returned a server error (500, 502, 503 or "overloaded"). Wait and retry, or switch to another model or provider. Check the provider's status page.

### "AI service error: …"

An error Open Notebook doesn't recognize; the rest of the message is the provider's own text (shortened). It usually names the problem (unsupported parameter, content policy, model access). The full error is in the log: `docker compose logs open_notebook | grep -i "Unclassified LLM error"`.

### "The model returned an empty response. Try again, or pick a different model if this keeps happening."

The model answered with no text. Common with reasoning models that use their whole output budget on thinking, or models with a small output limit. Retry, or choose a non-reasoning model for that role. In Ask, the same problem appears as "The strategy model returned no search terms for this question" or "The final answer model returned an empty response"; pick other models in the Ask page's advanced model options.

---

## Credentials and encryption

### "Encryption key not configured"

Shown in **Manage → Models** and as a banner: "Set the OPEN_NOTEBOOK_ENCRYPTION_KEY environment variable…". Saving a credential fails with `Encryption key not configured. Set OPEN_NOTEBOOK_ENCRYPTION_KEY to enable storing API keys.`, and the API log shows `OPEN_NOTEBOOK_ENCRYPTION_KEY not set. API key encryption will fail until this is configured.`

**Fix:** add the key to the `open_notebook` service and run `docker compose up -d`:

```yaml
environment:
  - OPEN_NOTEBOOK_ENCRYPTION_KEY=<generated-key>
```

Generate the value yourself, for example with `openssl rand -hex 32` (on Windows, see [Set your encryption key](../1-INSTALLATION/docker-compose.md#step-2-set-your-encryption-key)). Don't reuse an example value.

If you set it only in `.env`, it never reaches the container: the shipped compose file doesn't load `.env` into it. Don't keep the `change-me-to-a-secret-string` placeholder. See [Security](../5-CONFIGURATION/security.md#api-key-encryption).

### "Decryption Error"

On a credential in Manage → Models: "This credential's API key could not be decrypted. The encryption key may have changed. Delete this credential and re-create it with the correct key." The API log shows `Failed to decrypt credential <id>: Decryption failed: ...`.

**Cause:** `OPEN_NOTEBOOK_ENCRYPTION_KEY` is not the value the credential was saved with. Common reasons: the key was changed, a new container was created without it (for example a different compose file or a typo), or the database was restored onto an instance with another key.

**Fix:** if you still have the old key, put it back and run `docker compose up -d`; the credentials work again. Otherwise delete each affected credential and add it again. Test, Models and Edit are disabled on a credential in this state.

Credentials saved by v1.15.0 or later can't be read by older versions either. After a downgrade, restore the backup taken before the upgrade ([Security → Upgrading to PBKDF2](../5-CONFIGURATION/security.md#upgrading-to-pbkdf2-v1150)).

### "Environment Variables Detected"

Provider keys are set as environment variables (`OPENAI_API_KEY` and so on). They still work as a fallback, but **Migrate to Database** turns them into regular credentials. Afterwards, remove the variables from your configuration. See [Environment Reference → Legacy](../5-CONFIGURATION/environment-reference.md#legacy-ai-provider-variables-deprecated).

### Test fails

| Message | Meaning |
|---------|---------|
| "Invalid API key" | The provider rejected the key |
| "API key lacks required permissions" | The key is valid but can't list or use models (restricted key, project permissions) |
| "Model not found on this provider" | The test model isn't available to this key; Discover Models still shows what is |
| "Cannot connect to server. Check the URL is correct." | Nothing reachable at the Base URL, or TLS verification failed |
| "Cannot connect to Ollama. Check if Ollama server is running." | See [Ollama troubleshooting](../5-CONFIGURATION/ollama.md#troubleshooting) |
| "Connection timed out. Check if server is accessible." | Firewall, wrong address, or a busy server |

### "No models found from this provider"

Discover Models returned an empty list. Local servers: load or pull a model first. Gateways and compatible servers that don't list models: type the model id in the search box and click **Add "…"**.

---

## Answer quality

These aren't errors, but they are the most common complaints.

- **Answers ignore my sources.** In notebook chat, each source card has a context setting that cycles between "Not included in chat", "Insights only" and "Full content". Check that the sources you care about are included. With Ollama, also check [the context window](../5-CONFIGURATION/ollama.md#context-window-num_ctx).
- **"Insights only" gives shallow answers.** It sends the source's insights, not its text. Use "Full content" for the sources the question is about.
- **Generic or wrong answers.** Ask specific questions that name the source or section, and use a stronger model for the Chat Model role. Check the citations: they show which sources the answer used.
- **Ask can't find something that is there.** Ask searches the embeddings; sources without embeddings aren't found. See [Processing Issues → Search](processing-issues.md#search-and-ask).

More: [Chat Effectively](../3-USER-GUIDE/chat-effectively.md).

---

## Related

- [AI Providers](../5-CONFIGURATION/ai-providers.md) — setup for each provider
- [Processing Issues](processing-issues.md) — sources, search, podcasts
- [Connection Issues](connection-issues.md) — UI, API and database
- [Environment Reference](../5-CONFIGURATION/environment-reference.md)
