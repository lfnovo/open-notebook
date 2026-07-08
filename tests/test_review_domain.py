"""Tests for Review domain logic not already covered by API-level tests."""

from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.domain.review import Review


class TestGetRecentPaths:
    @pytest.mark.asyncio
    @patch("open_notebook.domain.review.repo_query", new_callable=AsyncMock)
    async def test_dedupes_preserving_most_recent_order(self, mock_repo_query):
        mock_repo_query.return_value = [
            {"repo_path": "/repos/a"},
            {"repo_path": "/repos/b"},
            {"repo_path": "/repos/a"},  # older run of the same repo, must be dropped
            {"repo_path": "/repos/c"},
        ]

        paths = await Review.get_recent_paths()

        assert paths == ["/repos/a", "/repos/b", "/repos/c"]

    @pytest.mark.asyncio
    @patch("open_notebook.domain.review.repo_query", new_callable=AsyncMock)
    async def test_respects_limit(self, mock_repo_query):
        mock_repo_query.return_value = [
            {"repo_path": "/repos/a"},
            {"repo_path": "/repos/b"},
            {"repo_path": "/repos/c"},
        ]

        paths = await Review.get_recent_paths(limit=2)

        assert paths == ["/repos/a", "/repos/b"]

    @pytest.mark.asyncio
    @patch("open_notebook.domain.review.repo_query", new_callable=AsyncMock)
    async def test_empty_when_no_reviews(self, mock_repo_query):
        mock_repo_query.return_value = []

        paths = await Review.get_recent_paths()

        assert paths == []
