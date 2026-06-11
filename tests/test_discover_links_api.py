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
