"""
Pluggable web-search adapters for the "discover web sources" capability.

Design constraints are taken from upstream issue #973 ("[Design] Web research
agent / study-guide compiler for notebooks"):

* **No heavy direct dependencies** — only the standard library and ``httpx``,
  which the project already depends on. No ``duckduckgo-search`` or
  ``langchain-community``.
* **A thin HTTP adapter behind an abstract interface** — adding Brave, SearxNG,
  or Serper later is a new class implementing ``WebSearchProvider``, not a
  change to the API layer.
* **Credentials come from the environment** — never from the request body, and
  Docker-secrets aware through ``get_secret_from_env``.

Search returns *candidates* only. Fetching each page is deliberately left to
``content-core``, which already runs the fetch behind the normal source
processing pipeline once a candidate is ingested as a Source.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol, Sequence
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from loguru import logger

from open_notebook.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InvalidInputError,
)
from open_notebook.utils.encryption import get_secret_from_env
from open_notebook.utils.ssl_config import httpx_verify_setting

# Tavily is the first provider: a single REST call, no LLM round-trip. Its
# endpoint is fixed, so the adapter cannot be pointed at an internal address.
TAVILY_ENDPOINT = "https://api.tavily.com/search"
DEFAULT_PROVIDER = "tavily"
DEFAULT_TIMEOUT_SECONDS = 30.0

# Provider name -> environment variable holding its API key.
PROVIDER_ENV_VARS: Dict[str, str] = {
    "tavily": "TAVILY_API_KEY",
}

# Query-string keys that never change which document a URL points at. Dropped
# when normalizing, so the same page shared with different tracking parameters
# is recognized as one candidate (and not ingested twice).
TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "utm_name",
        "utm_reader",
        "fbclid",
        "gclid",
        "dclid",
        "msclkid",
        "yclid",
        "igshid",
        "mc_cid",
        "mc_eid",
        "_ga",
        "_gl",
        "ref",
        "ref_src",
        "ref_url",
        "source",
        "spm",
        "si",
        "__twitter_impression",
        "wt_mc",
        "at_medium",
        "at_campaign",
    }
)


def normalize_url(url: str) -> str:
    """Return a canonical URL: no fragment, no tracking params, no trailing slash.

    Used to de-duplicate search hits against the sources a notebook already
    contains, so re-running discovery does not create the same source twice.
    """
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return url.strip()

    kept = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            urlencode(sorted(kept)),
            "",
        )
    )


@dataclass(frozen=True)
class SearchResult:
    """A web page proposed as a future Source.

    Attributes:
        title: Page title as reported by the provider (may be empty).
        url: Absolute URL of the page.
        snippet: Short provider-supplied excerpt (may be empty).
        score: Provider relevance score; higher is better (0.0 when unknown).
        provider: Name of the provider that produced this hit.
    """

    title: str
    url: str
    snippet: str = ""
    score: float = 0.0
    provider: str = ""

    @property
    def normalized_url(self) -> str:
        """Return the canonical form used for de-duplication."""
        return normalize_url(self.url)


class WebSearchProvider(Protocol):
    """A web-search backend.

    Implementations must be stateless between calls and raise only the typed
    exceptions in ``open_notebook.exceptions`` so the API layer can map them to
    HTTP status codes without inspecting provider-specific errors.
    """

    name: str

    async def search(
        self,
        query: str,
        limit: int,
        *,
        exclude_domains: Sequence[str] = (),
    ) -> List[SearchResult]:
        """Return up to ``limit`` ranked results for ``query``."""
        ...


class TavilySearchProvider:
    """Tavily Search REST adapter (https://docs.tavily.com)."""

    name = "tavily"

    def __init__(self, api_key: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """Store the API key and the per-request timeout.

        Args:
            api_key: Tavily API key (see ``TAVILY_API_KEY``).
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key
        self._timeout = timeout

    async def search(
        self,
        query: str,
        limit: int,
        *,
        exclude_domains: Sequence[str] = (),
    ) -> List[SearchResult]:
        """Query the Tavily Search API and parse its results."""
        payload = {
            "query": query,
            "max_results": max(1, limit),
            "search_depth": "basic",
            "include_answer": False,
            "exclude_domains": [domain for domain in exclude_domains if domain],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(verify=httpx_verify_setting()) as client:
                response = await client.post(
                    TAVILY_ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=self._timeout,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (401, 403):
                raise ConfigurationError(
                    "The web search provider rejected the API key. "
                    f"Check {PROVIDER_ENV_VARS['tavily']}."
                ) from exc
            if status == 429:
                raise ExternalServiceError(
                    "The web search provider rate-limited the request; retry shortly."
                ) from exc
            raise ExternalServiceError(
                f"The web search provider returned HTTP {status}."
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceError(
                f"Could not reach the web search provider: {exc}"
            ) from exc

        return _parse_tavily_results(response.json())


def _parse_tavily_results(payload: dict) -> List[SearchResult]:
    """Convert a Tavily response body into ``SearchResult`` objects."""
    results: List[SearchResult] = []
    for item in payload.get("results") or []:
        url = (item.get("url") or "").strip()
        if not url:
            continue
        results.append(
            SearchResult(
                title=(item.get("title") or "").strip(),
                url=url,
                snippet=(item.get("content") or "").strip(),
                score=float(item.get("score") or 0.0),
                provider=DEFAULT_PROVIDER,
            )
        )
    return results


def resolve_api_key(provider: str) -> str:
    """Return a provider's API key from the environment.

    Args:
        provider: Provider name (key of ``PROVIDER_ENV_VARS``).

    Returns:
        The non-empty API key.

    Raises:
        ConfigurationError: If the provider is unknown or its key is not set.
    """
    env_var = PROVIDER_ENV_VARS.get(provider)
    if env_var is None:
        raise ConfigurationError(
            f"Unknown web search provider '{provider}'. "
            f"Available: {', '.join(sorted(PROVIDER_ENV_VARS))}."
        )

    value = get_secret_from_env(env_var)
    if not value or not value.strip():
        raise ConfigurationError(
            f"No web search API key configured. Set {env_var} to enable "
            f"'{provider}' discovery."
        )
    return value.strip()


def get_provider(name: Optional[str] = None) -> WebSearchProvider:
    """Resolve a search provider by name.

    Args:
        name: Provider name; defaults to ``DEFAULT_PROVIDER`` when omitted.

    Returns:
        A ready-to-use provider.

    Raises:
        ConfigurationError: If the provider is unknown or not configured.
    """
    resolved = (name or DEFAULT_PROVIDER).strip().lower()
    api_key = resolve_api_key(resolved)
    if resolved == "tavily":
        return TavilySearchProvider(api_key)
    raise ConfigurationError(  # pragma: no cover - guard for future providers
        f"Web search provider '{resolved}' is not implemented yet."
    )


async def search_web(
    query: str,
    limit: int = 5,
    *,
    provider: Optional[str] = None,
    exclude_domains: Sequence[str] = (),
) -> List[SearchResult]:
    """Search the web and return ranked candidates.

    Args:
        query: Free-text search query (must be non-empty).
        limit: Maximum number of results to return.
        provider: Provider name; defaults to ``DEFAULT_PROVIDER``.
        exclude_domains: Domains the provider must not return.

    Returns:
        Ranked search results (empty list when the provider finds nothing).

    Raises:
        InvalidInputError: If the query is empty.
        ConfigurationError: If the provider is unknown or not configured.
        ExternalServiceError: If the provider request fails.
    """
    cleaned = (query or "").strip()
    if not cleaned:
        raise InvalidInputError("Search query cannot be empty")

    backend = get_provider(provider)
    results = await backend.search(cleaned, limit, exclude_domains=exclude_domains)
    logger.info(
        f"Web search via {backend.name} for {cleaned!r} returned "
        f"{len(results)} candidate(s)"
    )
    return results
