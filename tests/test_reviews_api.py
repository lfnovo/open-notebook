"""Tests for the repo-review config and recent-paths endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client after environment variables have been cleared by conftest."""
    from api.main import app

    return TestClient(app)


class TestReviewConfig:
    def test_returns_configured_allowed_roots(self, client, monkeypatch):
        monkeypatch.setattr(
            "api.routers.reviews.REPO_REVIEW_ALLOWED_ROOTS", ["/data/repos"]
        )

        response = client.get("/api/reviews/config")

        assert response.status_code == 200
        assert response.json() == {"allowed_roots": ["/data/repos"]}

    def test_empty_when_feature_unconfigured(self, client, monkeypatch):
        monkeypatch.setattr("api.routers.reviews.REPO_REVIEW_ALLOWED_ROOTS", [])

        response = client.get("/api/reviews/config")

        assert response.status_code == 200
        assert response.json() == {"allowed_roots": []}


class TestRecentReviewPaths:
    @patch("api.routers.reviews.Review.get_recent_paths", new_callable=AsyncMock)
    def test_returns_paths_from_domain_method(self, mock_get_recent_paths, client):
        mock_get_recent_paths.return_value = ["/repos/a", "/repos/b"]

        response = client.get("/api/reviews/recent-paths")

        assert response.status_code == 200
        assert response.json() == ["/repos/a", "/repos/b"]

    @patch("api.routers.reviews.Review.get_recent_paths", new_callable=AsyncMock)
    def test_empty_when_no_review_history(self, mock_get_recent_paths, client):
        mock_get_recent_paths.return_value = []

        response = client.get("/api/reviews/recent-paths")

        assert response.status_code == 200
        assert response.json() == []
