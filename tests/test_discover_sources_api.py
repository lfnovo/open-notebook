"""
Tests for POST /api/sources/discover (api/routers/sources.py).

Locks the contract of the "discover web sources" capability (issue #973): a
search hit becomes a link Source unless it is a duplicate (skipped) or fails
the SSRF guard (error), and `dry_run` never writes anything.
"""

import pytest
from fastapi.testclient import TestClient

from api.models import SourceResponse
from open_notebook.research.web_search import SearchResult


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def _hit(url: str, title: str = "Title", score: float = 0.5) -> SearchResult:
    return SearchResult(
        title=title, url=url, snippet="snip", score=score, provider="tavily"
    )


class _FakeNotebookModel:
    """Stands in for the Notebook domain model's async get()."""

    def __init__(self, found: bool) -> None:
        self._found = found

    async def get(self, notebook_id: str):
        return object() if self._found else None


def _patch(
    monkeypatch,
    *,
    hits,
    existing=(),
    notebook_found=True,
    create_error=False,
    block_urls=(),
    validate_error=None,
):
    import api.routers.sources as sources

    async def fake_search_web(query, limit=5, *, provider=None, exclude_domains=()):
        return list(hits)

    async def fake_existing(notebook_id):
        return set(existing)

    async def fake_validate(url, provider):
        if validate_error is not None:
            raise ValueError(validate_error)
        if url in block_urls:
            raise ValueError("blocked internal address")

    async def fake_create(source_data, content_state, transformation_ids, file_path):
        if create_error:
            raise RuntimeError("queue unavailable")
        return SourceResponse(
            id="source:1",
            title="Title",
            topics=[],
            asset=None,
            full_text=None,
            embedded=False,
            embedded_chunks=0,
            created="2026-01-01T00:00:00Z",
            updated="2026-01-01T00:00:00Z",
        )

    monkeypatch.setattr(sources, "Notebook", _FakeNotebookModel(notebook_found))
    monkeypatch.setattr(sources, "search_web", fake_search_web)
    monkeypatch.setattr(sources, "_existing_notebook_urls", fake_existing)
    monkeypatch.setattr(sources, "validate_url", fake_validate)
    monkeypatch.setattr(sources, "_create_source_async_path", fake_create)


class TestDiscoverSourcesEndpoint:
    def test_dry_run_returns_candidates_without_creating(self, client, monkeypatch):
        _patch(monkeypatch, hits=[_hit("https://a.example/x")])

        response = client.post(
            "/api/sources/discover",
            json={"query": "topic", "notebook_id": "notebook:1", "dry_run": True},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["created_count"] == 0
        assert body["provider"] == "tavily"
        assert body["results"][0]["status"] == "candidate"
        assert body["results"][0]["url"] == "https://a.example/x"

    def test_creates_link_sources_for_each_hit(self, client, monkeypatch):
        _patch(
            monkeypatch,
            hits=[_hit("https://a.example/x"), _hit("https://b.example/y")],
        )

        response = client.post(
            "/api/sources/discover",
            json={"query": "topic", "notebook_id": "notebook:1"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["created_count"] == 2
        assert {r["status"] for r in body["results"]} == {"created"}
        assert body["results"][0]["source_id"] == "source:1"

    def test_existing_url_is_skipped(self, client, monkeypatch):
        _patch(
            monkeypatch,
            hits=[_hit("https://a.example/x?utm_source=newsletter")],
            existing={"https://a.example/x"},
        )

        body = client.post(
            "/api/sources/discover",
            json={"query": "topic", "notebook_id": "notebook:1"},
        ).json()

        assert body["created_count"] == 0
        assert body["skipped_count"] == 1
        assert body["results"][0]["status"] == "skipped"

    def test_duplicate_hits_are_collapsed(self, client, monkeypatch):
        _patch(
            monkeypatch,
            hits=[
                _hit("https://a.example/x"),
                _hit("https://a.example/x?utm_source=t"),
            ],
        )

        body = client.post(
            "/api/sources/discover",
            json={"query": "topic", "notebook_id": "notebook:1"},
        ).json()

        assert body["created_count"] == 1
        assert len(body["results"]) == 1

    def test_ssrf_blocked_url_is_reported_per_candidate(self, client, monkeypatch):
        blocked = "http://169.254.169.254/latest/meta-data"
        _patch(
            monkeypatch,
            hits=[_hit(blocked), _hit("https://ok.example/")],
            block_urls={blocked},
        )

        body = client.post(
            "/api/sources/discover",
            json={"query": "topic", "notebook_id": "notebook:1"},
        ).json()

        statuses = {r["url"]: r["status"] for r in body["results"]}
        assert statuses[blocked] == "error"
        assert statuses["https://ok.example/"] == "created"
        assert body["created_count"] == 1

    def test_creation_failure_is_reported_per_candidate(self, client, monkeypatch):
        _patch(
            monkeypatch,
            hits=[_hit("https://a.example/x")],
            create_error=True,
        )

        response = client.post(
            "/api/sources/discover",
            json={"query": "topic", "notebook_id": "notebook:1"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["created_count"] == 0
        assert body["results"][0]["status"] == "error"

    def test_missing_notebook_returns_404(self, client, monkeypatch):
        _patch(monkeypatch, hits=[], notebook_found=False)

        response = client.post(
            "/api/sources/discover",
            json={"query": "topic", "notebook_id": "notebook:1"},
        )

        assert response.status_code == 404

    def test_empty_query_is_rejected_by_validation(self, client):
        response = client.post(
            "/api/sources/discover",
            json={"query": "", "notebook_id": "notebook:1"},
        )

        assert response.status_code == 422

    def test_limit_bounds_are_enforced(self, client):
        response = client.post(
            "/api/sources/discover",
            json={"query": "topic", "notebook_id": "notebook:1", "limit": 0},
        )

        assert response.status_code == 422
