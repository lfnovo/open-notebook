"""Tests for the sources API endpoint."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.config import UPLOADS_FOLDER
from open_notebook.domain.notebook import Source


@pytest.fixture
def client():
    """Create test client after environment variables have been cleared by conftest."""
    from api.main import app

    return TestClient(app)


class TestAsyncSourceAssetPersistence:
    """Tests for #627 - asset is persisted before async processing.

    These tests hit the real create_source endpoint with mocked DB/command
    calls, verifying that the Source saved to the database has the correct
    asset set *before* async processing begins.
    """

    @pytest.mark.asyncio
    @patch("api.routers.sources.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.add_to_notebook", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    async def test_async_link_source_persists_url_asset(
        self, mock_nb_get, mock_add_nb, mock_submit, client
    ):
        """POST /sources with type=link and async_processing=true persists Asset(url=...)."""
        mock_nb_get.return_value = MagicMock()
        mock_submit.return_value = "command:123"

        saved_sources = []

        async def capture_save(self_source):
            saved_sources.append(self_source)
            self_source.id = "source:fake"
            self_source.command = None

        with patch.object(Source, "save", autospec=True, side_effect=capture_save):
            response = client.post(
                "/api/sources",
                data={
                    "type": "link",
                    "url": "https://example.com/article",
                    "notebooks": '["notebook:1"]',
                    "async_processing": "true",
                },
            )

        assert response.status_code == 200
        assert len(saved_sources) >= 1

        source = saved_sources[0]
        assert source.asset is not None
        assert source.asset.url == "https://example.com/article"
        assert source.asset.file_path is None

    @pytest.mark.asyncio
    @patch("api.routers.sources.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.add_to_notebook", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    @patch("api.routers.sources.save_uploaded_file", new_callable=AsyncMock)
    async def test_async_upload_source_persists_file_asset(
        self, mock_upload, mock_nb_get, mock_add_nb, mock_submit, client
    ):
        """POST /sources with type=upload and async_processing=true persists Asset(file_path=...)."""
        mock_nb_get.return_value = MagicMock()
        mock_upload.return_value = os.path.join(os.path.abspath(UPLOADS_FOLDER), "video.mp4")
        mock_submit.return_value = "command:123"

        saved_sources = []

        async def capture_save(self_source):
            saved_sources.append(self_source)
            self_source.id = "source:fake"
            self_source.command = None

        with patch.object(Source, "save", autospec=True, side_effect=capture_save):
            response = client.post(
                "/api/sources",
                data={
                    "type": "upload",
                    "notebooks": '["notebook:1"]',
                    "async_processing": "true",
                },
                files={"file": ("video.mp4", b"fake content", "video/mp4")},
            )

        assert response.status_code == 200
        assert len(saved_sources) >= 1

        source = saved_sources[0]
        assert source.asset is not None
        assert source.asset.file_path == os.path.join(os.path.abspath(UPLOADS_FOLDER), "video.mp4")
        assert source.asset.url is None

    @pytest.mark.asyncio
    @patch("api.routers.sources.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.add_to_notebook", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    async def test_async_text_source_has_no_asset(
        self, mock_nb_get, mock_add_nb, mock_submit, client
    ):
        """POST /sources with type=text and async_processing=true has asset=None."""
        mock_nb_get.return_value = MagicMock()
        mock_submit.return_value = "command:123"

        saved_sources = []

        async def capture_save(self_source):
            saved_sources.append(self_source)
            self_source.id = "source:fake"
            self_source.command = None

        with patch.object(Source, "save", autospec=True, side_effect=capture_save):
            response = client.post(
                "/api/sources",
                data={
                    "type": "text",
                    "content": "Some text content",
                    "notebooks": '["notebook:1"]',
                    "async_processing": "true",
                },
            )

        assert response.status_code == 200
        assert len(saved_sources) >= 1

        source = saved_sources[0]
        assert source.asset is None


class TestRetrySourceProcessing:
    """POST /sources/{id}/retry must find a source's notebooks via the reference
    edge's in/out columns, not a non-existent `source` column (#861)."""

    @pytest.mark.asyncio
    @patch("api.routers.sources.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.get", new_callable=AsyncMock)
    async def test_retry_finds_notebooks_and_requeues(
        self, mock_get, mock_repo_query, mock_submit, client
    ):
        source = MagicMock()
        source.id = "source:1"
        source.command = None
        source.title = "My source"
        source.topics = []
        source.full_text = None
        source.asset = MagicMock(file_path=None, url="https://example.com/post")
        source.save = AsyncMock()
        source.get_embedded_chunks = AsyncMock(return_value=0)
        mock_get.return_value = source

        # The corrected query returns the linked notebook(s)
        mock_repo_query.return_value = ["notebook:1"]
        # submit_command_job returns str(RecordID), which already includes the
        # "command:" table prefix.
        mock_submit.return_value = "command:123"

        response = client.post("/api/sources/source:1/retry")

        assert response.status_code == 200
        # Regression guard: must query the reference edge by its `in` column
        called_query = mock_repo_query.await_args.args[0]
        assert "WHERE in = $source_id" in called_query
        assert "SELECT VALUE out FROM reference" in called_query
        # Regression guard: command_id must not be double-prefixed
        # (`command:command:…`), which previously raised a 500 on save.
        assert "command:command" not in str(source.command)
        assert str(source.command).count("command:") == 1
        assert str(source.command).startswith("command:")

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.get", new_callable=AsyncMock)
    async def test_retry_400_only_when_truly_unlinked(
        self, mock_get, mock_repo_query, client
    ):
        source = MagicMock()
        source.id = "source:1"
        source.command = None
        mock_get.return_value = source
        mock_repo_query.return_value = []  # genuinely no notebooks

        response = client.post("/api/sources/source:1/retry")

        assert response.status_code == 400
        assert "not associated with any notebooks" in response.json()["detail"]


class TestGetSourceNotFound:
    """GET /sources/{id} must return 404 (not 500) for a missing/deleted source.
    `Source.get()` raises NotFoundError rather than returning None, so the handler
    must map it to 404 instead of catching it in its generic `except`."""

    @pytest.mark.asyncio
    @patch("api.routers.sources.Source.get", new_callable=AsyncMock)
    async def test_get_missing_source_returns_404(self, mock_get, client):
        from open_notebook.exceptions import NotFoundError

        mock_get.side_effect = NotFoundError("source with id source:gone not found")

        response = client.get("/api/sources/source:gone")

        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestTitleSortUsesAlias:
    """Regression for sort_by=title returning a 500 (v1.11 release testing).

    source.title carries a SEARCH (BM25) index and SurrealDB's planner
    fails ORDER BY on such a column with "No iterator has been found".
    The router must therefore sort by the computed `title_sort` alias,
    never by the raw indexed column.
    """

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_sort_by_title_orders_by_alias(self, mock_query, client):
        mock_query.return_value = []

        response = client.get("/api/sources?sort_by=title")

        assert response.status_code == 200
        query = mock_query.call_args[0][0]
        assert "ORDER BY title_sort" in query
        assert "AS title_sort" in query

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query", new_callable=AsyncMock)
    async def test_all_sort_fields_return_200(self, mock_query, client):
        mock_query.return_value = []
        for field in ["type", "title", "created", "updated", "insights_count", "embedded"]:
            response = client.get(f"/api/sources?sort_by={field}")
            assert response.status_code == 200, f"sort_by={field}"

    def test_invalid_sort_field_returns_400(self, client):
        response = client.get("/api/sources?sort_by=bogus")
        assert response.status_code == 400
