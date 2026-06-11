# Recursive Link Source Discovery — Design

**Date:** 2026-06-11
**Status:** Approved for planning
**Scope:** v1 — link discovery + checklist + multi-source import

## Summary

Add an opt-in "Include linked pages" capability to the *Add New Source* flow. When a
user adds a single URL source and enables this option, the system fetches the page,
extracts the links it contains, and presents them as a checklist. The user selects which
linked pages to bring in; each selected link is imported as its own full `Source`
(identical to pasting the URL manually), alongside the original.

This is the first new feature of the SAI Notebook fork.

## Goals

- Let a user discover and selectively import the links found on a source page.
- Reuse the existing, proven source-import pipeline for the actual ingestion.
- Keep the discovery step read-only and side-effect free.

## Non-Goals (explicitly deferred)

- **Depth > 1** — no following links-of-links. One hop only.
- **`markdown.new` fallback engine** — URL→markdown already works today via content-core
  (`jina` / `firecrawl` / `simple` engines). A `markdown.new` fallback in our
  `content_process` node is a future follow-up, not part of v1.
- **Extraction cache** — discovery only fetches the *parent* page; selected child links
  are fetched once at import regardless, so a cross-process cache would only save the
  parent's second fetch. Modest payoff; accept the double-fetch of the parent in v1.
- **Parent→child source relationships** — followed links are flat, independent sources.
- **Dedup against existing notebook sources** — matches today's batch-import behavior.
- **Backend caps / domain filters** — the user curates manually via the checklist.

## How URL fetching works today (context)

Established during brainstorming, for implementer reference:

- Frontend `POST /sources` (multipart form, `type: "link"`, one `url`). Batch paste already
  exists but fires one independent request per URL, sequentially — the backend never knows
  the URLs are related. See [AddSourceDialog.tsx:322](../../../frontend/src/components/sources/AddSourceDialog.tsx#L322)
  and [SourceTypeStep.tsx:28](../../../frontend/src/components/sources/steps/SourceTypeStep.tsx#L28).
- API ([api/routers/sources.py:289](../../../api/routers/sources.py#L289)) creates a `Source`
  record immediately and submits a `process_source` job (async by default).
- The actual fetch is in the LangGraph `content_process` node
  ([open_notebook/graphs/source.py:34-94](../../../open_notebook/graphs/source.py#L34-L94)):
  ```python
  from content_core import extract_content
  content_state["url_engine"] = "auto"        # firecrawl | jina | simple
  content_state["document_engine"] = "auto"
  content_state["output_format"] = "markdown"
  processed_state = await extract_content(content_state)
  ```
  The returned `.content` (markdown) is stored as `source.full_text`, `.title` becomes the
  title, and `embed=True` kicks off a separate embedding job.
- There is **no** link extraction or recursion anywhere today; each URL is fetched in isolation.

## Architecture

```
┌─ Frontend (AddSourceDialog wizard) ────────────────────────────┐
│  [URL step] ──"Include linked pages"☑──▶ [Select Links step]    │
│       │ single URL only                       │ checklist        │
│       └───────────────┬────────────────────────┘                │
│                       ▼                                          │
│   import list = [original URL] + [selected links]                │
│                       │ existing batch submit (1 POST/source)    │
└───────────────────────┼──────────────────────────────────────────┘
                        ▼
┌─ API ──────────────────────────────────────────────────────────┐
│  NEW  POST /sources/discover-links   (read-only, no DB writes)  │
│        └─ content_core.extract_content(url, md) → markdown      │
│        └─ extract_links_from_markdown(md, base_url)  ◀ pure fn   │
│        └─ returns [{url, text, same_domain}]                    │
│  UNCHANGED  POST /sources  (each selected URL imported as today)│
└─────────────────────────────────────────────────────────────────┘
```

### Chosen approach

**Approach A — dedicated read-only discovery endpoint.** Discovery is a separate,
side-effect-free endpoint; the write/import path is left entirely untouched and reuses the
proven batch flow. Rejected alternatives: a "discover-only" flag bolted onto the source
graph (couples read logic into a workflow built for writes), and client-side link parsing
(CORS-blocked, no JS-rendering engine, preview wouldn't match backend extraction).

Trade-off accepted: the parent page is fetched twice (once for discovery, once at import).

## Components

Three new units, each independently testable.

### 1. `extract_links_from_markdown(markdown, base_url) -> list[LinkCandidate]`

Pure function, no I/O. Likely location: `open_notebook/utils/` (follow existing util
layout). Responsibilities:

- Parse markdown links: `[text](url)`.
- Resolve relative URLs against `base_url` via `urljoin`.
- Drop non-http(s) schemes (`mailto:`, `tel:`, `javascript:`), pure `#` anchors.
- Dedupe by normalized URL.
- Drop the parent/base URL itself.
- Tag each candidate `same_domain: bool` (host comparison against `base_url`).

`LinkCandidate` shape: `{ url: str, text: str, same_domain: bool }`.

### 2. `POST /sources/discover-links`

Read-only endpoint + thin service method (in `api/sources_service.py` or a focused new
module). Creates **no DB records**.

- **Request:** `{ "url": str }`
- **Flow:** call existing content-core extraction (`url_engine="auto"`,
  `output_format="markdown"`) → markdown; then `extract_links_from_markdown`.
- **Response:**
  ```json
  {
    "source_url": "https://...",
    "title": "Extracted page title or null",
    "count": 12,
    "links": [
      { "url": "https://...", "text": "link text", "same_domain": true }
    ]
  }
  ```
- **Errors:** fetch failure/timeout → 4xx/5xx with a message the frontend can show;
  empty link list is a valid 200 response with `count: 0`.

### 3. `SelectLinksStep` (React)

New wizard step component, shown only in single-URL mode when "Include linked pages" is on.

- On entry: call `discover-links`, show a loading state.
- Render checklist of candidates with controls: **select all**, **select all same-domain**,
  **select none**. Group/sort by same-domain vs external, show counts.
- On error: show the error with a **"Skip — import original only"** action.
- Selection state feeds the final import list.

## Data flow

1. User enters **one** URL, ticks "Include linked pages," clicks Next.
2. Frontend → `POST /sources/discover-links { url }`.
3. Backend fetches the parent page (content-core, markdown), runs the pure extractor,
   returns candidates.
4. "Select Links" step renders the checklist; user picks a subset.
5. User continues to the existing **Notebooks** and **Process** steps, unchanged.
6. On Done: import list = `[original] + [selected]` flows through the existing `submitBatch`
   path — one `POST /sources` per URL, fetched fresh. Existing progress UI shows
   success/failed counts.

## Scope rules & constraints

- **Single-URL only:** the recursion checkbox is hidden/disabled when the textarea contains
  more than one URL. Recursion and batch-paste are mutually exclusive in v1.
- **Depth = 1**, no links-of-links.
- **No backend cap or domain filter** — user curates via the checklist; backend only
  *presents* same-domain/external tagging.
- **No dedup** against existing notebook sources (matches current batch behavior).

## Error handling

- Discovery fetch fails/times out → error in the step + "Skip — import original only".
- Zero links found → friendly message, proceed with original only.
- Per-link import failures → already covered by the existing batch progress UI.

## Testing strategy

- **Unit (TDD-first):** `extract_links_from_markdown` — relative resolution, scheme/anchor
  filtering, dedup, same-domain tagging, malformed markdown, empty input, dropping the
  base URL itself.
- **API:** `discover-links` — happy path (content-core mocked), fetch failure, empty result.
- **Frontend:** `SelectLinksStep` — loading state, error→fallback path, the three
  select-all behaviors, selection feeding the import list.

## i18n

Per root CLAUDE.md, all new front-end strings get translation keys: checkbox label, step
title/description, loading text, error messages, and the select-all controls.

## Future follow-ups (out of scope)

- `markdown.new` fallback in `content_process` (after content-core failure).
- Cross-process extraction cache (SurrealDB `url_extract_cache` table, short TTL).
- Depth > 1 with cost controls and dedup.
- Parent→child source relationships for grouping/collapsing/tree-delete.
- Dedup followed links against sources already in the notebook.
