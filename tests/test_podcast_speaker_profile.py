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
    pick_voice_model,
)
from open_notebook.ai.models import DefaultModels
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


def patch_default_tts(model_id=None):
    """Patch the Default Models lookup so command tests never hit the DB.

    generate_podcast_command reads the Default Text-to-Speech Model (#1467);
    model_id=None means no default is set.
    """
    return patch.object(
        DefaultModels,
        "get_instance",
        new=AsyncMock(return_value=Mock(default_text_to_speech_model=model_id)),
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
                match="references a speaker profile that no longer exists",
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
            with pytest.raises(ValueError, match="has no speaker profile configured"):
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


class TestOrphanedProfileDoesNotPoisonConfig:
    """One orphaned episode profile (speaker_config=None after migration 20)
    must not fail podcast-creator's validation of the whole episode config,
    and the profile dicts handed to podcast-creator must carry speaker NAMES
    (its contract), not record IDs."""

    @pytest.mark.asyncio
    async def test_orphan_dropped_and_ids_rewritten_to_names(self, tmp_path):
        episode_profile = EpisodeProfile(
            id="episode_profile:ep1",
            name="Test Episode Profile",
            speaker_config="speaker_profile:sp1",
            outline_llm="model:llm",
            transcript_llm="model:llm",
            default_briefing="brief",
            num_segments=3,
        )
        speaker_profile = SpeakerProfile(
            id="speaker_profile:sp1",
            name="Tech Experts",
            voice_model="model:tts",
            speakers=[
                {
                    "name": "Alex",
                    "voice_id": "v1",
                    "backstory": "b",
                    "personality": "p",
                }
            ],
        )

        episode_rows = [
            {
                "id": "episode_profile:ep1",
                "name": "Test Episode Profile",
                "speaker_config": "speaker_profile:sp1",
                "default_briefing": "brief",
                "num_segments": 3,
            },
            {
                # Orphaned by migration 20: referenced speaker no longer exists
                "id": "episode_profile:ep2",
                "name": "Orphaned Profile",
                "speaker_config": None,
                "default_briefing": "brief",
                "num_segments": 3,
            },
        ]
        speaker_rows = [{"id": "speaker_profile:sp1", "name": "Tech Experts"}]

        async def fake_repo_query(query, *args, **kwargs):
            if "episode_profile" in query:
                return episode_rows
            return speaker_rows

        configure_calls = {}

        def fake_configure(key, value):
            configure_calls[key] = value

        resolved: tuple = ("openai", "model-name", {})

        with (
            patch_default_tts(),
            patch.object(
                EpisodeProfile,
                "get_by_name",
                new=AsyncMock(return_value=episode_profile),
            ),
            patch.object(
                SpeakerProfile,
                "resolve",
                new=AsyncMock(return_value=speaker_profile),
            ),
            patch(
                "open_notebook.podcasts.models._resolve_model_config",
                new=AsyncMock(return_value=resolved),
            ),
            patch(
                "commands.podcast_commands._resolve_model_config",
                new=AsyncMock(return_value=resolved),
            ),
            patch("commands.podcast_commands.repo_query", new=fake_repo_query),
            patch("commands.podcast_commands.configure", new=fake_configure),
            patch(
                "commands.podcast_commands.create_podcast",
                new=AsyncMock(
                    return_value={
                        "final_output_file_path": str(
                            tmp_path / "episodes" / "ep-dir" / "out.mp3"
                        ),
                        "transcript": {},
                        "outline": {},
                    }
                ),
            ),
            # audio_file is stored relative to PODCASTS_FOLDER and validated
            # at write time (#1030), so the fake output path must live under
            # the (patched) podcasts root.
            patch(
                "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER",
                str(tmp_path),
            ),
            patch(
                "commands.podcast_commands.build_episode_output_dir",
                new=lambda *args: ("ep-dir", tmp_path / "ep-dir"),
            ),
            patch(
                "open_notebook.podcasts.models.PodcastEpisode.save",
                new=AsyncMock(),
            ),
        ):
            result = await generate_podcast_command(make_input())

        assert result.success is True
        # The stored/reported audio path is relative to PODCASTS_FOLDER (#1030)
        assert result.audio_file_path == "episodes/ep-dir/out.mp3"
        episode_config = configure_calls["episode_config"]["profiles"]
        # Orphaned profile removed instead of poisoning validation
        assert "Orphaned Profile" not in episode_config
        # Record ID rewritten to the speaker profile NAME for podcast-creator
        assert (
            episode_config["Test Episode Profile"]["speaker_config"] == "Tech Experts"
        )


class TestUnconfiguredSpeakerProfileDoesNotPoisonConfig:
    """A speaker profile without a voice model (the seeded ones ship that way)
    must not fail podcast-creator's validation of the whole speakers config
    when generating with a different, complete profile (#1450). With no default Text-to-Speech model set, it is dropped from the config."""

    @pytest.mark.asyncio
    async def test_unconfigured_profile_dropped_selected_kept(self, tmp_path):
        episode_profile = EpisodeProfile(
            id="episode_profile:ep1",
            name="Test Episode Profile",
            speaker_config="speaker_profile:sp1",
            outline_llm="model:llm",
            transcript_llm="model:llm",
            default_briefing="brief",
            num_segments=3,
        )
        speaker = {
            "name": "Alex",
            "voice_id": "v1",
            "backstory": "b",
            "personality": "p",
        }
        speaker_profile = SpeakerProfile(
            id="speaker_profile:sp1",
            name="Tech Experts",
            voice_model="model:tts",
            speakers=[speaker],
        )
        episode_rows = [
            {
                "id": "episode_profile:ep1",
                "name": "Test Episode Profile",
                "speaker_config": "speaker_profile:sp1",
                "default_briefing": "brief",
                "num_segments": 3,
            },
        ]
        speaker_rows = [
            {
                "id": "speaker_profile:sp1",
                "name": "Tech Experts",
                "voice_model": "model:tts",
                "speakers": [dict(speaker)],
            },
            {
                # Seeded profile nobody configured yet
                "id": "speaker_profile:sp2",
                "name": "business_panel",
                "voice_model": None,
                "speakers": [dict(speaker)],
            },
        ]

        async def fake_repo_query(query, *args, **kwargs):
            if "episode_profile" in query:
                return episode_rows
            return speaker_rows

        configure_calls = {}

        def fake_configure(key, value):
            configure_calls[key] = value

        resolved: tuple = ("openai", "model-name", {})

        with (
            patch_default_tts(),
            patch.object(
                EpisodeProfile,
                "get_by_name",
                new=AsyncMock(return_value=episode_profile),
            ),
            patch.object(
                SpeakerProfile, "resolve", new=AsyncMock(return_value=speaker_profile)
            ),
            patch(
                "open_notebook.podcasts.models._resolve_model_config",
                new=AsyncMock(return_value=resolved),
            ),
            patch(
                "commands.podcast_commands._resolve_model_config",
                new=AsyncMock(return_value=resolved),
            ),
            patch("commands.podcast_commands.repo_query", new=fake_repo_query),
            patch("commands.podcast_commands.configure", new=fake_configure),
            patch(
                "commands.podcast_commands.create_podcast",
                new=AsyncMock(
                    return_value={
                        "final_output_file_path": str(
                            tmp_path / "episodes" / "ep-dir" / "out.mp3"
                        ),
                        "transcript": {},
                        "outline": {},
                    }
                ),
            ),
            patch("open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(tmp_path)),
            patch(
                "commands.podcast_commands.build_episode_output_dir",
                new=lambda *args: ("ep-dir", tmp_path / "ep-dir"),
            ),
            patch("open_notebook.podcasts.models.PodcastEpisode.save", new=AsyncMock()),
        ):
            result = await generate_podcast_command(make_input())

        assert result.success is True
        speakers_config = configure_calls["speakers_config"]["profiles"]
        assert "business_panel" not in speakers_config
        assert speakers_config["Tech Experts"]["tts_provider"] == "openai"

        # The whole config passes podcast-creator's own validation.
        from podcast_creator.speakers import SpeakerConfig

        SpeakerConfig(profiles=speakers_config)


class TestPickVoiceModel:
    """The speaker profile's own voice model wins, the Default Text-to-Speech
    Model is the fallback, and having neither is a clear error (#1467)."""

    def test_profile_voice_model_wins_over_default(self):
        assert pick_voice_model("p", "model:own", "model:default") == "model:own"

    def test_default_used_when_profile_has_none(self):
        assert pick_voice_model("p", None, "model:default") == "model:default"

    def test_error_names_both_places_when_neither_is_set(self):
        with pytest.raises(ValueError) as exc_info:
            pick_voice_model("solo_expert", None, None)

        message = str(exc_info.value)
        assert "solo_expert" in message
        assert "speaker profile" in message
        assert "Manage -> Models" in message


SPEAKER = {"name": "Alex", "voice_id": "v1", "backstory": "b", "personality": "p"}


async def run_generation(tmp_path, speaker_profile, speaker_rows, default_tts):
    """Run generate_podcast_command with every external call mocked.

    Returns the command result, the configs handed to podcast-creator and the
    _resolve_model_config mock (to check which model IDs were resolved).
    """

    episode_profile = EpisodeProfile(
        id="episode_profile:ep1",
        name="Test Episode Profile",
        speaker_config=str(speaker_profile.id),
        outline_llm="model:llm",
        transcript_llm="model:llm",
        default_briefing="brief",
        num_segments=3,
    )
    episode_rows = [
        {
            "id": "episode_profile:ep1",
            "name": "Test Episode Profile",
            "speaker_config": str(speaker_profile.id),
            "default_briefing": "brief",
            "num_segments": 3,
        }
    ]

    async def fake_repo_query(query, *args, **kwargs):
        if "episode_profile" in query:
            return episode_rows
        return speaker_rows

    configure_calls = {}

    def fake_configure(key, value):
        configure_calls[key] = value

    resolve = AsyncMock(return_value=("openai", "model-name", {}))

    with (
        patch_default_tts(default_tts),
        patch.object(
            EpisodeProfile, "get_by_name", new=AsyncMock(return_value=episode_profile)
        ),
        patch.object(
            SpeakerProfile, "resolve", new=AsyncMock(return_value=speaker_profile)
        ),
        patch("open_notebook.podcasts.models._resolve_model_config", new=resolve),
        patch("commands.podcast_commands._resolve_model_config", new=resolve),
        patch("commands.podcast_commands.repo_query", new=fake_repo_query),
        patch("commands.podcast_commands.configure", new=fake_configure),
        patch(
            "commands.podcast_commands.create_podcast",
            new=AsyncMock(
                return_value={
                    "final_output_file_path": str(
                        tmp_path / "episodes" / "ep-dir" / "out.mp3"
                    ),
                    "transcript": {},
                    "outline": {},
                }
            ),
        ),
        patch("open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(tmp_path)),
        patch(
            "commands.podcast_commands.build_episode_output_dir",
            new=lambda *args: ("ep-dir", tmp_path / "ep-dir"),
        ),
        patch("open_notebook.podcasts.models.PodcastEpisode.save", new=AsyncMock()),
    ):
        result = await generate_podcast_command(make_input())

    return result, configure_calls, resolve


class TestDefaultTextToSpeechModel:
    """Podcasts fall back to the Default Text-to-Speech Model when a speaker
    profile has no voice model of its own (#1467)."""

    @pytest.mark.asyncio
    async def test_selected_profile_without_voice_model_uses_default(self, tmp_path):
        speaker_profile = SpeakerProfile(
            id="speaker_profile:sp1",
            name="solo_expert",
            voice_model=None,
            speakers=[SPEAKER],
        )

        speaker_rows = [
            {
                "id": "speaker_profile:sp1",
                "name": "solo_expert",
                "voice_model": None,
                "speakers": [dict(SPEAKER)],
            }
        ]

        result, configure_calls, resolve = await run_generation(
            tmp_path, speaker_profile, speaker_rows, default_tts="model:default_tts"
        )

        assert result.success is True
        resolve.assert_any_await("model:default_tts")
        speakers_config = configure_calls["speakers_config"]["profiles"]
        assert speakers_config["solo_expert"]["tts_provider"] == "openai"

        from podcast_creator.speakers import SpeakerConfig

        SpeakerConfig(profiles=speakers_config)

    @pytest.mark.asyncio
    async def test_unrelated_profile_without_voice_model_kept_with_default(
        self, tmp_path
    ):
        speaker_profile = SpeakerProfile(
            id="speaker_profile:sp1",
            name="Tech Experts",
            voice_model="model:tts",
            speakers=[SPEAKER],
        )

        speaker_rows = [
            {
                "id": "speaker_profile:sp1",
                "name": "Tech Experts",
                "voice_model": "model:tts",
                "speakers": [dict(SPEAKER)],
            },
            {
                "id": "speaker_profile:sp2",
                "name": "business_panel",
                "voice_model": None,
                "speakers": [dict(SPEAKER)],
            },
        ]

        result, configure_calls, resolve = await run_generation(
            tmp_path, speaker_profile, speaker_rows, default_tts="model:default_tts"
        )

        assert result.success is True
        speakers_config = configure_calls["speakers_config"]["profiles"]
        # Kept and voiced by the default instead of being dropped
        assert speakers_config["business_panel"]["tts_provider"] == "openai"
        # The selected profile still uses its own voice model
        resolve.assert_any_await("model:tts")
        resolve.assert_any_await("model:default_tts")

    @pytest.mark.asyncio
    async def test_no_voice_model_and_no_default_is_a_clear_error(self):
        speaker_profile = SpeakerProfile(
            id="speaker_profile:sp1",
            name="solo_expert",
            voice_model=None,
            speakers=[SPEAKER],
        )

        episode_profile = make_episode_profile(speaker_config="speaker_profile:sp1")
        episode_profile.outline_llm = "model:llm"
        episode_profile.transcript_llm = "model:llm"

        with (
            patch_default_tts(None),
            patch.object(
                EpisodeProfile,
                "get_by_name",
                new=AsyncMock(return_value=episode_profile),
            ),
            patch.object(
                SpeakerProfile, "resolve", new=AsyncMock(return_value=speaker_profile)
            ),
        ):
            with pytest.raises(ValueError) as exc_info:
                await generate_podcast_command(make_input())

        message = str(exc_info.value)
        assert "solo_expert" in message
        assert "default Text-to-Speech model" in message
