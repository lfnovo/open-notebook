"""
Regression tests for issue #1044: generate_podcast_command must honor the
speaker_profile parameter instead of always re-deriving the speaker from
episode_profile.speaker_config.

No database is available in tests: EpisodeProfile.get_by_name and
SpeakerProfile.get_by_name are mocked. Each test lets the command fail at a
deterministic early exit (speaker not found) so the assertion is purely about
WHICH speaker profile name the command tried to resolve.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from commands.podcast_commands import (
    PodcastGenerationInput,
    generate_podcast_command,
)
from open_notebook.podcasts.models import EpisodeProfile, SpeakerProfile


def make_episode_profile(speaker_config="profile-from-episode"):
    profile = Mock()
    profile.name = "Test Episode Profile"
    profile.speaker_config = speaker_config
    return profile


def make_input(speaker_profile=None):
    return PodcastGenerationInput(
        episode_profile="Test Episode Profile",
        speaker_profile=speaker_profile,
        episode_name="Test Episode",
        content="test content",
    )


class TestSpeakerProfileResolution:
    @pytest.mark.asyncio
    async def test_provided_speaker_profile_wins_over_episode_config(self):
        """An explicitly provided speaker_profile is resolved, not the
        episode profile's speaker_config."""
        episode_profile = make_episode_profile(speaker_config="old-name")
        speaker_get = AsyncMock(return_value=None)

        with (
            patch.object(
                EpisodeProfile,
                "get_by_name",
                new=AsyncMock(return_value=episode_profile),
            ),
            patch.object(SpeakerProfile, "get_by_name", new=speaker_get),
        ):
            with pytest.raises(
                ValueError, match="Speaker profile 'new-name' not found"
            ):
                await generate_podcast_command(make_input(speaker_profile="new-name"))

        speaker_get.assert_awaited_once_with("new-name")

    @pytest.mark.asyncio
    async def test_falls_back_to_episode_speaker_config_when_omitted(self):
        """Without an explicit speaker_profile, the episode profile's
        speaker_config is used."""
        episode_profile = make_episode_profile(speaker_config="old-name")
        speaker_get = AsyncMock(return_value=None)

        with (
            patch.object(
                EpisodeProfile,
                "get_by_name",
                new=AsyncMock(return_value=episode_profile),
            ),
            patch.object(SpeakerProfile, "get_by_name", new=speaker_get),
        ):
            with pytest.raises(
                ValueError, match="Speaker profile 'old-name' not found"
            ):
                await generate_podcast_command(make_input(speaker_profile=None))

        speaker_get.assert_awaited_once_with("old-name")

    def test_speaker_profile_is_optional_on_input_model(self):
        """The command contract allows omitting speaker_profile entirely."""
        input_data = PodcastGenerationInput(
            episode_profile="Test Episode Profile",
            episode_name="Test Episode",
            content="test content",
        )
        assert input_data.speaker_profile is None
