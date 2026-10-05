# Processing Issues - Sources, Search & Podcasts

Problems with background work: sources that don't finish, uploads that are rejected, search without results, podcasts that fail. Each entry starts with what you see.

All of this work runs in the **worker**, a background process. With Docker it runs inside the `open_notebook` container next to the API; from source you start it yourself with `make worker-start`.

---

## Sources stay "Queued" ("Waiting to be processed")

**Cause:** the worker isn't running, or it can't reach the job queue. Jobs are stored in the database and wait there until a worker picks them up. Embeddings, insights and podcasts wait the same way.

**From source:**

```bash
make status          # "Background Worker: ❌ Not running"?
make worker-start
```

**Docker:** the worker is started and restarted by supervisord inside the container. Check its state in the log:

```bash
docker compose logs open_notebook | grep -E "spawned: 'worker'|worker entered|exited: worker"
```

- `success: worker entered RUNNING state` → it's running; see the next check.
- `exited: worker` repeating, or `gave up: worker entered FATAL state` → it crashes on start. The lines just before show why; common causes are a wrong `SURREAL_*` setting and a failed first-start install of an optional runtime (`[entrypoint] WARNING: ... install FAILED`).

**Running but still nothing happens:** the API and the worker must use the same database. Make sure all five `SURREAL_*` variables are set explicitly (the shipped compose file does): the job queue falls back to namespace and database `test` when they're missing, while the API uses `open_notebook`. See [Database](../5-CONFIGURATION/database.md).

**Many sources at once:** the worker runs `OPEN_NOTEBOOK_WORKER_MAX_TASKS` jobs at a time (default 5); the rest stay Queued until a slot frees up. That's normal.

---

## Failed sources

**What you see:** the source card shows **Failed** ("Processing failed"). Open the card's menu and use **Retry Processing** to queue it again; a failed source is not retried automatically.

**Finding the reason:** the source card doesn't show why it failed. The reason is stored with the job and appears in two places:

```bash
# The worker log, with the full underlying error
docker compose logs open_notebook | grep -iE "content-core extraction failed|Source processing|process_source"

# The API: processing_info.error holds the reason shown in the table below
curl -s http://localhost:5055/api/sources/<source_id>/status
```

(Add `-H "Authorization: Bearer <password>"` if a password is set.) The source id is in the browser address bar when you open the source.

| Reason | Cause | Fix |
|--------|-------|-----|
| "Could not reach this address (connection, timeout or DNS error). Check the URL and try again." | The site is down, blocks the server, or the container has no internet access | Open the URL from the server (`docker compose exec open_notebook curl -I <url>`). Behind a corporate proxy, set `HTTP_PROXY`/`HTTPS_PROXY` |
| "The page was not found (it may have been removed or moved). Check the URL." | HTTP 404 | Fix the URL |
| "This URL or input is not valid." | Malformed URL or input | Check what you pasted |
| "Could not extract content from this YouTube video. No transcript or subtitles are available. Try configuring a Speech-to-Text model in Settings to transcribe the audio instead." | The video has no captions | Assign a **Speech-to-Text Model** in Manage → Models, then retry |
| "YouTube blocked or failed the transcript request. If this keeps happening, set CCORE_YOUTUBE_PROXY (a residential proxy) or CCORE_YOUTUBE_COOKIES_FILE for the worker." | YouTube blocks the server's IP (common on cloud hosts) | Set one of those variables in the `open_notebook` environment, `docker compose up -d`, retry. See [Environment Reference](../5-CONFIGURATION/environment-reference.md#content-extraction) |
| "This file type is not supported." | content-core has no extractor for the file | Convert the file (to PDF, DOCX, plain text…). Images need `OPEN_NOTEBOOK_ENABLE_DOCLING=true` |
| "The file could not be read. It may be corrupted or in an unsupported format." | Damaged, encrypted or mislabeled file | Re-export or re-download it |
| "Content extraction is not configured correctly. Check the content processing engine and speech-to-text settings; the worker log has the details." | Engine or speech-to-text misconfigured: missing API key for the chosen engine (Firecrawl), unreadable `CCORE_YOUTUBE_COOKIES_FILE`, a speech-to-text model that doesn't work | Read the worker log, then fix **Settings → Content Processing** or the Speech-to-Text Model |
| "The content extraction service failed." | An external service failed: Firecrawl, Jina, Crawl4AI or the speech-to-text provider | Check that service, or switch the engine to `auto` in **Settings → Content Processing** |
| "Could not extract any text content from this source. The content may be empty, inaccessible, or in an unsupported format." | Extraction worked but produced no text: a scanned PDF without OCR, a page rendered by JavaScript, a login wall | Enable Docling (OCR) for scans; use the Crawl4AI or Firecrawl engine for JavaScript pages |
| "Could not extract content from this source." | Any other extraction error | See the worker log |

These failures are final: retrying without changing anything fails the same way.

### The selected engine isn't used

The worker log shows `Configured url engine 'crawl4ai' is selected in Content Settings but its runtime is not available in this container; falling back to 'auto'. Set OPEN_NOTEBOOK_ENABLE_CRAWL4AI=true to enable it`. The engine is selected in Settings but its optional runtime isn't installed (or the install failed on startup). Set the variable it names, run `docker compose up -d`, and check the log for `[entrypoint]` lines. See [Content Processing Engines](../3-USER-GUIDE/content-processing-engines.md).

### Transcription of audio or video fails

See [Local Speech-to-Text → When transcription fails](../5-CONFIGURATION/local-stt.md#when-transcription-fails) for local servers. For cloud speech-to-text, check that a **Speech-to-Text Model** is assigned and its provider key works (**Test** in Manage → Models).

---

## Uploads rejected

### "Request body exceeds the maximum allowed upload size" (413)

The file is larger than `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` (default 100). Uploads through the UI are also capped at 100 MB by the frontend's proxy, whatever that variable says; larger files must be sent to the API on port 5055 directly. Behind a reverse proxy, its own body limit applies first and the browser may report a CORS error with status 413. See [Reverse Proxy → Upload size](../5-CONFIGURATION/reverse-proxy.md#upload-size-413-errors).

### "… (detected type: …)" (415)

The upload was rejected before processing because content-core can't extract that file type. The message names the reason and the detected type. Convert the file, or enable Docling for images and scanned documents.

---

## Search and Ask

### "This feature requires an embedding model. Please configure one in the Models section."

Also shown on the search page as "Vector search requires an embedding model. Only text search is available." No **Embedding Model** is assigned. Add one in Manage → Models (Discover Models with **Model Type** Embedding) and assign it under Default Model Assignments. Language-only providers such as Anthropic have no embedding models; add a second provider.

### Vector search finds nothing

- Sources added before you assigned an embedding model, or with embedding turned off, have no embeddings. Rebuild them from the **Advanced** page.
- After changing the embedding model, old and new vectors don't match. The Models page warns about this ("Important: Rebuild Required"); rebuild from the **Advanced** page.
- Check that the sources are **Completed**, not Queued or Failed.

### Ask fails with "The strategy model returned no search terms for this question."

The model chosen for the strategy step returned nothing usable, usually because a reasoning model spent its output budget on thinking. Pick a different strategy model in the Ask page's advanced model options, or rephrase the question. "The final answer model returned an empty response." has the same cause for the last step.

---

## Transformations and insights

### "This source has no text content to transform"

The source has no extracted text (it failed or is still processing). Fix the source first; see [Failed sources](#failed-sources).

### Insights never appear

Insights are created by a background job. If the source is Completed but its insights don't show up, check that the worker is running ([above](#sources-stay-queued-waiting-to-be-processed)). Model errors are covered in [AI & Chat Issues](ai-chat-issues.md).

---

## Podcast failures

A failed episode shows **Failed** with the error message on the episode card in **Podcasts → Episodes**, and a **Retry** button. Podcast generation is attempted once; use Retry after fixing the cause. When Open Notebook recognizes the error, the message ends with a `NOTE:` that explains it.

### Profile errors (generation stops before any model is called)

| Message | Fix |
|---------|-----|
| "Episode profile 'X' has no speaker profile configured. Please update the profile to select a speaker profile." | Edit the episode profile in **Podcasts → Profiles** and pick a speaker profile |
| "Episode profile 'X' references a speaker profile that no longer exists. Please update the profile to select a speaker profile." | The speaker profile was deleted; pick another |
| "Episode profile 'X' has no outline model configured. Please update the profile to select an outline model." (same for "transcript model") | Pick the models in the episode profile |
| "Speaker profile 'X' has no voice model configured. Please update the profile to select a voice model." | Edit the speaker profile and choose a text-to-speech model. The speaker profiles that ship with Open Notebook have no voice model until you set one |

If no text-to-speech model exists at all, the Models page shows "Not set — audio generation unavailable until configured" next to the Text-to-Speech Model. Add a provider with TTS (OpenAI, Google, ElevenLabs, MiniMax, a local [Speaches](../5-CONFIGURATION/local-tts.md) server…).

### Errors with a NOTE

| Error contains | What the NOTE explains | Fix |
|----------------|------------------------|-----|
| `Invalid speaker name` | The transcript model wrote a speaker name that isn't in the speaker profile, usually a placeholder such as `...` | Retry; each attempt is a fresh sample. If it repeats, use a stronger transcript model |
| `Voice name ... not supported` | The speaker profile's **Voice ID** isn't valid for its TTS model. The seeded profiles use OpenAI voice names (`alloy`, `nova`…) | Set voice ids your TTS provider offers |
| `Requested entity was not found` | Google's generic "not found": usually an OpenAI voice name sent to a Gemini voice model, otherwise a model id that doesn't exist | Fix the Voice ID, or the model in the episode profile. If the transcript finished and audio failed, it's the voice |
| `Invalid json output` or `Expecting value` | The outline or transcript response wasn't valid JSON: either truncated (podcast generation asks for up to 8192 output tokens per step unless the episode profile sets max tokens), or a reasoning model put everything inside `<think>` tags | Set max tokens to the model's limit or use fewer, shorter segments; or use a non-reasoning model for outline and transcript |

### Other podcast errors

- Timeouts on the outline or transcript step: see [AI & Chat Issues → timeouts](ai-chat-issues.md#the-ai-provider-took-too-long-to-respond).
- Audio fails part-way with a local or rate-limited TTS server: lower `TTS_BATCH_SIZE` and raise `ESPERANTO_TTS_TIMEOUT` ([Environment Reference](../5-CONFIGURATION/environment-reference.md#worker-and-background-jobs)).
- Episode stays Pending: the worker isn't running ([above](#sources-stay-queued-waiting-to-be-processed)).

More on podcast setup: [Creating Podcasts](../3-USER-GUIDE/creating-podcasts.md).

---

## Related

- [AI & Chat Issues](ai-chat-issues.md) — model, credential and timeout errors
- [Connection Issues](connection-issues.md) — UI, API and database connectivity
- [Environment Reference](../5-CONFIGURATION/environment-reference.md)
