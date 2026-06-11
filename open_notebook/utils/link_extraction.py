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
