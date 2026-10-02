"""Tests for duplicate source detection and warning (#257)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.routers.sources import (
    content_hash,
    find_duplicate_sources,
    normalize_source_url,
)


@pytest.fixture
def client():
    """Create test client after environment variables have been cleared by conftest."""
    from api.main import app

    return TestClient(app)


EXISTING = [
    {
        "id": "source:1",
        "title": "Example Article",
        "asset": {"url": "https://example.com/article/"},
        "full_text": "hello world",
        "created": "2026-01-01",
        "updated": "2026-01-02",
    },
    {
        "id": "source:2",
        "title": "notes.pdf",
        "asset": {"file_path": "/uploads/notes.pdf"},
        "full_text": "something else entirely",
        "created": "2026-01-01",
        "updated": "2026-01-01",
    },
]


class TestNormalizeSourceUrl:
    def test_trivial_variants_match(self):
        assert normalize_source_url(
            "https://Example.com/article/"
        ) == normalize_source_url("https://example.com/article")

    def test_tracking_params_and_fragment_ignored(self):
        assert normalize_source_url(
            "https://example.com/article?utm_source=x#section"
        ) == normalize_source_url("https://example.com/article")

    def test_default_port_ignored(self):
        assert normalize_source_url(
            "https://example.com:443/article"
        ) == normalize_source_url("https://example.com/article")

    def test_different_targets_differ(self):
        assert normalize_source_url("https://example.com/a") != normalize_source_url(
            "https://example.com/b"
        )


class TestContentHash:
    def test_whitespace_insensitive(self):
        assert content_hash("hello   world\n") == content_hash("hello world")

    def test_blank_is_none(self):
        assert content_hash("") is None
        assert content_hash(None) is None
        assert content_hash("   \n ") is None

    def test_different_text_different_hash(self):
        assert content_hash("hello world") != content_hash("hello mars")


class TestFindDuplicateSources:
    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_url_match(self, mock_query):
        mock_query.return_value = EXISTING
        dups = await find_duplicate_sources(
            source_type="link", url="https://example.com/article?utm_x=1"
        )
        assert [d.id for d in dups] == ["source:1"]
        assert dups[0].match_reason == "url"
        # Summary fields for the warning dialog are populated
        assert dups[0].title == "Example Article"
        assert dups[0].url == "https://example.com/article/"
        assert dups[0].excerpt == "hello world"

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_content_match(self, mock_query):
        mock_query.return_value = EXISTING
        dups = await find_duplicate_sources(source_type="text", content="hello   world")
        assert [d.id for d in dups] == ["source:1"]
        assert dups[0].match_reason == "content"

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_filename_fallback(self, mock_query):
        mock_query.return_value = EXISTING
        dups = await find_duplicate_sources(source_type="upload", filename="Notes.PDF")
        assert [d.id for d in dups] == ["source:2"]
        assert dups[0].match_reason == "filename"
        assert dups[0].filename == "notes.pdf"

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_no_match_returns_empty(self, mock_query):
        mock_query.return_value = EXISTING
        assert (
            await find_duplicate_sources(
                source_type="link", url="https://unrelated.example/x"
            )
        ) == []

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_lookup_failure_is_fail_open(self, mock_query):
        """A duplicate lookup must never block source creation."""
        mock_query.side_effect = RuntimeError("db down")
        assert (
            await find_duplicate_sources(
                source_type="link", url="https://example.com/article"
            )
        ) == []


class TestCheckDuplicatesEndpoint:
    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_returns_matches(self, mock_query, client):
        mock_query.return_value = EXISTING
        response = client.post(
            "/api/sources/check-duplicates",
            json={"type": "link", "url": "https://example.com/article/"},
        )
        assert response.status_code == 200
        duplicates = response.json()["duplicates"]
        assert len(duplicates) == 1
        assert duplicates[0]["id"] == "source:1"
        assert duplicates[0]["match_reason"] == "url"

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_no_duplicates_empty_list(self, mock_query, client):
        mock_query.return_value = EXISTING
        response = client.post(
            "/api/sources/check-duplicates",
            json={"type": "link", "url": "https://unrelated.example/x"},
        )
        assert response.status_code == 200
        assert response.json() == {"duplicates": []}

    def test_link_without_url_is_400(self, client):
        response = client.post("/api/sources/check-duplicates", json={"type": "link"})
        assert response.status_code == 400
