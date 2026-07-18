"""
Tests for the write side of the podcast audio path contract (#1030) and for
the migration that converts pre-existing rows.

`to_relative_audio_path()` is what the generation command stores into
`PodcastEpisode.audio_file`: always relative to PODCASTS_FOLDER, never
absolute, never escaping - validated at write time so the DB can't hold a
bad value. Migration 21 rewrites historical absolute/`file://` rows to the
same form.
"""

from pathlib import Path

import pytest

from open_notebook.podcasts.audio_paths import (
    podcasts_root,
    to_relative_audio_path,
)


class TestToRelativeAudioPath:
    def test_absolute_path_under_root_becomes_relative(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(tmp_path)
        )
        audio = tmp_path / "episodes" / "uuid-1" / "audio" / "uuid-1.mp3"

        assert to_relative_audio_path(str(audio)) == "episodes/uuid-1/audio/uuid-1.mp3"

    def test_accepts_path_objects(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(tmp_path)
        )
        audio = tmp_path / "episodes" / "uuid-2" / "a.mp3"

        assert to_relative_audio_path(audio) == "episodes/uuid-2/a.mp3"

    def test_file_uri_under_root_becomes_relative(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(tmp_path)
        )
        uri = f"file://{tmp_path}/episodes/uuid-3/a.mp3"

        assert to_relative_audio_path(uri) == "episodes/uuid-3/a.mp3"

    def test_cwd_relative_path_under_root_becomes_relative(
        self, tmp_path, monkeypatch
    ):
        """podcast-creator receives a CWD-relative output_dir when
        DATA_FOLDER is './data'; the helper must normalize either form."""
        root = tmp_path / "data" / "podcasts"
        root.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", "./data/podcasts"
        )

        rel = to_relative_audio_path("data/podcasts/episodes/uuid-4/a.mp3")

        assert rel == "episodes/uuid-4/a.mp3"

    def test_path_outside_root_raises_value_error(self, tmp_path, monkeypatch):
        root = tmp_path / "podcasts"
        root.mkdir()
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(root)
        )

        with pytest.raises(ValueError, match="outside the podcasts folder"):
            to_relative_audio_path(str(tmp_path / "elsewhere.mp3"))

    def test_traversal_out_of_root_raises_value_error(self, tmp_path, monkeypatch):
        root = tmp_path / "podcasts"
        root.mkdir()
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(root)
        )

        with pytest.raises(ValueError, match="outside the podcasts folder"):
            to_relative_audio_path(str(root / ".." / "escape.mp3"))

    def test_root_itself_raises_value_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(tmp_path)
        )
        with pytest.raises(ValueError, match="outside the podcasts folder"):
            to_relative_audio_path(str(tmp_path))

    def test_roundtrips_with_read_helper(self, tmp_path, monkeypatch):
        from open_notebook.podcasts.audio_paths import resolve_contained_audio_path

        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(tmp_path)
        )
        audio = tmp_path / "episodes" / "uuid-5" / "a.mp3"
        audio.parent.mkdir(parents=True)
        audio.write_bytes(b"audio")

        stored = to_relative_audio_path(str(audio))
        assert resolve_contained_audio_path(stored) == audio.resolve()

    def test_podcasts_root_is_absolute(self):
        assert podcasts_root().is_absolute()


class TestMigration21Registration:
    """Migration files exist and are registered in AsyncMigrationManager
    (migrations are hard-coded, not auto-discovered)."""

    MIGRATIONS_DIR = Path("open_notebook/database/migrations")

    def test_migration_files_exist(self):
        assert (self.MIGRATIONS_DIR / "21.surrealql").is_file()
        assert (self.MIGRATIONS_DIR / "21_down.surrealql").is_file()

    def test_manager_registers_migration_21(self):
        from open_notebook.database.async_migrate import AsyncMigrationManager

        manager = AsyncMigrationManager()
        assert len(manager.up_migrations) >= 21
        assert len(manager.up_migrations) == len(manager.down_migrations)
        assert "podcasts/" in manager.up_migrations[20].sql

    def test_up_migration_strips_known_prefixes_only(self):
        sql = (self.MIGRATIONS_DIR / "21.surrealql").read_text()
        for prefix in (
            "file:///",
            "/app/data/podcasts/",
            "/data/podcasts/",
            "./data/podcasts/",
            "data/podcasts/",
        ):
            assert f'"{prefix}"' in sql, f"expected conversion of prefix {prefix}"
        # Prefix-strip lengths must match the prefixes they guard.
        assert "string::slice(audio_file, 7)" in sql  # len("file://"), keeps "/"
        assert "string::slice(audio_file, 19)" in sql  # len("/app/data/podcasts/")
        assert "string::slice(audio_file, 15)" in sql  # len("/data/podcasts/")
        assert "string::slice(audio_file, 16)" in sql  # len("./data/podcasts/")
        assert "string::slice(audio_file, 14)" in sql  # len("data/podcasts/")
        # Percent-encoded file:// URIs cannot be URL-decoded in SurrealQL and
        # must stay untouched (legacy-invalid).
        assert '!string::contains(audio_file, "%")' in sql
        # Root prefixes are stripped through ONE IF/ELSE chain so a stripped
        # remainder can never be stripped a second time.
        assert sql.count("UPDATE episode") == 2
