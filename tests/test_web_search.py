"""
Tests for the pluggable web-search adapters
(open_notebook.research.web_search).

These lock the contract of the "discover web sources" capability (issue #973):
provider errors surface as typed exceptions the API layer can map to HTTP
status codes, credentials come only from the environment, and URLs are
normalized so the same page is de-duplicated across runs.
"""

import httpx
import pytest

from open_notebook.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InvalidInputError,
)
from open_notebook.research import web_search


class _FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.request = httpx.Request("POST", web_search.TAVILY_ENDPOINT)

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", web_search.TAVILY_ENDPOINT)
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=request, response=response
            )


class _FakeAsyncClient:
    """Stands in for httpx.AsyncClient, recording the outgoing call."""

    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def post(self, url: str, **kwargs: object) -> _FakeResponse:
        self.calls.append((url, kwargs))
        return self._response


def _patch_client(monkeypatch, response: _FakeResponse) -> _FakeAsyncClient:
    fake = _FakeAsyncClient(response)
    # The adapter builds it as AsyncClient(verify=...), so accept **kwargs.
    monkeypatch.setattr(web_search.httpx, "AsyncClient", lambda **kwargs: fake)
    return fake


class TestNormalizeUrl:
    def test_strips_tracking_params_fragment_and_lowercases_host(self):
        raw = "HTTPS://Example.com/Path/?utm_source=x&b=2&a=1#frag"
        assert web_search.normalize_url(raw) == "https://example.com/Path?a=1&b=2"

    def test_drops_trailing_slash_but_keeps_root(self):
        assert web_search.normalize_url("https://e.com/docs/") == "https://e.com/docs"
        assert web_search.normalize_url("https://e.com") == "https://e.com/"

    def test_untracked_query_params_are_preserved_and_sorted(self):
        assert (
            web_search.normalize_url("https://e.com/s?z=1&a=2")
            == "https://e.com/s?a=2&z=1"
        )


class TestSearchResult:
    def test_normalized_url_uses_the_shared_normalizer(self):
        result = web_search.SearchResult(
            title="t", url="https://E.com/a/?utm_source=news"
        )
        assert result.normalized_url == "https://e.com/a"


class TestTavilyProvider:
    @pytest.mark.asyncio
    async def test_parses_results_and_sends_bearer_token(self, monkeypatch):
        payload = {
            "results": [
                {
                    "title": "A",
                    "url": "https://a.example/",
                    "content": "aa",
                    "score": 0.9,
                },
                {"title": "B", "url": "https://b.example/", "content": "bb"},
                {"title": "no url", "url": "", "content": "x"},
            ]
        }
        fake = _patch_client(monkeypatch, _FakeResponse(200, payload))

        provider = web_search.TavilySearchProvider("tvly-test")
        results = await provider.search("topic", 5, exclude_domains=["spam.example"])

        assert [r.url for r in results] == [
            "https://a.example/",
            "https://b.example/",
        ]
        assert results[0].title == "A"
        assert results[0].snippet == "aa"
        assert results[0].score == 0.9
        assert results[0].provider == "tavily"
        assert results[1].score == 0.0

        url, kwargs = fake.calls[0]
        assert url == web_search.TAVILY_ENDPOINT
        assert kwargs["headers"]["Authorization"] == "Bearer tvly-test"
        assert kwargs["json"]["exclude_domains"] == ["spam.example"]
        assert kwargs["json"]["max_results"] == 5

    @pytest.mark.asyncio
    async def test_missing_results_key_returns_empty_list(self, monkeypatch):
        _patch_client(monkeypatch, _FakeResponse(200, {}))
        provider = web_search.TavilySearchProvider("k")
        assert await provider.search("q", 3) == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (401, ConfigurationError),
            (403, ConfigurationError),
            (429, ExternalServiceError),
            (500, ExternalServiceError),
        ],
    )
    async def test_http_errors_map_to_typed_exceptions(
        self, monkeypatch, status, expected
    ):
        _patch_client(monkeypatch, _FakeResponse(status, {}))
        provider = web_search.TavilySearchProvider("k")
        with pytest.raises(expected):
            await provider.search("q", 3)

    @pytest.mark.asyncio
    async def test_network_error_maps_to_external_service_error(self, monkeypatch):
        class _Boom:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc_info):
                return False

            async def post(self, *args, **kwargs):
                raise httpx.ConnectError("boom")

        monkeypatch.setattr(web_search.httpx, "AsyncClient", lambda **kwargs: _Boom())
        provider = web_search.TavilySearchProvider("k")
        with pytest.raises(ExternalServiceError):
            await provider.search("q", 3)


class TestProviderResolution:
    def test_missing_key_raises_configuration_error(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY_FILE", raising=False)
        with pytest.raises(ConfigurationError):
            web_search.get_provider("tavily")

    def test_unknown_provider_raises_configuration_error(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "k")
        with pytest.raises(ConfigurationError):
            web_search.get_provider("nope")

    def test_default_provider_is_tavily(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "k")
        assert web_search.get_provider().name == "tavily"


class TestSearchWeb:
    @pytest.mark.asyncio
    async def test_empty_query_is_rejected(self):
        with pytest.raises(InvalidInputError):
            await web_search.search_web("   ")

    @pytest.mark.asyncio
    async def test_delegates_to_the_resolved_provider(self, monkeypatch):
        captured: dict = {}

        class _Fake:
            name = "tavily"

            async def search(self, query, limit, *, exclude_domains=()):
                captured.update(
                    query=query, limit=limit, exclude=tuple(exclude_domains)
                )
                return [web_search.SearchResult(title="t", url="https://t.example/")]

        monkeypatch.setattr(web_search, "get_provider", lambda name=None: _Fake())
        results = await web_search.search_web("  topic  ", 7, exclude_domains=["x"])

        assert captured == {"query": "topic", "limit": 7, "exclude": ("x",)}
        assert [r.url for r in results] == ["https://t.example/"]
