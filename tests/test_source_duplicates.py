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

    def test_default_port_is_scheme_specific(self):
        # 443 is not the default port for http, 80 is not for https.
        assert normalize_source_url("http://example.com:443/a") != normalize_source_url(
            "http://example.com/a"
        )
        assert normalize_source_url("https://example.com:80/a") != normalize_source_url(
            "https://example.com/a"
        )
        assert normalize_source_url("http://example.com:80/a") == normalize_source_url(
            "http://example.com/a"
        )

    def test_encoded_reserved_chars_not_conflated(self):
        assert normalize_source_url(
            "https://example.com/a%2Fb"
        ) != normalize_source_url("https://example.com/a/b")

    def test_encoded_unreserved_chars_match(self):
        assert normalize_source_url(
            "https://example.com/%7Euser"
        ) == normalize_source_url("https://example.com/~user")

    def test_malformed_url_never_raises(self):
        assert normalize_source_url("http://[::1") == "http://[::1"
        assert normalize_source_url("::::") == "::::"


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

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_malformed_url_is_fail_open(self, mock_query):
        """A candidate URL that fails normalization returns [] (never 500)."""
        mock_query.return_value = EXISTING
        assert (
            await find_duplicate_sources(source_type="link", url="http://[::1")
        ) == []

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_no_keys_skips_query(self, mock_query):
        assert await find_duplicate_sources() == []
        mock_query.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_link_lookup_is_keyed_by_host(self, mock_query):
        """Link probes filter by URL host instead of scanning the table."""
        mock_query.return_value = EXISTING
        await find_duplicate_sources(
            source_type="link", url="https://example.com/article"
        )
        query, params = mock_query.await_args.args
        assert "LIMIT 500" not in query
        assert params["host"] == "example.com"

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_title_prefilter_trims_whitespace(self, mock_query):
        """Stored titles with surrounding whitespace must not escape the prefilter."""
        mock_query.return_value = []
        await find_duplicate_sources(source_type="text", title="My Doc")
        query, params = mock_query.await_args.args
        assert "string::trim(title)" in query
        assert params["weak_title"] == "my doc"

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_content_lookup_is_length_bounded(self, mock_query):
        """Text probes prefilter by stored length before hashing full_text."""
        mock_query.return_value = []
        await find_duplicate_sources(source_type="text", content="hello world")
        query, params = mock_query.await_args.args
        assert "string::len(full_text)" in query
        assert params["min_len"] <= len("hello world") <= params["max_len"]


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

    def test_invalid_type_is_rejected(self, client):
        response = client.post(
            "/api/sources/check-duplicates", json={"type": "podcast"}
        )
        assert response.status_code == 422

    def test_metadata_url_is_rejected(self, client):
        response = client.post(
            "/api/sources/check-duplicates",
            json={"type": "link", "url": "http://169.254.169.254/latest/"},
        )
        assert response.status_code == 400
