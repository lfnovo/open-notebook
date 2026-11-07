# Content Processing Engines - Choosing How Content Is Extracted

When you add a source, Open Notebook extracts its text before chunking, embedding, and indexing it. How that extraction happens depends on the **processing engine**. You usually don't need to touch this — the defaults handle most content — but knowing your options helps when a document extracts poorly or a URL comes back empty.

Configure everything here in **Settings → Content Processing**.

> **Some engines are optional.** The default image stays lean, so the heavier
> **Docling** (layout + OCR + image sources) and **local Crawl4AI** (JavaScript
> rendering) engines are **opt-in** — you enable them with an environment
> variable and they install on first startup. Until then they appear **disabled**
> in Settings. See [Optional engines](#optional-engines-docling--crawl4ai) below.

---

## Where to Configure

```
Settings → Content Processing:
  - Document Processing Engine   (uploaded files)
  - URL Processing Engine        (web links)
  - Enable OCR                   (scanned PDFs and images, Docling only)
  - Extract formulas             (Docling only)
  - Describe images and charts   (Docling only)
```

Click **Save** after changing them. Changes apply to sources processed **after** saving. To re-extract an existing web link with the new settings, use **Refresh content** in its card menu; for a file, add it again (a failed source can also be reprocessed with **Retry Processing**).

---

## Document Processing Engines

Controls how uploaded files (PDF, Word, PowerPoint, EPUB, etc.) are turned into text.

| Engine | What it does | Trade-off |
|--------|--------------|-----------|
| **Auto (Recommended)** (default) | Tries Docling (when it's enabled) and falls back to simple extraction. | Balanced. Good default for almost everyone. |
| **Docling** | Layout-aware extraction: understands columns, tables, headings, and reading order. Runs OCR on scanned pages when OCR is enabled. **Optional — must be enabled** (see below). | Most accurate, but slower and heavier. |
| **Simple** | Fast, lightweight text extraction. Skips Docling entirely. | Fastest, but loses table structure and layout; no OCR. |

**When to pick each:**

- **Auto** — leave it here unless you have a reason not to.
- **Docling** — force it when tables, multi-column layouts, or scanned PDFs matter and Auto isn't giving you clean results. Requires Docling to be enabled.
- **Simple** — choose it for large batches of clean, text-native documents where speed matters more than layout fidelity.

---

## URL Processing Engines

Controls how web links are fetched and converted to text. Sites differ wildly — some are static HTML, others render everything with JavaScript, others sit behind anti-bot protection — so Open Notebook offers several engines with different capabilities.

| Engine | What it does | Needs |
|--------|--------------|-------|
| **Auto (Recommended)** (default) | Tries each engine in order until one succeeds (see chain below). | Nothing; uses whatever is configured. |
| **Firecrawl** | Managed scraping service. Handles JavaScript, anti-bot, and proxies well. | `FIRECRAWL_API_KEY` (or a self-hosted instance). |
| **Jina** | Jina AI Reader. Good at turning articles into clean text. | `JINA_API_KEY`. |
| **Crawl4AI** | Renders JavaScript pages in a local Chromium browser. No API key needed. **Optional — must be enabled** (see below). | `OPEN_NOTEBOOK_ENABLE_CRAWL4AI=true` (installs on first startup), or point at a remote server with `CRAWL4AI_API_URL`. |
| **Simple** | Basic HTTP fetch parsed with BeautifulSoup. | Nothing. |

### How the Auto fallback chain works

In Auto mode, Open Notebook tries engines in order and stops at the first that returns usable content:

```
Firecrawl  →  Jina  →  Crawl4AI  →  simple (bs4)
```

- Engines that aren't configured (e.g. no Firecrawl key) or aren't enabled (Crawl4AI) are skipped.
- Firecrawl and Jina are tried first because they handle difficult sites best.
- Crawl4AI catches JavaScript-heavy pages the API services miss, using local Chromium — **when it's enabled**.
- `simple` is the last resort — a plain HTTP request. It's fast and needs nothing, but **misses anything rendered by JavaScript**, so single-page apps and dynamic sites often come back empty or partial.

**When to force a specific engine:**

- **Firecrawl** / **Jina** — you have a key and want consistent, high-quality extraction without paying the local-rendering cost.
- **Crawl4AI** — a site needs a real browser (JavaScript-rendered content) but you'd rather not use a paid API. Requires Crawl4AI to be enabled.
- **Simple** — the site is plain HTML and you want the fastest, dependency-free path.

See the [Environment Reference](../5-CONFIGURATION/environment-reference.md#content-extraction) for the API keys and tuning variables (`FIRECRAWL_API_URL`, `CCORE_FIRECRAWL_PROXY`, `CCORE_FIRECRAWL_WAIT_FOR`, `CRAWL4AI_API_URL`, `CRAWL4AI_API_TOKEN`).

---

## OCR Toggle

**Settings → Content Processing → Enable OCR** (on by default, but only effective once Docling is enabled).

OCR reads text off images. It applies when the Docling engine handles:

- **Scanned PDFs** — pages that are images of text rather than real text.
- **Image sources** — PNG, JPEG, TIFF.

OCR only runs through Docling, so it does nothing until **Docling is enabled** (see below). With Docling off, the toggle is disabled in Settings and scanned PDFs fall back to plain text extraction (which yields little for image-only pages), while image sources are rejected as unsupported.

**Leave it on** if you work with scanned documents or images. **Turn it off** to speed up processing when all your documents are text-native — OCR adds overhead you don't need there.

---

## Formulas and Image Descriptions

Two more Docling options in **Settings → Content Processing**, both off by default:

- **Extract formulas** — keeps mathematical formulas as structured markup instead of garbled text. Adds processing time. Useful for math-heavy papers.
- **Describe images and charts** — uses a vision model to describe images and pull data out of charts, so that content becomes searchable text. Significantly slower, and may call a vision model.

Like OCR, both only take effect when Docling handles the document.

---

## Optional engines (Docling & Crawl4AI)

Docling and local Crawl4AI are heavy: Docling pulls a multi-hundred-MB to multi-GB machine-learning stack, and Crawl4AI bundles a Chromium browser. To keep the default image small, they are **not installed by default**. You opt in with an environment variable; the runtime is then installed automatically the **first time the container starts**, and the downloads are cached on your data volume so later restarts are fast.

| Enable this | To unlock |
|-------------|-----------|
| `OPEN_NOTEBOOK_ENABLE_DOCLING=true` | The Docling document engine, the OCR, formula and image-description toggles, and image sources (PNG/JPEG/TIFF). |
| `OPEN_NOTEBOOK_ENABLE_CRAWL4AI=true` | The local `crawl4ai` URL engine (JavaScript rendering via Chromium). |
| `CRAWL4AI_API_URL=…` | The `crawl4ai` engine against a **remote** Crawl4AI server — no local install needed. Add `CRAWL4AI_API_TOKEN=…` if the server requires a bearer token (Crawl4AI Docker ≥ 0.9.0 does by default). |

Notes:

- **First start is slower.** Enabling Docling downloads a large ML stack (several minutes on the first boot). Progress is logged loudly. Subsequent boots reuse the cache on the `/app/data` volume.
- **Degrade, don't die.** If the startup install fails (e.g. no network), the app still starts — the engine is simply reported unavailable and its option stays disabled in Settings.
- **The UI reflects reality.** Settings shows Docling/Crawl4AI/OCR as disabled until the runtime is actually installed and importable, so while a first-boot install is still running they correctly read "unavailable".
- **Offline / air-gapped deployments:** the startup install needs network access on first boot. If you can't reach PyPI, leave these disabled.

Set the variables the same way as any other Open Notebook environment variable (see the [Environment Reference](../5-CONFIGURATION/environment-reference.md) and your `docker-compose.yml`).

---

## Quick Reference

```
Document extracts poorly (tables, columns garbled)
  → Enable Docling, then set Document Processing Engine to "Docling"

Scanned PDF or image comes out blank
  → Enable Docling and Enable OCR (engine Auto or Docling)

Web link comes back empty or half-extracted
  → The site is likely JavaScript-heavy
  → In Auto mode, add a Firecrawl or Jina key, or enable Crawl4AI
  → Or choose "Crawl4AI" / "Firecrawl" as the URL Processing Engine

Processing feels slow on clean documents
  → Set Document Processing Engine to "Simple" and/or disable OCR
```

---

## Related

- [Adding Sources](adding-sources.md) — supported file types and step-by-step upload guide
- [Environment Reference](../5-CONFIGURATION/environment-reference.md) — extraction API keys and tuning variables
- [Advanced Configuration](../5-CONFIGURATION/advanced.md) — web scraping and content extraction setup
