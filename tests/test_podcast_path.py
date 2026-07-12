"""
Tests for podcast episode directory path generation.

Verifies that episode output directories use UUID-based names
instead of raw episode names, preventing filesystem issues with
spaces and special characters (GitHub issue #663).
"""

import uuid
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from commands.podcast_commands import build_episode_output_dir
from open_notebook.podcasts.models import EpisodeProfile, _resolve_model_config


class TestBuildEpisodeOutputDir:
    """Test the actual production helper that builds episode output paths."""

    def test_directory_name_is_valid_uuid(self):
        dir_name, _ = build_episode_output_dir("/data/podcasts")
        parsed = uuid.UUID(dir_name)
        assert str(parsed) == dir_name

    def test_path_structure(self):
        dir_name, output_dir = build_episode_output_dir("/data/podcasts")
        assert str(output_dir) == f"/data/podcasts/episodes/{dir_name}"

    def test_defaults_to_podcasts_folder(self):
        """No-arg form builds under PODCASTS_FOLDER - the same root the
        write-time validation (to_relative_audio_path) checks against."""
        from open_notebook.config import PODCASTS_FOLDER

        dir_name, output_dir = build_episode_output_dir()
        assert str(output_dir) == str(
            Path(PODCASTS_FOLDER) / "episodes" / dir_name
        )

    def test_no_collision_between_calls(self):
        dir1, _ = build_episode_output_dir("/data/podcasts")
        dir2, _ = build_episode_output_dir("/data/podcasts")
        assert dir1 != dir2

    def test_path_is_independent_of_episode_name(self):
        """The returned path must never contain user-supplied episode names.

        Since build_episode_output_dir does not accept an episode name at all,
        any name the user types is structurally excluded from the path.
        """
        problematic_names = [
            "My Episode Name",
            "Episode: Part 1",
            'test "quotes"',
            "path/traversal",
            "café résumé",
            "   spaces   ",
            "?*<>|",
        ]
        for name in problematic_names:
            _, output_dir = build_episode_output_dir("/data/podcasts")
            path_str = str(output_dir)
            # The episode name must not appear anywhere in the path
            assert name not in path_str
            # UUID paths contain only hex digits and hyphens after the base
            dir_component = output_dir.name
            assert all(c in "0123456789abcdef-" for c in dir_component), (
                f"Unexpected chars in directory name: {dir_component}"
            )

    def test_path_works_on_posix(self):
        dir_name, output_dir = build_episode_output_dir("/data/podcasts")
        posix = PurePosixPath(str(output_dir))
        assert posix.parts == ("/", "data", "podcasts", "episodes", dir_name)

    def test_directory_can_be_created(self, tmp_path):
        """Create the directory on the real filesystem."""
        _, output_dir = build_episode_output_dir(str(tmp_path))
        output_dir.mkdir(parents=True, exist_ok=True)
        assert output_dir.exists()
        assert output_dir.is_dir()


class TestResolveModelConfigMaxTokens:
    """Test max_tokens passthrough without database access."""

    @pytest.mark.asyncio
    async def test_includes_max_tokens_when_configured(self):
        fake_model = SimpleNamespace(
            provider="anthropic",
            name="claude-sonnet-4",
            credential=None,
        )

        with (
            patch(
                "open_notebook.ai.models.Model.get",
                new=AsyncMock(return_value=fake_model),
            ),
            patch(
                "open_notebook.ai.key_provider.provision_provider_keys",
                new=AsyncMock(return_value=True),
            ),
        ):
            provider, model_name, config = await _resolve_model_config(
                "model:test", max_tokens=12000
            )

        assert provider == "anthropic"
        assert model_name == "claude-sonnet-4"
        assert config["max_tokens"] == 12000

    @pytest.mark.asyncio
    async def test_omits_max_tokens_when_not_configured(self):
        fake_model = SimpleNamespace(
            provider="anthropic",
            name="claude-sonnet-4",
            credential=None,
        )

        with (
            patch(
                "open_notebook.ai.models.Model.get",
                new=AsyncMock(return_value=fake_model),
            ),
            patch(
                "open_notebook.ai.key_provider.provision_provider_keys",
                new=AsyncMock(return_value=True),
            ),
        ):
            _, _, config = await _resolve_model_config("model:test")

        assert "max_tokens" not in config


class TestEpisodeProfileMaxTokens:
    """Test EpisodeProfile accepts optional max_tokens."""

    def test_accepts_max_tokens(self):
        profile = EpisodeProfile(
            name="Long Form",
            speaker_config="default",
            default_briefing="Test briefing",
            max_tokens=12000,
        )

        assert profile.max_tokens == 12000

    def test_max_tokens_defaults_to_none(self):
        profile = EpisodeProfile(
            name="Default",
            speaker_config="default",
            default_briefing="Test briefing",
        )

        assert profile.max_tokens is None
