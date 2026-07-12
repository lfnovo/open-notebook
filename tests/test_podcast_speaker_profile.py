"""
Regression tests for issues #1044 and #630.

#1044: generate_podcast_command must honor the speaker_profile parameter
instead of always re-deriving the speaker from episode_profile.speaker_config.

#630: episode_profile.speaker_config references the speaker profile by
record ID (migration 20) instead of by name, so renaming a speaker profile
no longer breaks episode profiles. The command resolves either form via
SpeakerProfile.resolve, and the API boundary (PodcastService) resolves the
user-facing name to a record ID before submitting the job.

No database is available in tests: profile lookups are mocked. Command tests
let the command fail at a deterministic early exit (speaker not found) so the
assertion is purely about WHICH speaker profile reference was resolved.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from commands.podcast_commands import (
    PodcastGenerationInput,
    generate_podcast_command,
)
from open_notebook.podcasts.models import EpisodeProfile, SpeakerProfile


def make_episode_profile(speaker_config="speaker_profile:from_episode"):
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
        episode_profile = make_episode_profile(
            speaker_config="speaker_profile:old_speaker"
        )
        speaker_resolve = AsyncMock(return_value=None)

        with (
            patch.object(
                EpisodeProfile,
                "get_by_name",
                new=AsyncMock(return_value=episode_profile),
            ),
            patch.object(SpeakerProfile, "resolve", new=speaker_resolve),
        ):
            with pytest.raises(
                ValueError, match="Speaker profile 'new-name' not found"
            ):
                await generate_podcast_command(make_input(speaker_profile="new-name"))

        speaker_resolve.assert_awaited_once_with("new-name")

    @pytest.mark.asyncio
    async def test_falls_back_to_episode_speaker_config_when_omitted(self):
        """Without an explicit speaker_profile, the episode profile's
        speaker_config (a record ID) is used."""
        episode_profile = make_episode_profile(
            speaker_config="speaker_profile:old_speaker"
        )
        speaker_resolve = AsyncMock(return_value=None)

        with (
            patch.object(
                EpisodeProfile,
                "get_by_name",
                new=AsyncMock(return_value=episode_profile),
            ),
            patch.object(SpeakerProfile, "resolve", new=speaker_resolve),
        ):
            with pytest.raises(
                ValueError,
                match="Speaker profile 'speaker_profile:old_speaker' not found",
            ):
                await generate_podcast_command(make_input(speaker_profile=None))

        speaker_resolve.assert_awaited_once_with("speaker_profile:old_speaker")

    @pytest.mark.asyncio
    async def test_orphaned_speaker_config_fails_with_clear_error(self):
        """An episode profile whose speaker reference was orphaned by
        migration 20 (speaker_config is None) fails with a clear message
        instead of trying to resolve None."""
        episode_profile = make_episode_profile(speaker_config=None)
        speaker_resolve = AsyncMock(return_value=None)

        with (
            patch.object(
                EpisodeProfile,
                "get_by_name",
                new=AsyncMock(return_value=episode_profile),
            ),
            patch.object(SpeakerProfile, "resolve", new=speaker_resolve),
        ):
            with pytest.raises(
                ValueError, match="has no speaker profile configured"
            ):
                await generate_podcast_command(make_input(speaker_profile=None))

        speaker_resolve.assert_not_awaited()

    def test_speaker_profile_is_optional_on_input_model(self):
        """The command contract allows omitting speaker_profile entirely."""
        input_data = PodcastGenerationInput(
            episode_profile="Test Episode Profile",
            episode_name="Test Episode",
            content="test content",
        )
        assert input_data.speaker_profile is None


class TestSpeakerProfileResolve:
    """SpeakerProfile.resolve dispatches record IDs to a direct lookup and
    anything else to the name lookup."""

    @pytest.mark.asyncio
    async def test_resolve_by_record_id_queries_by_id(self):
        with patch(
            "open_notebook.podcasts.models.repo_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = [
                {
                    "id": "speaker_profile:abc",
                    "name": "Tech Experts",
                    "speakers": [
                        {
                            "name": "Alex",
                            "voice_id": "v1",
                            "backstory": "b",
                            "personality": "p",
                        }
                    ],
                }
            ]
            profile = await SpeakerProfile.resolve("speaker_profile:abc")

        assert profile is not None
        assert profile.name == "Tech Experts"
        assert mock_query.await_args is not None
        query, params = mock_query.await_args.args
        assert "FROM $id" in query
        assert str(params["id"]) == "speaker_profile:abc"

    @pytest.mark.asyncio
    async def test_resolve_by_record_id_returns_none_when_missing(self):
        with patch(
            "open_notebook.podcasts.models.repo_query", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = []
            profile = await SpeakerProfile.resolve("speaker_profile:gone")

        assert profile is None

    @pytest.mark.asyncio
    async def test_resolve_by_name_delegates_to_get_by_name(self):
        with patch.object(
            SpeakerProfile, "get_by_name", new_callable=AsyncMock
        ) as mock_get_by_name:
            mock_get_by_name.return_value = None
            profile = await SpeakerProfile.resolve("Tech Experts")

        assert profile is None
        mock_get_by_name.assert_awaited_once_with("Tech Experts")


class TestApiBoundaryResolvesNameToRecordId:
    """PodcastService.submit_generation_job accepts the speaker profile by
    NAME (the public API contract) and submits the command with the resolved
    record ID."""

    @pytest.mark.asyncio
    async def test_submit_passes_record_id_to_command(self):
        from api.podcast_service import PodcastService

        episode_profile = Mock()
        episode_profile.name = "Deep Dive"
        speaker_profile = Mock()
        speaker_profile.id = "speaker_profile:abc"
        speaker_profile.name = "Tech Experts"

        with (
            patch(
                "api.podcast_service.EpisodeProfile.get_by_name",
                new=AsyncMock(return_value=episode_profile),
            ),
            patch(
                "api.podcast_service.SpeakerProfile.resolve",
                new=AsyncMock(return_value=speaker_profile),
            ) as mock_resolve,
            patch("api.podcast_service.submit_command") as mock_submit,
        ):
            mock_submit.return_value = "command:job1"
            job_id = await PodcastService.submit_generation_job(
                episode_profile_name="Deep Dive",
                speaker_profile_name="Tech Experts",
                episode_name="Episode 1",
                content="some content",
            )

        assert job_id == "command:job1"
        mock_resolve.assert_awaited_once_with("Tech Experts")
        command_args = mock_submit.call_args.args[2]
        assert command_args["speaker_profile"] == "speaker_profile:abc"


class TestMigration20:
    """Migration 20 converts speaker_config from name string to record link.

    Migrations are hard-coded in AsyncMigrationManager, not discovered, so
    these tests guard both the SQL content and the registration."""

    def test_migration_converts_names_and_tightens_type(self):
        from pathlib import Path

        sql = (
            Path(__file__).parent.parent
            / "open_notebook"
            / "database"
            / "migrations"
            / "20.surrealql"
        ).read_text()
        assert (
            "UPDATE episode_profile SET speaker_config = "
            "(SELECT VALUE id FROM ONLY speaker_profile "
            "WHERE name = $parent.speaker_config LIMIT 1) "
            "WHERE type::is::string(speaker_config)" in sql
        )
        assert (
            "DEFINE FIELD OVERWRITE speaker_config ON TABLE episode_profile "
            "TYPE option<record<speaker_profile>>" in sql
        )

    def test_migration_down_restores_names(self):
        from pathlib import Path

        sql = (
            Path(__file__).parent.parent
            / "open_notebook"
            / "database"
            / "migrations"
            / "20_down.surrealql"
        ).read_text()
        assert (
            "UPDATE episode_profile SET speaker_config = speaker_config.name "
            "WHERE type::is::record(speaker_config)" in sql
        )
        assert (
            "DEFINE FIELD OVERWRITE speaker_config ON TABLE episode_profile "
            "TYPE option<string>" in sql
        )

    def test_migration_is_registered_in_manager(self):
        from open_notebook.database.async_migrate import AsyncMigrationManager

        manager = AsyncMigrationManager()
        assert len(manager.up_migrations) >= 20
        assert len(manager.up_migrations) == len(manager.down_migrations)
        assert "speaker_config" in manager.up_migrations[19].sql
        assert "option<record<speaker_profile>>" in manager.up_migrations[19].sql
        assert "speaker_config.name" in manager.down_migrations[19].sql
