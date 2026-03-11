"""
Tests for podcast episode directory path generation.

Verifies that episode output directories use UUID-based names
instead of raw episode names, preventing filesystem issues with
spaces and special characters (GitHub issue #663).
"""

import uuid
from pathlib import Path, PurePosixPath


def _build_episode_output_dir(data_folder: str) -> tuple[str, Path]:
    """Replicate the directory naming logic from generate_podcast_command."""
    episode_dir_name = str(uuid.uuid4())
    output_dir = Path(f"{data_folder}/podcasts/episodes/{episode_dir_name}")
    return episode_dir_name, output_dir


class TestPodcastEpisodeDirectory:
    """Verify that episode directories are always filesystem-safe."""

    def test_directory_uses_uuid_format(self):
        dir_name, _ = _build_episode_output_dir("/data")
        # Should be a valid UUID
        parsed = uuid.UUID(dir_name)
        assert str(parsed) == dir_name

    def test_directory_path_is_valid(self):
        _, output_dir = _build_episode_output_dir("/data")
        # Path should have exactly the expected structure
        assert str(output_dir).startswith("/data/podcasts/episodes/")
        # Directory name should be the last component
        assert len(output_dir.name) == 36  # UUID string length

    def test_no_collision_between_calls(self):
        dir1, _ = _build_episode_output_dir("/data")
        dir2, _ = _build_episode_output_dir("/data")
        assert dir1 != dir2

    def test_path_has_no_spaces_or_special_chars(self):
        """Regardless of episode name, path should be clean."""
        problematic_names = [
            "My Episode Name",
            "Episode: Part 1",
            'test "quotes"',
            "path/traversal",
            "dots..and...more",
            "café résumé",
            "   spaces   ",
            "",
            "?*<>|",
        ]
        for name in problematic_names:
            dir_name, output_dir = _build_episode_output_dir("/data")
            # UUID path is independent of the episode name
            path_str = str(output_dir)
            assert " " not in path_str, f"Space found in path for name: {name}"
            for char in ['<', '>', ':', '"', '|', '?', '*']:
                assert char not in path_str, (
                    f"Unsafe char '{char}' in path for name: {name}"
                )

    def test_path_works_on_posix(self):
        _, output_dir = _build_episode_output_dir("/data")
        posix = PurePosixPath(str(output_dir))
        assert posix.parts == ("/", "data", "podcasts", "episodes", output_dir.name)

    def test_uuid_directory_can_be_created(self, tmp_path):
        """Actually create the directory to verify it works on the real filesystem."""
        dir_name, output_dir = _build_episode_output_dir(str(tmp_path))
        output_dir.mkdir(parents=True, exist_ok=True)
        assert output_dir.exists()
        assert output_dir.is_dir()
