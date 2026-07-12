# Content Processing Engines - Choosing How Content Is Extracted

When you add a source, Open Notebook extracts its text before chunking, embedding, and indexing it. How that extraction happens depends on the **processing engine**. You usually don't need to touch this — the defaults handle most content — but knowing your options helps when a document extracts poorly or a URL comes back empty.

Configure everything here in **Settings → Content Processing**.

---

## Where to Configure

```
Settings → Content Processing:
  - Document Processing Engine   (for uploaded files)
  - URL Processing Engine        (for web links)
  - Enable OCR                   (scanned PDFs and images)
```

Changes apply to sources you add **after** saving. Re-add a source if you want it re-extracted with a different engine.

---

## Document Processing Engines

Controls how uploaded files (PDF, Word, PowerPoint, EPUB, etc.) are turned into text.

| Engine | What it does | Trade-off |
|--------|--------------|-----------|
| **auto** (default) | Picks the best engine for the file type. Uses Docling for complex documents, simple extraction for the rest. | Balanced. Good default for almost everyone. |
| **docling** | Layout-aware extraction: understands columns, tables, headings, and reading order. Runs OCR on scanned pages when OCR is enabled. | Most accurate, but slower and heavier. |
| **simple** | Fast, lightweight text extraction. Skips Docling entirely. | Fastest, but loses table structure and layout; no OCR. |

**When to pick each:**

- **auto** — leave it here unless you have a reason not to.
- **docling** — force it when tables, multi-column layouts, or scanned PDFs matter and `auto` isn't giving you clean results.
- **simple** — choose it for large batches of clean, text-native documents where speed matters more than layout fidelity.

---

## URL Processing Engines

Controls how web links are fetched and converted to text. Sites differ wildly — some are static HTML, others render everything with JavaScript, others sit behind anti-bot protection — so Open Notebook offers several engines with different capabilities.

| Engine | What it does | Needs |
|--------|--------------|-------|
| **auto** (default) | Tries each engine in order until one succeeds (see chain below). | Nothing; uses whatever is configured. |
| **firecrawl** | Managed scraping service. Handles JavaScript, anti-bot, and proxies well. | `FIRECRAWL_API_KEY` (or a self-hosted instance). |
| **jina** | Jina AI Reader. Good at turning articles into clean text. | `JINA_API_KEY`. |
| **crawl4ai** | Renders JavaScript pages locally in a bundled Chromium browser. No API key needed. | Bundled in the Docker image; or point at a remote server with `CRAWL4AI_API_URL`. |
| **simple** | Basic HTTP fetch parsed with BeautifulSoup. | Nothing. |

### How the `auto` fallback chain works

In `auto` mode, Open Notebook tries engines in order and stops at the first that returns usable content:

```
Firecrawl  →  Jina  →  Crawl4AI  →  simple (bs4)
```

- Engines that aren't configured (e.g. no Firecrawl key) are skipped.
- Firecrawl and Jina are tried first because they handle difficult sites best.
- Crawl4AI catches JavaScript-heavy pages the API services miss, using local Chromium.
- `simple` is the last resort — a plain HTTP request. It's fast and needs nothing, but **misses anything rendered by JavaScript**, so single-page apps and dynamic sites often come back empty or partial.

**When to force a specific engine:**

- **firecrawl** / **jina** — you have a key and want consistent, high-quality extraction without paying the local-rendering cost.
- **crawl4ai** — a site needs a real browser (JavaScript-rendered content) but you'd rather not use a paid API.
- **simple** — the site is plain HTML and you want the fastest, dependency-free path.

See the [Environment Reference](../5-CONFIGURATION/environment-reference.md#content-extraction) for the API keys and tuning variables (`FIRECRAWL_API_URL`, `CCORE_FIRECRAWL_PROXY`, `CCORE_FIRECRAWL_WAIT_FOR`, `CRAWL4AI_API_URL`).

---

## OCR Toggle

**Settings → Content Processing → Enable OCR** (on by default).

OCR reads text off images. It applies when the Docling engine handles:

- **Scanned PDFs** — pages that are images of text rather than real text.
- **Image sources** — PNG, JPEG, TIFF, BMP.

**Leave it on** if you work with scanned documents or images. **Turn it off** to speed up processing when all your documents are text-native — OCR adds overhead you don't need there.

OCR only runs through Docling. If you set the Document Processing Engine to `simple`, OCR is skipped regardless of this toggle.

---

## Quick Reference

```
Document extracts poorly (tables, columns garbled)
  → Set Document Engine to "docling"

Scanned PDF or image comes out blank
  → Enable OCR (and make sure the engine is auto or docling)

Web link comes back empty or half-extracted
  → The site is likely JavaScript-heavy
  → In auto mode, add a Firecrawl or Jina key, or rely on bundled Crawl4AI
  → Or force "crawl4ai" / "firecrawl"

Processing feels slow on clean documents
  → Set Document Engine to "simple" and/or disable OCR
```

---

## Related

- [Adding Sources](adding-sources.md) — supported file types and step-by-step upload guide
- [Environment Reference](../5-CONFIGURATION/environment-reference.md) — extraction API keys and tuning variables
- [Advanced Configuration](../5-CONFIGURATION/advanced.md) — web scraping and content extraction setup
