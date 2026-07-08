"""
Tests for the podcast episode listing N+1 fix (api/routers/podcasts.py +
open_notebook/podcasts/models.py).

list_podcast_episodes() used to call episode.get_job_detail() once per
episode - each a separate round trip against the surreal_commands `command`
table. PodcastEpisode.get_job_details_for_commands() batches that into one
query; the router now calls it once up front instead of looping.
"""

from unittest.mock import AsyncMock, patch

import pytest

from api.routers.podcasts import list_podcast_episodes
from open_notebook.podcasts.models import PodcastEpisode


def make_episode(command=None, audio_file=None, **overrides):
    defaults = dict(
        id=f"episode:{overrides.pop('suffix', 'x')}",
        name="Test Episode",
        episode_profile={"name": "default"},
        speaker_profile={"name": "default"},
        briefing="briefing",
        content="content",
        command=command,
        audio_file=audio_file,
    )
    defaults.update(overrides)
    return PodcastEpisode(**defaults)


class TestGetJobDetailsForCommandsUnit:
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_without_querying(self):
        with patch(
            "open_notebook.podcasts.models.repo_query", new=AsyncMock()
        ) as mock_query:
            result = await PodcastEpisode.get_job_details_for_commands([])
        assert result == {}
        mock_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_query_for_multiple_commands(self):
        fake_rows = [
            {"id": "command:a", "status": "completed", "error_message": None},
            {"id": "command:b", "status": "failed", "error_message": "boom"},
        ]
        with patch(
            "open_notebook.podcasts.models.repo_query",
            new=AsyncMock(return_value=fake_rows),
        ) as mock_query:
            result = await PodcastEpisode.get_job_details_for_commands(
                ["command:a", "command:b"]
            )

        mock_query.assert_awaited_once()
        assert result == {
            "command:a": {"status": "completed", "error_message": None},
            "command:b": {"status": "failed", "error_message": "boom"},
        }

    @pytest.mark.asyncio
    async def test_query_failure_returns_empty_dict_rather_than_raising(self):
        with patch(
            "open_notebook.podcasts.models.repo_query",
            new=AsyncMock(side_effect=RuntimeError("db down")),
        ):
            result = await PodcastEpisode.get_job_details_for_commands(["command:a"])
        assert result == {}

    @pytest.mark.asyncio
    async def test_falsy_command_ids_are_filtered_out(self):
        with patch(
            "open_notebook.podcasts.models.repo_query", new=AsyncMock(return_value=[])
        ) as mock_query:
            await PodcastEpisode.get_job_details_for_commands([None, "", "command:a"])

        # Only the truthy id should reach the query's bound params.
        _, kwargs_or_args = mock_query.call_args
        bound_vars = mock_query.call_args.args[1]
        assert len(bound_vars["command_ids"]) == 1


class TestListPodcastEpisodesUsesBatchedLookup:
    @pytest.mark.asyncio
    async def test_batch_method_called_once_not_per_episode(self):
        episodes = [
            make_episode(command=f"command:cmd{i}", suffix=str(i)) for i in range(5)
        ]
        batch_result = {
            f"command:cmd{i}": {"status": "completed", "error_message": None}
            for i in range(5)
        }

        with (
            patch(
                "api.routers.podcasts.PodcastService.list_episodes",
                new=AsyncMock(return_value=episodes),
            ),
            patch.object(
                PodcastEpisode,
                "get_job_details_for_commands",
                new=AsyncMock(return_value=batch_result),
            ) as mock_batch,
            patch.object(
                PodcastEpisode, "get_job_detail", new=AsyncMock()
            ) as mock_per_episode,
        ):
            response = await list_podcast_episodes()

        mock_batch.assert_awaited_once()
        mock_per_episode.assert_not_called()
        assert len(response) == 5
        assert all(item.job_status == "completed" for item in response)

    @pytest.mark.asyncio
    async def test_episode_missing_from_batch_result_falls_back_to_unknown(self):
        """Mirrors the old per-episode except-block fallback: a command with
        no row (e.g. deleted) must not crash the whole listing."""
        episodes = [make_episode(command="command:missing", suffix="1")]

        with (
            patch(
                "api.routers.podcasts.PodcastService.list_episodes",
                new=AsyncMock(return_value=episodes),
            ),
            patch.object(
                PodcastEpisode,
                "get_job_details_for_commands",
                new=AsyncMock(return_value={}),
            ),
        ):
            response = await list_podcast_episodes()

        assert response[0].job_status == "unknown"

    @pytest.mark.asyncio
    async def test_total_batch_failure_falls_back_to_unknown_for_all(self):
        episodes = [
            make_episode(command=f"command:cmd{i}", suffix=str(i)) for i in range(3)
        ]

        with (
            patch(
                "api.routers.podcasts.PodcastService.list_episodes",
                new=AsyncMock(return_value=episodes),
            ),
            patch.object(
                PodcastEpisode,
                "get_job_details_for_commands",
                new=AsyncMock(side_effect=RuntimeError("db down")),
            ),
        ):
            response = await list_podcast_episodes()

        assert len(response) == 3
        assert all(item.job_status == "unknown" for item in response)

    @pytest.mark.asyncio
    async def test_episode_without_command_but_with_audio_is_completed(self):
        episode = make_episode(
            command=None, audio_file="/some/path.mp3", suffix="noaudiocmd"
        )

        with (
            patch(
                "api.routers.podcasts.PodcastService.list_episodes",
                new=AsyncMock(return_value=[episode]),
            ),
            patch.object(
                PodcastEpisode,
                "get_job_details_for_commands",
                new=AsyncMock(return_value={}),
            ) as mock_batch,
        ):
            response = await list_podcast_episodes()

        # No command anywhere -> batch call still happens (with an empty
        # list) but must not error, and the episode is reported completed.
        mock_batch.assert_awaited_once()
        assert response[0].job_status == "completed"

    @pytest.mark.asyncio
    async def test_episode_with_neither_command_nor_audio_is_skipped(self):
        episode = make_episode(command=None, audio_file=None, suffix="incomplete")

        with (
            patch(
                "api.routers.podcasts.PodcastService.list_episodes",
                new=AsyncMock(return_value=[episode]),
            ),
            patch.object(
                PodcastEpisode,
                "get_job_details_for_commands",
                new=AsyncMock(return_value={}),
            ),
        ):
            response = await list_podcast_episodes()

        assert response == []

    @pytest.mark.asyncio
    async def test_error_message_propagates_from_batch_result(self):
        episode = make_episode(command="command:err", suffix="err")
        batch_result = {
            "command:err": {"status": "failed", "error_message": "kaboom"}
        }

        with (
            patch(
                "api.routers.podcasts.PodcastService.list_episodes",
                new=AsyncMock(return_value=[episode]),
            ),
            patch.object(
                PodcastEpisode,
                "get_job_details_for_commands",
                new=AsyncMock(return_value=batch_result),
            ),
        ):
            response = await list_podcast_episodes()

        assert response[0].job_status == "failed"
        assert response[0].error_message == "kaboom"
