# Recursive Link Source Discovery — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in "Include linked pages" capability to the Add Source flow: scan a single URL for its links, let the user pick which ones via a checklist, and import each selected link as its own full Source alongside the original.

**Architecture:** A new read-only `POST /sources/discover-links` endpoint fetches the page via the existing content-core extraction (markdown), runs a pure link-extraction function, and returns candidate links. The frontend adds a checkbox + a conditional "Select Links" wizard step; on submit, the original URL plus the selected links flow through the existing per-URL batch-import path. The write/import path is untouched.

**Tech Stack:** Python 3.11/3.12, FastAPI, Pydantic v2, content-core, pytest (backend). Next.js 16 / React 19, TypeScript, TanStack Query, react-hook-form, Tailwind/shadcn, Vitest + Testing Library (frontend). i18next for translations.

**Spec:** [docs/superpowers/specs/2026-06-11-recursive-link-source-discovery-design.md](../specs/2026-06-11-recursive-link-source-discovery-design.md)

---

## File Structure

**Backend (create):**
- `open_notebook/utils/link_extraction.py` — pure `extract_links_from_markdown(markdown, base_url)` function. One responsibility: turn markdown + base URL into a deduped, filtered, domain-tagged list of link candidates. No I/O.
- `tests/test_link_extraction.py` — unit tests for the pure function.
- `tests/test_discover_links_api.py` — endpoint tests (content-core mocked).

**Backend (modify):**
- `api/models.py` — add `DiscoverLinksRequest`, `LinkCandidate`, `DiscoverLinksResponse` schemas.
- `api/routers/sources.py` — add `POST /sources/discover-links` endpoint.

**Frontend (create):**
- `frontend/src/components/sources/steps/SelectLinksStep.tsx` — the checklist step component.
- `frontend/src/components/sources/steps/SelectLinksStep.test.tsx` — component tests.

**Frontend (modify):**
- `frontend/src/lib/types/api.ts` — add `LinkCandidate`, `DiscoverLinksResponse` types.
- `frontend/src/lib/api/sources.ts` — add `discoverLinks(url)` API method.
- `frontend/src/lib/hooks/use-sources.ts` — add `useDiscoverLinks` query hook.
- `frontend/src/components/sources/steps/SourceTypeStep.tsx` — add the "Include linked pages" checkbox.
- `frontend/src/components/sources/AddSourceDialog.tsx` — dynamic step list, discovery state, include selected links in submit.
- `frontend/src/lib/locales/en-US/index.ts` — new translation keys (other locales fall back to `en-US` via `fallbackLng`).

---

## Task 1: Pure link-extraction function (backend)

**Files:**
- Create: `open_notebook/utils/link_extraction.py`
- Test: `tests/test_link_extraction.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_link_extraction.py`:

```python
"""Unit tests for markdown link extraction."""

from open_notebook.utils.link_extraction import extract_links_from_markdown


class TestExtractLinksFromMarkdown:
    def test_extracts_absolute_links(self):
        md = "See [Example](https://other.com/page) and [Home](https://example.com/home)."
        links = extract_links_from_markdown(md, "https://example.com/article")
        urls = [link["url"] for link in links]
        assert "https://other.com/page" in urls
        assert "https://example.com/home" in urls

    def test_resolves_relative_links_against_base(self):
        md = "[Docs](/docs/intro)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        assert links[0]["url"] == "https://example.com/docs/intro"

    def test_tags_same_domain(self):
        md = "[Internal](/x) [External](https://other.com/y)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        by_url = {link["url"]: link["same_domain"] for link in links}
        assert by_url["https://example.com/x"] is True
        assert by_url["https://other.com/y"] is False

    def test_drops_mailto_tel_javascript_and_anchors(self):
        md = "[m](mailto:a@b.com) [t](tel:123) [j](javascript:void(0)) [a](#section)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        assert links == []

    def test_dedupes_repeated_urls(self):
        md = "[a](https://example.com/x) [b](https://example.com/x)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        assert len(links) == 1

    def test_drops_fragment_and_excludes_base_url_itself(self):
        md = "[self](https://example.com/article#top) [self2](https://example.com/article)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        assert links == []

    def test_empty_or_none_markdown_returns_empty(self):
        assert extract_links_from_markdown("", "https://example.com") == []
        assert extract_links_from_markdown(None, "https://example.com") == []

    def test_malformed_markdown_does_not_raise(self):
        md = "[broken](  ) [no-close](https://example.com/x"
        links = extract_links_from_markdown(md, "https://example.com/article")
        # The unclosed link is not matched; result is a list (no exception)
        assert isinstance(links, list)

    def test_keeps_link_text(self):
        md = "[Click here](https://other.com/z)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        assert links[0]["text"] == "Click here"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_link_extraction.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'open_notebook.utils.link_extraction'`

- [ ] **Step 3: Write minimal implementation**

Create `open_notebook/utils/link_extraction.py`:

```python
"""Extract candidate links from extracted markdown content.

Pure function with no I/O: given the markdown a page was extracted into and the
URL it came from, return a deduped, filtered list of link candidates that the
user can choose to import as separate sources.
"""

import re
from typing import List, Optional, TypedDict
from urllib.parse import urljoin, urlparse

# Matches [text](url) and [text](url "title"); url has no whitespace.
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")

_SKIP_SCHEMES = {"mailto", "tel", "javascript"}


class LinkCandidate(TypedDict):
    url: str
    text: str
    same_domain: bool


def extract_links_from_markdown(
    markdown: Optional[str], base_url: str
) -> List[LinkCandidate]:
    if not markdown:
        return []

    base_host = urlparse(base_url).netloc.lower()
    base_key = base_url.split("#", 1)[0].rstrip("/")
    seen: set[str] = set()
    results: List[LinkCandidate] = []

    for match in _MARKDOWN_LINK_RE.finditer(markdown):
        text = match.group(1).strip()
        raw_url = match.group(2).strip()

        if not raw_url or raw_url.startswith("#"):
            continue
        if urlparse(raw_url).scheme.lower() in _SKIP_SCHEMES:
            continue

        absolute = urljoin(base_url, raw_url)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue

        normalized = parsed._replace(fragment="").geturl()
        if normalized.rstrip("/") == base_key:
            continue
        if normalized in seen:
            continue

        seen.add(normalized)
        results.append(
            LinkCandidate(
                url=normalized,
                text=text,
                same_domain=parsed.netloc.lower() == base_host,
            )
        )

    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_link_extraction.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add open_notebook/utils/link_extraction.py tests/test_link_extraction.py
git commit -m "feat(links): pure markdown link extraction utility"
```

---

## Task 2: Discovery endpoint + schemas (backend)

**Files:**
- Modify: `api/models.py` (add schemas near `SourceCreate`, around line 326)
- Modify: `api/routers/sources.py` (add endpoint after `create_source`)
- Test: `tests/test_discover_links_api.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_discover_links_api.py`:

```python
"""Tests for the POST /sources/discover-links endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestDiscoverLinks:
    @patch("api.routers.sources.extract_content", new_callable=AsyncMock)
    def test_returns_filtered_links(self, mock_extract, client):
        mock_extract.return_value = MagicMock(
            content="[Internal](/x) [External](https://other.com/y) [Mail](mailto:a@b.com)",
            title="Example Page",
        )

        response = client.post(
            "/api/sources/discover-links",
            json={"url": "https://example.com/article"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["source_url"] == "https://example.com/article"
        assert body["title"] == "Example Page"
        assert body["count"] == 2
        urls = [link["url"] for link in body["links"]]
        assert "https://example.com/x" in urls
        assert "https://other.com/y" in urls
        assert all("mailto" not in u for u in urls)

    @patch("api.routers.sources.extract_content", new_callable=AsyncMock)
    def test_empty_content_returns_zero_links(self, mock_extract, client):
        mock_extract.return_value = MagicMock(content="", title=None)

        response = client.post(
            "/api/sources/discover-links",
            json={"url": "https://example.com/article"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 0
        assert body["links"] == []

    @patch("api.routers.sources.extract_content", new_callable=AsyncMock)
    def test_fetch_failure_returns_error_status(self, mock_extract, client):
        mock_extract.side_effect = RuntimeError("network down")

        response = client.post(
            "/api/sources/discover-links",
            json={"url": "https://example.com/article"},
        )

        # ExternalServiceError maps to 502 via the global exception handlers
        assert response.status_code == 502
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_discover_links_api.py -v`
Expected: FAIL — `extract_content` is not yet imported in `api.routers.sources` (patch target missing) and the route returns 404/405.

- [ ] **Step 3a: Add the schemas to `api/models.py`**

Insert immediately after the `SourceCreate` class (after line 325, before `class SourceUpdate`):

```python
class DiscoverLinksRequest(BaseModel):
    url: str = Field(..., description="URL to scan for links")


class LinkCandidate(BaseModel):
    url: str = Field(..., description="Absolute, normalized link URL")
    text: str = Field("", description="Link anchor text")
    same_domain: bool = Field(
        ..., description="True if the link host matches the source URL host"
    )


class DiscoverLinksResponse(BaseModel):
    source_url: str = Field(..., description="The scanned URL")
    title: Optional[str] = Field(None, description="Extracted page title, if any")
    count: int = Field(..., description="Number of candidate links")
    links: List[LinkCandidate] = Field(
        default_factory=list, description="Candidate links found on the page"
    )
```

(`BaseModel`, `Field`, `Optional`, `List` are already imported in this file.)

- [ ] **Step 3b: Add imports + endpoint to `api/routers/sources.py`**

At the top of the file, add to the `content_core` / domain imports area. After the existing import block (after line 36, `from open_notebook.exceptions import InvalidInputError`), add:

```python
from content_core import extract_content

from api.models import (
    DiscoverLinksRequest,
    DiscoverLinksResponse,
    LinkCandidate,
)
from open_notebook.exceptions import ExternalServiceError
from open_notebook.utils.link_extraction import extract_links_from_markdown
```

Then add the endpoint immediately after the `create_source` function's closing (place it right before the `@router.get("/sources", ...)` `get_sources` definition, i.e. after line 159 in the original — anywhere at module top level in this router file is fine as long as it is after `router = APIRouter()`):

```python
@router.post("/sources/discover-links", response_model=DiscoverLinksResponse)
async def discover_links(request: DiscoverLinksRequest):
    """Fetch a URL and return the links it contains, for selective import.

    Read-only: creates no database records. Reuses content-core extraction so the
    preview matches what the real import would fetch.
    """
    url = request.url.strip()
    if not url:
        raise InvalidInputError("URL is required")

    content_state = {
        "url": url,
        "url_engine": "auto",
        "document_engine": "auto",
        "output_format": "markdown",
    }

    try:
        processed = await extract_content(content_state)
    except Exception as e:
        logger.error(f"Failed to fetch URL for link discovery: {e}")
        raise ExternalServiceError(f"Could not fetch the URL: {e}") from e

    markdown = processed.content or ""
    links = extract_links_from_markdown(markdown, url)

    return DiscoverLinksResponse(
        source_url=url,
        title=getattr(processed, "title", None),
        count=len(links),
        links=[LinkCandidate(**link) for link in links],
    )
```

> Note: define `discover-links` so it is registered as a distinct path from `POST /sources`. There is no conflicting `POST /sources/{id}` route, so ordering relative to `get_sources` does not matter.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_discover_links_api.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the full backend touchpoint to check nothing regressed**

Run: `uv run pytest tests/test_sources_api.py tests/test_link_extraction.py tests/test_discover_links_api.py -v`
Expected: PASS (all)

- [ ] **Step 6: Commit**

```bash
git add api/models.py api/routers/sources.py tests/test_discover_links_api.py
git commit -m "feat(api): add POST /sources/discover-links endpoint"
```

---

## Task 3: Frontend API types, client method, and hook

**Files:**
- Modify: `frontend/src/lib/types/api.ts` (after `CreateSourceRequest`, around line 112)
- Modify: `frontend/src/lib/api/sources.ts` (add method to `sourcesApi`)
- Modify: `frontend/src/lib/hooks/use-sources.ts` (add hook)

- [ ] **Step 1: Add types to `frontend/src/lib/types/api.ts`**

Insert after the `CreateSourceRequest` interface (after line 112):

```typescript
export interface LinkCandidate {
  url: string
  text: string
  same_domain: boolean
}

export interface DiscoverLinksResponse {
  source_url: string
  title?: string
  count: number
  links: LinkCandidate[]
}
```

- [ ] **Step 2: Add the API method to `frontend/src/lib/api/sources.ts`**

Add `DiscoverLinksResponse` to the type import block (lines 4-11):

```typescript
import {
  SourceListResponse,
  SourceDetailResponse,
  SourceResponse,
  SourceStatusResponse,
  CreateSourceRequest,
  UpdateSourceRequest,
  DiscoverLinksResponse,
} from '@/lib/types/api'
```

Add this method inside the `sourcesApi` object (e.g. after the `create` method, before `update`):

```typescript
  discoverLinks: async (url: string) => {
    const response = await apiClient.post<DiscoverLinksResponse>(
      '/sources/discover-links',
      { url }
    )
    return response.data
  },
```

- [ ] **Step 3: Add the hook to `frontend/src/lib/hooks/use-sources.ts`**

First, open the file to confirm the existing import style:

Run: `sed -n '1,20p' frontend/src/lib/hooks/use-sources.ts`

Then add a query hook. Ensure `useQuery` is imported from `@tanstack/react-query` (add it to the existing import if not present) and `sourcesApi` is imported from `@/lib/api/sources`. Append:

```typescript
export function useDiscoverLinks(url: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['discover-links', url],
    queryFn: () => sourcesApi.discoverLinks(url as string),
    enabled: enabled && !!url,
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}
```

- [ ] **Step 4: Verify it type-checks**

Run: `cd frontend && npx tsc --noEmit`
Expected: no new errors referencing `discoverLinks`, `DiscoverLinksResponse`, or `useDiscoverLinks`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/types/api.ts frontend/src/lib/api/sources.ts frontend/src/lib/hooks/use-sources.ts
git commit -m "feat(frontend): discover-links api type, client, and hook"
```

---

## Task 4: SelectLinksStep component

**Files:**
- Create: `frontend/src/components/sources/steps/SelectLinksStep.tsx`
- Test: `frontend/src/components/sources/steps/SelectLinksStep.test.tsx`

The component is **controlled**: the parent owns `selectedLinks: string[]` and passes `onSelectedChange`. The component owns the discovery fetch via `useDiscoverLinks`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/sources/steps/SelectLinksStep.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SelectLinksStep } from './SelectLinksStep'
import { useDiscoverLinks } from '@/lib/hooks/use-sources'

// useTranslation is mocked globally in setup.ts (t returns the key string)
vi.mock('@/lib/hooks/use-sources', () => ({
  useDiscoverLinks: vi.fn(),
}))

const mockHook = useDiscoverLinks as unknown as ReturnType<typeof vi.fn>

describe('SelectLinksStep', () => {
  beforeEach(() => {
    mockHook.mockReset()
  })

  it('shows a loading state while scanning', () => {
    mockHook.mockReturnValue({ data: undefined, isLoading: true, isError: false, refetch: vi.fn() })
    render(
      <SelectLinksStep sourceUrl="https://example.com" selectedLinks={[]} onSelectedChange={vi.fn()} onSkip={vi.fn()} />
    )
    expect(screen.getByText('sources.scanningLinks')).toBeInTheDocument()
  })

  it('renders an error with a skip action on failure', () => {
    const onSkip = vi.fn()
    mockHook.mockReturnValue({ data: undefined, isLoading: false, isError: true, refetch: vi.fn() })
    render(
      <SelectLinksStep sourceUrl="https://example.com" selectedLinks={[]} onSelectedChange={vi.fn()} onSkip={onSkip} />
    )
    expect(screen.getByText('sources.discoverLinksError')).toBeInTheDocument()
    fireEvent.click(screen.getByText('sources.skipImportOriginal'))
    expect(onSkip).toHaveBeenCalledTimes(1)
  })

  it('renders candidates and toggles selection', () => {
    const onSelectedChange = vi.fn()
    mockHook.mockReturnValue({
      data: {
        source_url: 'https://example.com',
        count: 2,
        links: [
          { url: 'https://example.com/a', text: 'A', same_domain: true },
          { url: 'https://other.com/b', text: 'B', same_domain: false },
        ],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    })
    render(
      <SelectLinksStep sourceUrl="https://example.com" selectedLinks={[]} onSelectedChange={onSelectedChange} onSkip={vi.fn()} />
    )
    // The link text is shown
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
    // Clicking "select all" selects both
    fireEvent.click(screen.getByText('sources.selectAll'))
    expect(onSelectedChange).toHaveBeenCalledWith([
      'https://example.com/a',
      'https://other.com/b',
    ])
  })

  it('select same-site chooses only same_domain links', () => {
    const onSelectedChange = vi.fn()
    mockHook.mockReturnValue({
      data: {
        source_url: 'https://example.com',
        count: 2,
        links: [
          { url: 'https://example.com/a', text: 'A', same_domain: true },
          { url: 'https://other.com/b', text: 'B', same_domain: false },
        ],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    })
    render(
      <SelectLinksStep sourceUrl="https://example.com" selectedLinks={[]} onSelectedChange={onSelectedChange} onSkip={vi.fn()} />
    )
    fireEvent.click(screen.getByText('sources.selectSameDomain'))
    expect(onSelectedChange).toHaveBeenCalledWith(['https://example.com/a'])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/sources/steps/SelectLinksStep.test.tsx`
Expected: FAIL — cannot resolve `./SelectLinksStep`.

- [ ] **Step 3: Write the component**

Create `frontend/src/components/sources/steps/SelectLinksStep.tsx`:

```typescript
"use client"

import { useTranslation } from "@/lib/hooks/use-translation"
import { useDiscoverLinks } from "@/lib/hooks/use-sources"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { FormSection } from "@/components/ui/form-section"
import { LoaderIcon } from "lucide-react"

interface SelectLinksStepProps {
  sourceUrl: string
  selectedLinks: string[]
  onSelectedChange: (urls: string[]) => void
  onSkip: () => void
}

export function SelectLinksStep({
  sourceUrl,
  selectedLinks,
  onSelectedChange,
  onSkip,
}: SelectLinksStepProps) {
  const { t } = useTranslation()
  const { data, isLoading, isError } = useDiscoverLinks(sourceUrl, true)

  const links = data?.links ?? []

  const toggle = (url: string) => {
    if (selectedLinks.includes(url)) {
      onSelectedChange(selectedLinks.filter((u) => u !== url))
    } else {
      onSelectedChange([...selectedLinks, url])
    }
  }

  const selectAll = () => onSelectedChange(links.map((l) => l.url))
  const selectNone = () => onSelectedChange([])
  const selectSameDomain = () =>
    onSelectedChange(links.filter((l) => l.same_domain).map((l) => l.url))

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 py-8">
        <LoaderIcon className="h-5 w-5 animate-spin text-primary" />
        <span className="text-sm text-muted-foreground">{t("sources.scanningLinks")}</span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="space-y-3 py-6">
        <p className="text-sm text-destructive">{t("sources.discoverLinksError")}</p>
        <Button type="button" variant="outline" onClick={onSkip}>
          {t("sources.skipImportOriginal")}
        </Button>
      </div>
    )
  }

  if (links.length === 0) {
    return (
      <div className="space-y-3 py-6">
        <p className="text-sm text-muted-foreground">{t("sources.noLinksFound")}</p>
      </div>
    )
  }

  return (
    <FormSection
      title={t("sources.selectLinks")}
      description={t("sources.selectLinksDescription")}
    >
      <div className="flex items-center justify-between mb-3">
        <Badge variant="secondary">
          {t("sources.linksFound").replace("{count}", links.length.toString())}
        </Badge>
        <div className="flex gap-2">
          <Button type="button" variant="ghost" size="sm" onClick={selectAll}>
            {t("sources.selectAll")}
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={selectSameDomain}>
            {t("sources.selectSameDomain")}
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={selectNone}>
            {t("sources.selectNone")}
          </Button>
        </div>
      </div>

      <ul className="space-y-2 max-h-72 overflow-y-auto">
        {links.map((link) => (
          <li key={link.url} className="flex items-start gap-3 rounded-md border p-2">
            <Checkbox
              checked={selectedLinks.includes(link.url)}
              onCheckedChange={() => toggle(link.url)}
              className="mt-1"
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium truncate">{link.text || link.url}</span>
                <Badge variant={link.same_domain ? "secondary" : "outline"} className="shrink-0">
                  {link.same_domain ? t("sources.sameDomainBadge") : t("sources.externalBadge")}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground truncate">{link.url}</p>
            </div>
          </li>
        ))}
      </ul>
    </FormSection>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/sources/steps/SelectLinksStep.test.tsx`
Expected: PASS (4 passed)

> If `@/components/ui/checkbox` exposes a different prop than `onCheckedChange`, open `frontend/src/components/ui/checkbox.tsx` and match its actual API. It is a standard shadcn Radix checkbox, so `checked` + `onCheckedChange` is expected.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/sources/steps/SelectLinksStep.tsx frontend/src/components/sources/steps/SelectLinksStep.test.tsx
git commit -m "feat(frontend): SelectLinksStep checklist component"
```

---

## Task 5: Translation keys (en-US)

**Files:**
- Modify: `frontend/src/lib/locales/en-US/index.ts`

Other locales fall back to `en-US` automatically (`fallbackLng: 'en-US'` in `frontend/src/lib/i18n.ts`), so only `en-US` is required for the feature to function. Translating the other 12 locales is a separate follow-up.

- [ ] **Step 1: Add keys inside the `sources` object**

Open `frontend/src/lib/locales/en-US/index.ts` and add these keys inside the `sources: { ... }` object (e.g. right after `urlsCount` near line 368). Match the existing trailing-comma style:

```typescript
    includeLinkedPages: "Include linked pages",
    includeLinkedPagesHint: "Scan this page for links and choose which to import as separate sources",
    selectLinks: "Select Links",
    selectLinksDescription: "Choose which linked pages to import as separate sources",
    scanningLinks: "Scanning page for links…",
    linksFound: "{count} link(s) found",
    noLinksFound: "No links found on this page. Only the original page will be imported.",
    selectAll: "Select all",
    selectNone: "Select none",
    selectSameDomain: "Select same-site",
    sameDomainBadge: "same site",
    externalBadge: "external",
    discoverLinksError: "Couldn't scan the page for links.",
    skipImportOriginal: "Skip — import original only",
    linkedPagesSelected: "{count} linked page(s) selected",
```

- [ ] **Step 2: Verify locale file still parses**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors in `en-US/index.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/locales/en-US/index.ts
git commit -m "feat(i18n): add link-discovery translation keys (en-US)"
```

---

## Task 6: Wire the checkbox into SourceTypeStep

**Files:**
- Modify: `frontend/src/components/sources/steps/SourceTypeStep.tsx`

The checkbox is parent-controlled (not part of react-hook-form). It appears only when type is `link` and exactly one URL is present.

- [ ] **Step 1: Extend the props interface**

In `SourceTypeStep.tsx`, add to `SourceTypeStepProps` (after `onClearUrlErrors?`):

```typescript
  includeLinkedPages?: boolean
  onToggleIncludeLinkedPages?: (checked: boolean) => void
```

Update the function signature destructuring to include them:

```typescript
export function SourceTypeStep({ control, register, setValue, errors, urlValidationErrors, onClearUrlErrors, includeLinkedPages, onToggleIncludeLinkedPages }: SourceTypeStepProps) {
```

- [ ] **Step 2: Import the Checkbox**

Add to the imports at the top of the file:

```typescript
import { Checkbox } from "@/components/ui/checkbox"
```

- [ ] **Step 3: Render the checkbox under the URL textarea**

Inside the `type.value === 'link'` block, immediately after the closing of the `batchUrlHint` paragraph (`</p>` on the line after line 210) and before the `{errors.url && ...}` block, insert:

```typescript
                      {urlCount === 1 && onToggleIncludeLinkedPages && (
                        <div className="mt-3 flex items-start gap-2">
                          <Checkbox
                            id="include-linked-pages"
                            checked={!!includeLinkedPages}
                            onCheckedChange={(checked) => onToggleIncludeLinkedPages(checked === true)}
                            className="mt-0.5"
                          />
                          <div>
                            <Label htmlFor="include-linked-pages" className="text-sm font-medium">
                              {t('sources.includeLinkedPages')}
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              {t('sources.includeLinkedPagesHint')}
                            </p>
                          </div>
                        </div>
                      )}
```

- [ ] **Step 4: Verify it type-checks**

Run: `cd frontend && npx tsc --noEmit`
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/sources/steps/SourceTypeStep.tsx
git commit -m "feat(frontend): include-linked-pages checkbox in source type step"
```

---

## Task 7: Wire dynamic step + import into AddSourceDialog

**Files:**
- Modify: `frontend/src/components/sources/AddSourceDialog.tsx`

This task makes the wizard step list dynamic, adds discovery selection state, and includes the selected links in the import. The dialog currently uses fixed step numbers 1-3; we convert to a key-based step list so a "Select Links" step can be inserted at position 2 when recursion is active.

- [ ] **Step 1: Add imports and state**

Add the import for the new step near the other step imports (after line 19):

```typescript
import { SelectLinksStep } from './steps/SelectLinksStep'
```

Add new state alongside the existing `useState` declarations (after line 112, the `batchProgress` state):

```typescript
  // Recursive link discovery state
  const [includeLinkedPages, setIncludeLinkedPages] = useState(false)
  const [selectedLinks, setSelectedLinks] = useState<string[]>([])
```

- [ ] **Step 2: Compute recursion mode and a dynamic step-key list**

Add right after the `isOverLimit` line (line 207):

```typescript
  // Recursion is single-URL only; disabled in batch mode.
  const recursionActive =
    selectedType === 'link' && includeLinkedPages && parsedUrls.length === 1

  // Dynamic step keys: insert "links" after "source" when recursion is active.
  type StepKey = 'source' | 'links' | 'notebooks' | 'process'
  const stepKeys: StepKey[] = recursionActive
    ? ['source', 'links', 'notebooks', 'process']
    : ['source', 'notebooks', 'process']
  const totalSteps = stepKeys.length
  const currentStepKey = stepKeys[currentStep - 1]
```

- [ ] **Step 3: Replace the static `WIZARD_STEPS` with a derived list**

Replace the existing `WIZARD_STEPS` declaration (lines 95-99) with:

```typescript
  const STEP_TITLES: Record<StepKey, { title: string; description: string }> = {
    source: { title: t('sources.addSource'), description: t('sources.processDescription') },
    links: { title: t('sources.selectLinks'), description: t('sources.selectLinksDescription') },
    notebooks: { title: t('navigation.notebooks'), description: t('notebooks.searchPlaceholder') },
    process: { title: t('navigation.process'), description: t('sources.processDescription') },
  }

  const WIZARD_STEPS: WizardStep[] = stepKeys.map((key, idx) => ({
    number: idx + 1,
    title: STEP_TITLES[key].title,
    description: STEP_TITLES[key].description,
  }))
```

> Note: `stepKeys` is computed in Step 2, which sits below this declaration in source order. Move the `recursionActive` / `stepKeys` / `currentStepKey` block (from Step 2) to **above** this `STEP_TITLES` block so the references resolve. They depend only on `selectedType`, `includeLinkedPages`, `parsedUrls`, and `currentStep`, all available at that point.

- [ ] **Step 4: Update step validation to be key-based**

Replace the `isStepValid` function (lines 210-243) with:

```typescript
  const isStepValid = (step: number): boolean => {
    const key = stepKeys[step - 1]
    switch (key) {
      case 'source':
        if (!selectedType) return false
        if (isOverLimit) return false
        if (urlValidationErrors.length > 0) return false
        if (selectedType === 'link') {
          if (isBatchMode) return parsedUrls.length > 0
          return !!watchedUrl && watchedUrl.trim() !== ''
        }
        if (selectedType === 'text') {
          return !!watchedContent && watchedContent.trim() !== '' &&
                 !!watchedTitle && watchedTitle.trim() !== ''
        }
        if (selectedType === 'upload') {
          if (watchedFile instanceof FileList) {
            return watchedFile.length > 0 && watchedFile.length <= MAX_BATCH_SIZE
          }
          return !!watchedFile
        }
        return true
      case 'links':
        // Always valid: selecting zero links just imports the original.
        return true
      case 'notebooks':
      case 'process':
        return true
      default:
        return false
    }
  }
```

- [ ] **Step 5: Update navigation bounds to use `totalSteps`**

In `handleNextStep` (lines 246-263), replace the condition `if (currentStep < 3 && isStepValid(currentStep))` with:

```typescript
    if (currentStep < totalSteps && isStepValid(currentStep)) {
      setCurrentStep(currentStep + 1)
    }
```

In `handleStepClick` (lines 278-282), the existing logic already uses `currentStep` relative checks and needs no bound change, but ensure it cannot jump past the last step — it already guards on `step <= currentStep || (step === currentStep + 1 && ...)`, which is safe.

- [ ] **Step 6: Build the import URL list and route recursion through batch submit**

Refactor `submitBatch` (lines 322-383) so it accepts an explicit URL list instead of always reading `parsedUrls`. Change the signature and the URL-collection block:

Replace line 323:

```typescript
  const submitBatch = async (
    data: CreateSourceFormData,
    urls: string[],
  ): Promise<{ success: number; failed: number }> => {
```

Replace the "Collect items to process" block (lines 327-332) with:

```typescript
    // Collect items to process
    if (data.type === 'link' && urls.length > 0) {
      urls.forEach(url => items.push({ type: 'url', value: url }))
    } else if (data.type === 'upload' && parsedFiles.length > 0) {
      parsedFiles.forEach(file => items.push({ type: 'file', value: file }))
    }
```

- [ ] **Step 7: Update `onSubmit` to choose the right path and URL list**

Replace the `onSubmit` body's branching (lines 386-422) with:

```typescript
  const onSubmit = async (data: CreateSourceFormData) => {
    try {
      setProcessing(true)

      const importUrls = recursionActive
        ? [parsedUrls[0], ...selectedLinks]
        : parsedUrls

      const useBatchPath = isBatchMode || (recursionActive && importUrls.length > 1)

      if (useBatchPath) {
        setProcessingStatus({ message: t('sources.processingFiles') })
        const results = await submitBatch(data, importUrls)

        if (results.failed === 0) {
          toast.success(t('sources.batchSuccess').replace('{count}', results.success.toString()))
        } else if (results.success === 0) {
          toast.error(t('sources.batchFailed').replace('{count}', results.failed.toString()))
        } else {
          toast.warning(t('sources.batchPartial').replace('{success}', results.success.toString()).replace('{failed}', results.failed.toString()))
        }

        handleClose()
      } else {
        setProcessingStatus({ message: t('sources.submittingSource') })
        await submitSingleSource(data)
        handleClose()
      }
    } catch (error) {
      console.error('Error creating source:', error)
      setProcessingStatus({
        message: t('common.error'),
      })
      timeoutRef.current = setTimeout(() => {
        setProcessing(false)
        setProcessingStatus(null)
        setBatchProgress(null)
      }, 3000)
    }
  }
```

- [ ] **Step 8: Reset the new state in `handleClose`**

In `handleClose` (after line 438, `setBatchProgress(null)`), add:

```typescript
    setIncludeLinkedPages(false)
    setSelectedLinks([])
```

- [ ] **Step 9: Render the dynamic steps**

Replace the step-rendering block (lines 552-584) with key-based rendering:

```typescript
            {currentStepKey === 'source' && (
              <SourceTypeStep
                // @ts-expect-error - Type inference issue with zod schema
                control={control}
                register={register}
                setValue={setValue}
                // @ts-expect-error - Type inference issue with zod schema
                errors={errors}
                urlValidationErrors={urlValidationErrors}
                onClearUrlErrors={handleClearUrlErrors}
                includeLinkedPages={includeLinkedPages}
                onToggleIncludeLinkedPages={setIncludeLinkedPages}
              />
            )}

            {currentStepKey === 'links' && (
              <SelectLinksStep
                sourceUrl={parsedUrls[0]}
                selectedLinks={selectedLinks}
                onSelectedChange={setSelectedLinks}
                onSkip={() => {
                  setSelectedLinks([])
                  setCurrentStep(currentStep + 1)
                }}
              />
            )}

            {currentStepKey === 'notebooks' && (
              <NotebooksStep
                notebooks={notebooks}
                selectedNotebooks={selectedNotebooks}
                onToggleNotebook={handleNotebookToggle}
                loading={notebooksLoading}
              />
            )}

            {currentStepKey === 'process' && (
              <ProcessingStep
                // @ts-expect-error - Type inference issue with zod schema
                control={control}
                transformations={transformations}
                selectedTransformations={selectedTransformations}
                onToggleTransformation={handleTransformationToggle}
                loading={transformationsLoading}
                settings={settings}
              />
            )}
```

- [ ] **Step 10: Update the Next/Done button bound**

In the navigation block, replace `{currentStep < 3 && (` (line 609) with:

```typescript
              {currentStep < totalSteps && (
```

- [ ] **Step 11: Type-check and run the existing frontend tests**

Run: `cd frontend && npx tsc --noEmit`
Expected: no new errors.

Run: `cd frontend && npx vitest run`
Expected: PASS (existing suite still green, including the new SelectLinksStep test).

- [ ] **Step 12: Commit**

```bash
git add frontend/src/components/sources/AddSourceDialog.tsx
git commit -m "feat(frontend): dynamic Select Links step and recursive import wiring"
```

---

## Task 8: End-to-end manual verification

**Files:** none (verification only)

- [ ] **Step 1: Start the stack**

Run: `dev.bat` (Windows) and wait for SurrealDB + API + worker + frontend to come up.

- [ ] **Step 2: Verify the discovery endpoint directly**

Run:
```bash
curl -s -X POST http://localhost:5055/api/sources/discover-links -H "Content-Type: application/json" -d "{\"url\": \"https://example.com\"}"
```
Expected: JSON with `source_url`, `title`, `count`, and a `links` array (each item has `url`, `text`, `same_domain`).

- [ ] **Step 3: Verify the UI flow**

1. Open the app, open **Add New Source**, choose **Add URL**, paste a single content-rich URL.
2. Confirm the **Include linked pages** checkbox appears; tick it.
3. Click **Next** → the **Select Links** step appears with a loading spinner, then the checklist.
4. Use **Select all** / **Select same-site** / **Select none**; pick a few links.
5. Click **Next** through **Notebooks** and **Process**, then **Done**.
6. Confirm the batch progress UI runs and the original + selected links appear as separate sources in the notebook.

- [ ] **Step 4: Verify the negative paths**

- Paste **two** URLs → the checkbox does not appear (batch mode), recursion disabled.
- Give a URL that yields no links → "No links found" message; importing brings in only the original.

- [ ] **Step 5: Final commit (if any verification fixups were needed)**

```bash
git add -A
git commit -m "fix: address link-discovery verification findings"
```

---

## Self-Review

- **Spec coverage:**
  - Discovery endpoint (read-only, no records) → Task 2. ✓
  - Pure link extraction (resolve/filter/dedup/tag) → Task 1. ✓
  - Followed links become separate full sources via existing import → Task 7 (`submitBatch` reuse). ✓
  - Depth = 1 (only the parent is scanned) → discovery scans only `sourceUrl`; no recursion of children. ✓
  - User picks links via checklist (select all / same-site / none) → Task 4. ✓
  - Single-URL only; checkbox hidden in batch → Task 6 (`urlCount === 1`) + Task 7 (`recursionActive` requires `parsedUrls.length === 1`). ✓
  - Error handling: fetch failure + skip, zero links → Task 4 (error/empty states), Task 2 (502). ✓
  - i18n keys → Task 5. ✓
  - Deferred items (markdown.new, cache, parent→child, dedup) → not implemented, by design. ✓
- **Placeholder scan:** no TBD/TODO; every code step shows full code. ✓
- **Type consistency:** `LinkCandidate` (`url`, `text`, `same_domain`) is consistent across Python schema (Task 2), TS type (Task 3), and component usage (Task 4). `DiscoverLinksResponse` fields (`source_url`, `title`, `count`, `links`) match between backend and frontend. `useDiscoverLinks(url, enabled)` signature matches its call in Task 4. `submitBatch(data, urls)` signature matches its call in Task 7. `stepKeys` / `currentStepKey` / `totalSteps` are defined once (Task 2) and used in Tasks 3-10. ✓
