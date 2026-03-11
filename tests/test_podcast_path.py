"""
Tests for podcast episode directory path generation.

Verifies that episode output directories use UUID-based names
instead of raw episode names, preventing filesystem issues with
spaces and special characters (GitHub issue #663).
"""

import uuid
from pathlib import PurePosixPath

from commands.podcast_commands import build_episode_output_dir


class TestBuildEpisodeOutputDir:
    """Test the actual production helper that builds episode output paths."""

    def test_directory_name_is_valid_uuid(self):
        dir_name, _ = build_episode_output_dir("/data")
        parsed = uuid.UUID(dir_name)
        assert str(parsed) == dir_name

    def test_path_structure(self):
        dir_name, output_dir = build_episode_output_dir("/data")
        assert str(output_dir) == f"/data/podcasts/episodes/{dir_name}"

    def test_no_collision_between_calls(self):
        dir1, _ = build_episode_output_dir("/data")
        dir2, _ = build_episode_output_dir("/data")
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
            _, output_dir = build_episode_output_dir("/data")
            path_str = str(output_dir)
            # The episode name must not appear anywhere in the path
            assert name not in path_str
            # UUID paths contain only hex digits and hyphens after the base
            dir_component = output_dir.name
            assert all(c in "0123456789abcdef-" for c in dir_component), (
                f"Unexpected chars in directory name: {dir_component}"
            )

    def test_path_works_on_posix(self):
        dir_name, output_dir = build_episode_output_dir("/data")
        posix = PurePosixPath(str(output_dir))
        assert posix.parts == ("/", "data", "podcasts", "episodes", dir_name)

    def test_directory_can_be_created(self, tmp_path):
        """Create the directory on the real filesystem."""
        _, output_dir = build_episode_output_dir(str(tmp_path))
        output_dir.mkdir(parents=True, exist_ok=True)
        assert output_dir.exists()
        assert output_dir.is_dir()
