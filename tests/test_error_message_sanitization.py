"""
Tests that internal exception text is never leaked to API clients in
api/routers/sources.py and api/podcast_service.py.

These previously interpolated the raw exception (`detail=f"...: {str(e)}"`)
into the client-facing error response - inconsistent with the safer pattern
already used elsewhere in the same files (e.g. the download handlers),
which log the raw exception server-side but return a fixed generic
message. Every occurrence already had a matching logger.error() call, so
this was a client-facing message change only, not a logging change.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

SECRET = "connection to db-primary-7f3a.internal:5432 refused: password authentication failed"


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestSourcesRouterDoesNotLeakExceptionText:
    def test_list_sources_failure_returns_generic_message(self, client):
        with patch(
            "api.routers.sources.repo_query",
            new=AsyncMock(side_effect=RuntimeError(SECRET)),
        ):
            response = client.get("/api/sources")

        assert response.status_code == 500
        assert SECRET not in response.text
        assert response.json()["detail"] == "Error fetching sources"

    def test_delete_source_failure_returns_generic_message(self, client):
        mock_source = AsyncMock()
        mock_source.delete = AsyncMock(side_effect=RuntimeError(SECRET))

        with patch(
            "api.routers.sources.Source.get", new=AsyncMock(return_value=mock_source)
        ):
            response = client.delete("/api/sources/source:abc123")

        assert response.status_code == 500
        assert SECRET not in response.text
        assert response.json()["detail"] == "Error deleting source"

    def test_get_source_insights_failure_returns_generic_message(self, client):
        mock_source = AsyncMock()
        mock_source.get_insights = AsyncMock(side_effect=RuntimeError(SECRET))

        with patch(
            "api.routers.sources.Source.get", new=AsyncMock(return_value=mock_source)
        ):
            response = client.get("/api/sources/source:abc123/insights")

        assert response.status_code == 500
        assert SECRET not in response.text
        assert response.json()["detail"] == "Error fetching insights"

    def test_update_source_failure_returns_generic_message(self, client):
        mock_source = AsyncMock()
        mock_source.save = AsyncMock(side_effect=RuntimeError(SECRET))
        mock_source.asset = None

        with patch(
            "api.routers.sources.Source.get", new=AsyncMock(return_value=mock_source)
        ):
            response = client.put(
                "/api/sources/source:abc123", json={"title": "New Title"}
            )

        assert response.status_code == 500
        assert SECRET not in response.text
        assert response.json()["detail"] == "Error updating source"


class TestInvalidInputErrorsStillReturnTheirOwnSafeMessage:
    """InvalidInputError is a distinct, deliberate pattern (app-authored,
    user-facing validation text) - not the raw-exception-leak pattern this
    fix targets, and must be untouched."""

    def test_update_source_invalid_input_still_returns_its_message(self, client):
        from open_notebook.exceptions import InvalidInputError

        mock_source = AsyncMock()
        mock_source.save = AsyncMock(
            side_effect=InvalidInputError("Title cannot be empty")
        )
        mock_source.asset = None

        with patch(
            "api.routers.sources.Source.get", new=AsyncMock(return_value=mock_source)
        ):
            response = client.put(
                "/api/sources/source:abc123", json={"title": "x"}
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "Title cannot be empty"


class TestPodcastServiceDoesNotLeakExceptionText:
    @pytest.mark.asyncio
    async def test_get_job_status_failure_returns_generic_message(self):
        from fastapi import HTTPException

        from api.podcast_service import PodcastService

        with patch(
            "api.podcast_service.get_command_status",
            new=AsyncMock(side_effect=RuntimeError(SECRET)),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await PodcastService.get_job_status("command:abc123")

        assert exc_info.value.status_code == 500
        assert SECRET not in exc_info.value.detail
        assert exc_info.value.detail == "Failed to get job status"

    @pytest.mark.asyncio
    async def test_list_episodes_failure_returns_generic_message(self):
        from fastapi import HTTPException

        from api.podcast_service import PodcastService
        from open_notebook.podcasts.models import PodcastEpisode

        with patch.object(
            PodcastEpisode,
            "get_all",
            new=AsyncMock(side_effect=RuntimeError(SECRET)),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await PodcastService.list_episodes()

        assert exc_info.value.status_code == 500
        assert SECRET not in exc_info.value.detail
        assert exc_info.value.detail == "Failed to list episodes"

    @pytest.mark.asyncio
    async def test_get_episode_failure_returns_generic_not_found(self):
        from fastapi import HTTPException

        from api.podcast_service import PodcastService
        from open_notebook.podcasts.models import PodcastEpisode

        with patch.object(
            PodcastEpisode, "get", new=AsyncMock(side_effect=RuntimeError(SECRET))
        ):
            with pytest.raises(HTTPException) as exc_info:
                await PodcastService.get_episode("episode:missing")

        assert exc_info.value.status_code == 404
        assert SECRET not in exc_info.value.detail
        assert exc_info.value.detail == "Episode not found"

    @pytest.mark.asyncio
    async def test_submit_generation_job_failure_returns_generic_message(self):
        from fastapi import HTTPException

        from api.podcast_service import PodcastService

        with patch(
            "api.podcast_service.EpisodeProfile.get_by_name",
            new=AsyncMock(side_effect=RuntimeError(SECRET)),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await PodcastService.submit_generation_job(
                    episode_profile_name="default",
                    speaker_profile_name="default",
                    episode_name="Test Episode",
                    content="some content",
                )

        assert exc_info.value.status_code == 500
        assert SECRET not in exc_info.value.detail
        assert exc_info.value.detail == "Failed to submit podcast generation job"
