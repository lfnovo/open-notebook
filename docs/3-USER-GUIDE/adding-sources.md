# Adding Sources - Getting Content Into Your Notebook

Sources are the material the AI works with: files, web pages and pasted text. Every source goes through the same three-step **Add Source** wizard and is processed in the background.

---

## The Add Source Wizard

Open it from a notebook (**Add Source → Add Source**), from the **Sources** page (**New Source**), or from the sidebar (**New → Source**).

### Step 1: Add Source

Choose a tab:

- **Add URL**: paste a link. Paste several links, one per line, to import them in one go.
- **Upload File**: pick one file, or several to import them in one go.
- **Enter Text**: paste or type text. A **Title** is required for text.

For a single URL or file, the **Title** is optional; if you leave it empty, one is generated from the content. In batch mode (more than one URL or file) titles are always generated, and the same notebooks and transformations apply to every item. A batch can hold up to **50** URLs or files.

### Step 2: Notebooks

Pick the notebooks to link the source to (optional). Opened from a notebook, that notebook is already selected. A source can be linked to more notebooks later.

### Step 3: Process

- **Transformations (optional)**: transformations to run on the source after extraction. Each one produces an [insight](../2-CORE-CONCEPTS/notebooks-sources-notes.md#insights). Transformations marked *Suggest by default on new sources* are pre-selected (on a new install, that's **Dense Summary**). See [Transformations](transformations.md).
- **Enable embedding for search**: embeds the source so vector search and Ask can find it. Its default comes from **Settings → Embedding and Search → Default Embedding Option**: *Ask* shows this checkbox (checked), *Always* embeds without asking, *Never* skips embedding.

Click **Done**. You can click **Done** on any step to submit with the current choices.

---

## Supported Content

### Files

| Kind | Extensions |
|------|------------|
| Documents | PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, ODT, ODS, ODP, EPUB, TXT, MD, HTML, HTM |
| Audio | MP3, WAV, M4A, AAC |
| Video | MP4, AVI, MOV, WMV |
| Images | JPG, JPEG, PNG, TIFF (only when Docling is enabled; see [Content Processing Engines](content-processing-engines.md)) |

- **Audio and video are transcribed** with your **Speech-to-Text Model** (set in **Manage → Models → Default Model Assignments**). Without one, they can't be processed. For a local option, see [Local Speech-to-Text](../5-CONFIGURATION/local-stt.md).
- **Upload size** is limited to 100 MB by default. `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` raises the API's limit, but uploads through the web UI are also capped at 100 MB by the frontend.
- **Scanned PDFs** need Docling with OCR to give usable text.

### Web links

- **Articles and web pages**: fetched with the URL engine chosen in **Settings → Content Processing**. Pages that render with JavaScript may need Firecrawl, Jina or Crawl4AI; see [Content Processing Engines](content-processing-engines.md).
- **YouTube videos**: the transcript is imported. The preferred transcript languages are a setting reachable through the API (`youtube_preferred_languages` in `GET`/`PUT /api/settings`). If YouTube blocks your server, set `CCORE_YOUTUBE_PROXY` or `CCORE_YOUTUBE_COOKIES_FILE` for the worker ([Environment Reference](../5-CONFIGURATION/environment-reference.md)).
- **Pages behind a login or paywall** generally can't be fetched. Copy the text and use **Enter Text** instead.

### Text

Pasted text is processed like any other source (also in the background). Pasted HTML is converted to Markdown.

---

## Processing Status

A background job extracts the text, embeds it (if enabled) and runs the selected transformations. The source card shows:

| Status | Meaning |
|--------|---------|
| **Queued** | Waiting for the worker |
| **Processing** | Being processed (a progress bar may show) |
| **Completed** | Done; the status badge disappears and the card shows the number of insights, if any |
| **Failed** | Processing stopped; the card shows **Retry Processing** |

Sources are processed by the background worker. If sources stay **Queued** forever, the worker isn't running (`make worker-start` for source installs; it runs inside the Docker image automatically).

Transformations and embedding finish after the text is saved, so insights can appear a little after the source shows **Completed**.

---

## When a Source Fails

A failed source fails once: it is not retried automatically. The card shows *Source processing failed* and a **Retry Processing** button (also in the card's ⋮ menu).

The specific reason is stored with the job. You can read it in the worker log (which also has the underlying error) or from the API at `GET /api/sources/{source_id}/status` (the `processing_info.error` field). The UI does not show it yet. The reasons are:

| Message | What to do |
|---------|-----------|
| *The page was not found (it may have been removed or moved). Check the URL.* | Fix the link |
| *Could not reach this address (connection, timeout or DNS error). Check the URL and try again.* | Check the URL and your server's network access, then retry |
| *This URL or input is not valid.* | Fix the URL |
| *This file type is not supported.* | Convert the file to a supported format |
| *The file could not be read. It may be corrupted or in an unsupported format.* | Re-export or re-download the file |
| *Could not extract content from this YouTube video. No transcript or subtitles are available. ...* | The video has no transcript |
| *YouTube blocked or failed the transcript request. ...* | Set `CCORE_YOUTUBE_PROXY` or `CCORE_YOUTUBE_COOKIES_FILE` |
| *Content extraction is not configured correctly. ...* | Check the engine in **Settings → Content Processing** and your Speech-to-Text Model; the worker log has details |
| *The content extraction service failed.* / *Could not extract content from this source.* | Try another engine, or paste the text with **Enter Text** |

---

## Managing Sources

- **Open a source**: click its card for the Content, Insights and Details tabs. See [Interface Overview](interface-overview.md#the-source-view).
- **Add it to another notebook**: in that notebook, **Add Source → Add Existing Sources**, or from the source's Details tab, **Manage Notebooks**.
- **Remove from Notebook** (⋮ menu): unlinks the source from this notebook only.
- **Delete Source** (⋮ menu): deletes the source everywhere, with its insights, embeddings and uploaded file. This can't be undone.
- **Refresh content** (⋮ menu, completed links): fetches the page again and reprocesses it.
- **Embed Content** (source view ⋮ menu): embeds a source that was added without embedding.
- **Control what Chat sees**: the context icon on each card. See [Chat Effectively](chat-effectively.md#choosing-what-the-ai-sees).
