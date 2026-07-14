"""
Tests for the podcast audio path choke point (#1030).

`PodcastEpisode.audio_file` stores a path relative to PODCASTS_FOLDER;
`resolve_contained_audio_path()` (open_notebook/podcasts/audio_paths.py) is
the single helper every consumption point (stream, list, get, delete, retry)
uses to join + resolve + contain it. Absolute paths and `file://` URIs are
legacy rows migration 21 could not convert - they are treated as invalid,
preserving the 403/404 behavior #1018's guards gave them.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.config import PODCASTS_FOLDER
from open_notebook.podcasts.audio_paths import resolve_contained_audio_path
from open_notebook.podcasts.models import PodcastEpisode


def make_episode(audio_file=None, **overrides):
    defaults = dict(
        id="episode:test123",
        name="Test Episode",
        episode_profile={"name": "default"},
        speaker_profile={"name": "default"},
        briefing="test briefing",
        content="test content",
        audio_file=audio_file,
        command=None,
    )
    defaults.update(overrides)
    return PodcastEpisode(**defaults)


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestResolveContainedAudioPath:
    def test_relative_path_inside_root_resolves(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(tmp_path)
        )
        episode_dir = tmp_path / "episodes" / "some-uuid"
        episode_dir.mkdir(parents=True)
        (episode_dir / "final.mp3").write_bytes(b"fake audio")

        resolved = resolve_contained_audio_path("episodes/some-uuid/final.mp3")

        assert resolved == (episode_dir / "final.mp3").resolve()

    def test_dotdot_escape_is_rejected(self, tmp_path, monkeypatch):
        root = tmp_path / "podcasts"
        root.mkdir()
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(root)
        )
        outside = tmp_path / "outside.mp3"
        outside.write_bytes(b"etc passwd style file")

        assert resolve_contained_audio_path("../outside.mp3") is None
        assert resolve_contained_audio_path("episodes/../../outside.mp3") is None

    def test_absolute_path_is_rejected_even_when_inside_root(
        self, tmp_path, monkeypatch
    ):
        """Legacy rows the migration could not convert stay invalid - the DB
        contract after #1030 is relative-only."""
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(tmp_path)
        )
        inside = tmp_path / "episodes" / "u" / "a.mp3"
        inside.parent.mkdir(parents=True)
        inside.write_bytes(b"audio")

        assert resolve_contained_audio_path(str(inside)) is None
        assert resolve_contained_audio_path("/etc/passwd") is None

    def test_file_uri_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(tmp_path)
        )
        assert (
            resolve_contained_audio_path("file:///data/podcasts/episodes/x/a.mp3")
            is None
        )

    def test_sibling_directory_with_matching_prefix_is_rejected(
        self, tmp_path, monkeypatch
    ):
        """Regression guard for the startswith-without-separator bug: a
        sibling dir that merely *starts with* the root's name must not be
        reachable."""
        real_root = tmp_path / "podcasts"
        real_root.mkdir()
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(real_root)
        )
        sibling = tmp_path / "podcasts_evil"
        sibling.mkdir()
        (sibling / "secret.mp3").write_bytes(b"not yours")

        assert resolve_contained_audio_path("../podcasts_evil/secret.mp3") is None

    def test_symlink_escape_is_rejected(self, tmp_path, monkeypatch):
        root = tmp_path / "podcasts"
        root.mkdir()
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(root)
        )
        outside = tmp_path / "outside.mp3"
        outside.write_bytes(b"secret")
        (root / "link.mp3").symlink_to(outside)

        assert resolve_contained_audio_path("link.mp3") is None

    def test_empty_and_none_are_rejected(self):
        assert resolve_contained_audio_path(None) is None
        assert resolve_contained_audio_path("") is None

    def test_root_itself_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "open_notebook.podcasts.audio_paths.PODCASTS_FOLDER", str(tmp_path)
        )
        assert resolve_contained_audio_path(".") is None

    def test_real_podcasts_folder_resolves(self):
        """Sanity check against the real (non-monkeypatched) config constant."""
        assert (
            resolve_contained_audio_path("episodes/abc/out.mp3") is not None
        )
        assert resolve_contained_audio_path("../elsewhere.mp3") is None


class TestStreamEndpointRejectsInvalidAudio:
    def test_returns_403_for_legacy_absolute_audio_file(self, client, tmp_path):
        evil_file = tmp_path / "secret.mp3"
        evil_file.write_bytes(b"not a podcast")
        episode = make_episode(audio_file=str(evil_file))

        with patch(
            "api.routers.podcasts.PodcastService.get_episode",
            new=AsyncMock(return_value=episode),
        ):
            response = client.get("/api/podcasts/episodes/episode:test123/audio")

        assert response.status_code == 403

    def test_returns_403_for_relative_traversal(self, client):
        episode = make_episode(audio_file="../../etc/passwd")

        with patch(
            "api.routers.podcasts.PodcastService.get_episode",
            new=AsyncMock(return_value=episode),
        ):
            response = client.get("/api/podcasts/episodes/episode:test123/audio")

        assert response.status_code == 403

    def test_returns_404_for_missing_audio_inside_root(self, client):
        # Valid relative form (passes containment) but the file doesn't exist.
        episode = make_episode(audio_file="episodes/does-not-exist/out.mp3")

        with patch(
            "api.routers.podcasts.PodcastService.get_episode",
            new=AsyncMock(return_value=episode),
        ):
            response = client.get("/api/podcasts/episodes/episode:test123/audio")

        assert response.status_code == 404
        assert "not found on disk" in response.json()["detail"]

    def test_serves_audio_file_from_relative_path(self, client):
        episode_dir = Path(PODCASTS_FOLDER) / "episodes" / "test-serve-uuid"
        episode_dir.mkdir(parents=True, exist_ok=True)
        audio_path = episode_dir / "out.mp3"
        audio_path.write_bytes(b"fake mp3 bytes")
        try:
            episode = make_episode(audio_file="episodes/test-serve-uuid/out.mp3")
            with patch(
                "api.routers.podcasts.PodcastService.get_episode",
                new=AsyncMock(return_value=episode),
            ):
                response = client.get("/api/podcasts/episodes/episode:test123/audio")

            assert response.status_code == 200
            assert response.content == b"fake mp3 bytes"
        finally:
            audio_path.unlink(missing_ok=True)
            episode_dir.rmdir()


class TestListAndGetOmitAudioUrlWhenInvalid:
    def test_list_episodes_omits_audio_url_for_legacy_absolute_file(
        self, client, tmp_path
    ):
        evil_file = tmp_path / "secret.mp3"
        evil_file.write_bytes(b"not yours")
        episode = make_episode(audio_file=str(evil_file))

        with (
            patch(
                "api.routers.podcasts.PodcastService.list_episodes",
                new=AsyncMock(return_value=[episode]),
            ),
        ):
            response = client.get("/api/podcasts/episodes")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["audio_url"] is None

    def test_list_episodes_sets_audio_url_for_valid_relative_file(self, client):
        episode_dir = Path(PODCASTS_FOLDER) / "episodes" / "test-list-uuid"
        episode_dir.mkdir(parents=True, exist_ok=True)
        audio_path = episode_dir / "out.mp3"
        audio_path.write_bytes(b"fake mp3 bytes")
        try:
            episode = make_episode(audio_file="episodes/test-list-uuid/out.mp3")
            with patch(
                "api.routers.podcasts.PodcastService.list_episodes",
                new=AsyncMock(return_value=[episode]),
            ):
                response = client.get("/api/podcasts/episodes")

            assert response.status_code == 200
            body = response.json()
            assert body[0]["audio_url"] == (
                "/api/podcasts/episodes/episode:test123/audio"
            )
        finally:
            audio_path.unlink(missing_ok=True)
            episode_dir.rmdir()

    def test_get_episode_omits_audio_url_for_legacy_absolute_file(
        self, client, tmp_path
    ):
        evil_file = tmp_path / "secret.mp3"
        evil_file.write_bytes(b"not yours")
        episode = make_episode(audio_file=str(evil_file))

        with patch(
            "api.routers.podcasts.PodcastService.get_episode",
            new=AsyncMock(return_value=episode),
        ):
            response = client.get("/api/podcasts/episodes/episode:test123")

        assert response.status_code == 200
        assert response.json()["audio_url"] is None


class TestDeleteAndRetryRefuseInvalidUnlink:
    def test_delete_episode_does_not_unlink_legacy_absolute_file(
        self, client, tmp_path
    ):
        evil_file = tmp_path / "secret.mp3"
        evil_file.write_bytes(b"not yours")
        episode = make_episode(audio_file=str(evil_file))

        with (
            patch(
                "api.routers.podcasts.PodcastService.get_episode",
                new=AsyncMock(return_value=episode),
            ),
            patch.object(PodcastEpisode, "delete", new=AsyncMock(return_value=True)),
        ):
            response = client.delete("/api/podcasts/episodes/episode:test123")

        assert response.status_code == 200
        assert evil_file.exists(), "out-of-root file must not be deleted"

    def test_delete_episode_unlinks_relative_in_root_file(self, client):
        episode_dir = Path(PODCASTS_FOLDER) / "episodes" / "test-delete-uuid"
        episode_dir.mkdir(parents=True, exist_ok=True)
        audio_path = episode_dir / "out.mp3"
        audio_path.write_bytes(b"fake mp3 bytes")
        episode = make_episode(audio_file="episodes/test-delete-uuid/out.mp3")

        try:
            with (
                patch(
                    "api.routers.podcasts.PodcastService.get_episode",
                    new=AsyncMock(return_value=episode),
                ),
                patch.object(
                    PodcastEpisode, "delete", new=AsyncMock(return_value=True)
                ),
            ):
                response = client.delete("/api/podcasts/episodes/episode:test123")

            assert response.status_code == 200
            assert not audio_path.exists(), "in-root file should be deleted"
        finally:
            if episode_dir.exists():
                for f in episode_dir.iterdir():
                    f.unlink()
                episode_dir.rmdir()
