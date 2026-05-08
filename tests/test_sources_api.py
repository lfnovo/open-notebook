"""Tests for the sources API endpoint."""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.routers.sources import get_sources
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
    @patch("api.services.source_service.resolve_default_model_id", new_callable=AsyncMock)
    @patch("api.services.source_service.resolve_resource_team_context", new_callable=AsyncMock)
    @patch("api.services.source_processing.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.add_to_notebook", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    async def test_async_link_source_persists_url_asset(
        self, mock_nb_get, mock_add_nb, mock_submit, mock_resolve_team, mock_resolve_model, client
    ):
        """POST /sources with type=link and async_processing=true persists Asset(url=...)."""
        mock_nb_get.return_value = MagicMock()
        mock_submit.return_value = "command:123"
        mock_resolve_team.return_value = None
        mock_resolve_model.return_value = "model:tools"

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
    @patch("api.services.source_service.resolve_default_model_id", new_callable=AsyncMock)
    @patch("api.services.source_service.resolve_resource_team_context", new_callable=AsyncMock)
    @patch("api.services.source_processing.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.add_to_notebook", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    @patch("api.routers.sources.save_uploaded_file", new_callable=AsyncMock)
    async def test_async_upload_source_persists_file_asset(
        self, mock_upload, mock_nb_get, mock_add_nb, mock_submit, mock_resolve_team, mock_resolve_model, client
    ):
        """POST /sources with type=upload and async_processing=true persists Asset(file_path=...)."""
        mock_nb_get.return_value = MagicMock()
        mock_upload.return_value = os.path.join(os.path.abspath(UPLOADS_FOLDER), "video.mp4")
        mock_submit.return_value = "command:123"
        mock_resolve_team.return_value = None
        mock_resolve_model.return_value = "model:tools"

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
    @patch("api.services.source_service.resolve_default_model_id", new_callable=AsyncMock)
    @patch("api.services.source_service.resolve_resource_team_context", new_callable=AsyncMock)
    @patch("api.services.source_processing.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.add_to_notebook", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    async def test_async_text_source_has_no_asset(
        self, mock_nb_get, mock_add_nb, mock_submit, mock_resolve_team, mock_resolve_model, client
    ):
        """POST /sources with type=text and async_processing=true has asset=None."""
        mock_nb_get.return_value = MagicMock()
        mock_submit.return_value = "command:123"
        mock_resolve_team.return_value = None
        mock_resolve_model.return_value = "model:tools"

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

    @pytest.mark.asyncio
    @patch("api.services.source_service.resolve_workspace_id_for_user", new_callable=AsyncMock)
    @patch("api.services.source_service.resolve_default_model_id", new_callable=AsyncMock)
    @patch("api.services.source_processing.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.add_to_notebook", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    async def test_async_text_source_persists_workspace_id(
        self, mock_nb_get, mock_add_nb, mock_submit, mock_resolve_model, mock_workspace_id, client
    ):
        mock_nb_get.return_value = MagicMock()
        mock_submit.return_value = "command:123"
        mock_resolve_model.return_value = "model:tools"
        mock_workspace_id.return_value = "workspace:team"

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
                    "workspace_id": "workspace:team",
                    "async_processing": "true",
                },
            )

        assert response.status_code == 200
        assert len(saved_sources) >= 1
        assert str(saved_sources[0].workspace_id) == "workspace:team"


@pytest.mark.asyncio
@patch("api.routers.sources.SourceRepository.list_sources", new_callable=AsyncMock)
@patch("api.routers.sources.WorkspaceRepository.user_can_access", new_callable=AsyncMock)
@patch("api.routers.sources.TeamRepository.user_team_ids", new_callable=AsyncMock)
async def test_admin_cannot_list_personal_workspace_sources_by_id(
    mock_team_ids,
    mock_workspace_access,
    mock_list_sources,
):
    mock_team_ids.return_value = []
    mock_workspace_access.return_value = False
    request = SimpleNamespace(
        state=SimpleNamespace(
            user_id="app_user:admin",
            username="admin",
            user_role="admin",
            user_status="active",
        )
    )

    with pytest.raises(HTTPException) as exc:
        await get_sources(
            request,
            notebook_id=None,
            title_contains=None,
            workspace_id="workspace:personal",
            limit=30,
            offset=0,
            sort_by="updated",
            sort_order="desc",
        )

    assert exc.value.status_code == 403
    mock_workspace_access.assert_awaited_once_with(
        workspace_id="workspace:personal",
        user_id="app_user:admin",
        include_all_for_admin=True,
    )
    mock_list_sources.assert_not_awaited()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
