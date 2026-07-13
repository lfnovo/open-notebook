"""
Tests for episode snapshot model resolution (#1114).

Episode snapshots reference models by record ID (outline_llm, transcript_llm,
voice_model) since the legacy provider/model strings were dropped (#1112).
The podcast endpoints resolve those references to display fields
(outline_model_provider/outline_model_name etc.) at serialization time,
batched into one query per request (Model.get_display_info_for_ids) so a
page of episodes never triggers a per-row model lookup.
"""

from unittest.mock import AsyncMock, patch

import pytest

from api.routers.podcasts import get_podcast_episode, list_podcast_episodes
from open_notebook.ai.models import Model
from open_notebook.podcasts.models import PodcastEpisode

MODEL_INFO = {
    "model:outline": {"provider": "openai", "name": "gpt-4o"},
    "model:transcript": {"provider": "anthropic", "name": "claude-sonnet"},
    "model:voice": {"provider": "elevenlabs", "name": "eleven_turbo"},
}


def make_episode(episode_profile=None, speaker_profile=None, **overrides):
    defaults = dict(
        id=f"episode:{overrides.pop('suffix', 'x')}",
        name="Test Episode",
        episode_profile=episode_profile or {"name": "default"},
        speaker_profile=speaker_profile or {"name": "default"},
        briefing="briefing",
        content="content",
        command="command:job",
        audio_file=None,
    )
    defaults.update(overrides)
    return PodcastEpisode(**defaults)


def referenced_episode(suffix="ref"):
    return make_episode(
        suffix=suffix,
        episode_profile={
            "name": "modern",
            "outline_llm": "model:outline",
            "transcript_llm": "model:transcript",
        },
        speaker_profile={"name": "modern", "voice_model": "model:voice"},
    )


def legacy_episode(suffix="legacy"):
    return make_episode(
        suffix=suffix,
        episode_profile={
            "name": "legacy",
            "outline_provider": "openai",
            "outline_model": "gpt-3.5-turbo",
            "transcript_provider": "openai",
            "transcript_model": "gpt-4",
        },
        speaker_profile={
            "name": "legacy",
            "tts_provider": "openai",
            "tts_model": "tts-1",
        },
    )


def unresolvable_episode(suffix="gone"):
    return make_episode(
        suffix=suffix,
        episode_profile={
            "name": "orphaned",
            "outline_llm": "model:deleted",
            "transcript_llm": "model:deleted",
        },
        speaker_profile={"name": "orphaned", "voice_model": "model:deleted"},
    )


class TestGetDisplayInfoForIdsUnit:
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_without_querying(self):
        with patch(
            "open_notebook.ai.models.repo_query", new=AsyncMock()
        ) as mock_query:
            result = await Model.get_display_info_for_ids([])
        assert result == {}
        mock_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_query_for_multiple_ids(self):
        fake_rows = [
            {"id": "model:outline", "name": "gpt-4o", "provider": "openai"},
            {"id": "model:voice", "name": "eleven_turbo", "provider": "elevenlabs"},
        ]
        with patch(
            "open_notebook.ai.models.repo_query",
            new=AsyncMock(return_value=fake_rows),
        ) as mock_query:
            result = await Model.get_display_info_for_ids(
                ["model:outline", "model:voice"]
            )

        mock_query.assert_awaited_once()
        assert result == {
            "model:outline": {"provider": "openai", "name": "gpt-4o"},
            "model:voice": {"provider": "elevenlabs", "name": "eleven_turbo"},
        }

    @pytest.mark.asyncio
    async def test_duplicate_and_falsy_ids_are_deduped_and_filtered(self):
        with patch(
            "open_notebook.ai.models.repo_query", new=AsyncMock(return_value=[])
        ) as mock_query:
            await Model.get_display_info_for_ids(
                ["model:outline", "model:outline", None, ""]  # type: ignore[list-item]
            )

        bound_vars = mock_query.call_args.args[1]
        assert len(bound_vars["model_ids"]) == 1

    @pytest.mark.asyncio
    async def test_query_failure_returns_empty_dict_rather_than_raising(self):
        with patch(
            "open_notebook.ai.models.repo_query",
            new=AsyncMock(side_effect=RuntimeError("db down")),
        ):
            result = await Model.get_display_info_for_ids(["model:outline"])
        assert result == {}

    @pytest.mark.asyncio
    async def test_unresolvable_ids_are_absent_from_result(self):
        with patch(
            "open_notebook.ai.models.repo_query",
            new=AsyncMock(
                return_value=[
                    {"id": "model:outline", "name": "gpt-4o", "provider": "openai"}
                ]
            ),
        ):
            result = await Model.get_display_info_for_ids(
                ["model:outline", "model:deleted"]
            )
        assert "model:deleted" not in result
        assert "model:outline" in result


def _list_patches(episodes, display_info=MODEL_INFO):
    """Common patch set: episodes list, job-status batch, model batch."""
    return (
        patch(
            "api.routers.podcasts.PodcastService.list_episodes",
            new=AsyncMock(return_value=episodes),
        ),
        patch.object(
            PodcastEpisode,
            "get_job_details_for_commands",
            new=AsyncMock(return_value={}),
        ),
        patch.object(
            Model,
            "get_display_info_for_ids",
            new=AsyncMock(return_value=display_info),
        ),
    )


class TestListEpisodesModelResolution:
    @pytest.mark.asyncio
    async def test_referenced_episode_gets_resolved_display_fields(self):
        patches = _list_patches([referenced_episode()])
        with patches[0], patches[1], patches[2]:
            response = await list_podcast_episodes()

        ep = response[0].episode_profile
        sp = response[0].speaker_profile
        assert ep["outline_model_provider"] == "openai"
        assert ep["outline_model_name"] == "gpt-4o"
        assert ep["transcript_model_provider"] == "anthropic"
        assert ep["transcript_model_name"] == "claude-sonnet"
        assert sp["voice_model_provider"] == "elevenlabs"
        assert sp["voice_model_name"] == "eleven_turbo"

    @pytest.mark.asyncio
    async def test_legacy_episode_keeps_historical_strings_untouched(self):
        patches = _list_patches([legacy_episode()])
        with patches[0], patches[1], patches[2]:
            response = await list_podcast_episodes()

        ep = response[0].episode_profile
        sp = response[0].speaker_profile
        # Legacy strings survive; no resolved fields are invented.
        assert ep["outline_provider"] == "openai"
        assert ep["outline_model"] == "gpt-3.5-turbo"
        assert "outline_model_provider" not in ep
        assert "transcript_model_name" not in ep
        assert sp["tts_provider"] == "openai"
        assert "voice_model_name" not in sp

    @pytest.mark.asyncio
    async def test_unresolvable_reference_leaves_display_fields_absent(self):
        patches = _list_patches([unresolvable_episode()])
        with patches[0], patches[1], patches[2]:
            response = await list_podcast_episodes()

        ep = response[0].episode_profile
        sp = response[0].speaker_profile
        assert ep["outline_llm"] == "model:deleted"
        assert "outline_model_provider" not in ep
        assert "transcript_model_provider" not in ep
        assert "voice_model_provider" not in sp

    @pytest.mark.asyncio
    async def test_mixed_page_resolves_each_episode_appropriately(self):
        episodes = [
            referenced_episode("1"),
            legacy_episode("2"),
            unresolvable_episode("3"),
        ]
        patches = _list_patches(episodes)
        with patches[0], patches[1], patches[2]:
            response = await list_podcast_episodes()

        assert len(response) == 3
        assert response[0].episode_profile["outline_model_name"] == "gpt-4o"
        assert response[1].episode_profile["outline_model"] == "gpt-3.5-turbo"
        assert "outline_model_name" not in response[2].episode_profile

    @pytest.mark.asyncio
    async def test_batch_method_called_once_and_no_per_episode_model_get(self):
        """The N+1 guard: one batched resolution for the whole page, never a
        Model.get() per episode/reference."""
        episodes = [referenced_episode(str(i)) for i in range(5)]

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
            patch.object(
                Model,
                "get_display_info_for_ids",
                new=AsyncMock(return_value=MODEL_INFO),
            ) as mock_batch,
            patch.object(Model, "get", new=AsyncMock()) as mock_get,
        ):
            response = await list_podcast_episodes()

        mock_batch.assert_awaited_once()
        mock_get.assert_not_called()
        assert len(response) == 5
        # Distinct references across the page collapse into one sorted list.
        (ids,) = mock_batch.call_args.args
        assert ids == ["model:outline", "model:transcript", "model:voice"]

    @pytest.mark.asyncio
    async def test_resolution_failure_degrades_to_unresolved_fields(self):
        with (
            patch(
                "api.routers.podcasts.PodcastService.list_episodes",
                new=AsyncMock(return_value=[referenced_episode()]),
            ),
            patch.object(
                PodcastEpisode,
                "get_job_details_for_commands",
                new=AsyncMock(return_value={}),
            ),
            patch.object(
                Model,
                "get_display_info_for_ids",
                new=AsyncMock(side_effect=RuntimeError("db down")),
            ),
        ):
            response = await list_podcast_episodes()

        assert len(response) == 1
        assert "outline_model_provider" not in response[0].episode_profile


class TestGetEpisodeModelResolution:
    @pytest.mark.asyncio
    async def test_single_episode_gets_resolved_display_fields(self):
        episode = referenced_episode()

        with (
            patch(
                "api.routers.podcasts.PodcastService.get_episode",
                new=AsyncMock(return_value=episode),
            ),
            patch.object(
                PodcastEpisode,
                "get_job_detail",
                new=AsyncMock(
                    return_value={"status": "completed", "error_message": None}
                ),
            ),
            patch.object(
                Model,
                "get_display_info_for_ids",
                new=AsyncMock(return_value=MODEL_INFO),
            ) as mock_batch,
        ):
            response = await get_podcast_episode("episode:ref")

        mock_batch.assert_awaited_once()
        assert response.episode_profile["outline_model_name"] == "gpt-4o"
        assert response.speaker_profile["voice_model_provider"] == "elevenlabs"
