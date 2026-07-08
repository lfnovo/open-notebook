"""
Tests for the podcast audio path containment check (api/routers/podcasts.py).

`_resolve_audio_path()` turns `episode.audio_file` into a filesystem Path;
`_is_audio_path_contained()` verifies that path stays under PODCASTS_FOLDER
before any endpoint streams or deletes it. audio_file is only ever set
server-side today (from a UUID-named directory under PODCASTS_FOLDER), so
these are defense-in-depth checks for a currently-unreachable path - these
tests construct an out-of-root audio_file directly to exercise that defense.
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.routers.podcasts import _is_audio_path_contained, _resolve_audio_path
from open_notebook.config import PODCASTS_FOLDER
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


class TestIsAudioPathContained:
    def test_path_inside_podcasts_folder_is_contained(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "api.routers.podcasts.PODCASTS_FOLDER", str(tmp_path)
        )
        episode_dir = tmp_path / "episodes" / "some-uuid"
        episode_dir.mkdir(parents=True)
        audio_path = episode_dir / "final.mp3"
        audio_path.write_bytes(b"fake audio")

        assert _is_audio_path_contained(audio_path) is True

    def test_sibling_directory_with_matching_prefix_is_not_contained(
        self, tmp_path, monkeypatch
    ):
        """Regression guard for the startswith-without-separator bug (finding
        L14): a sibling dir that merely *starts with* the same prefix string
        must NOT be treated as contained."""
        real_root = tmp_path / "podcasts"
        real_root.mkdir()
        monkeypatch.setattr("api.routers.podcasts.PODCASTS_FOLDER", str(real_root))

        sibling = tmp_path / "podcasts_evil"
        sibling.mkdir()
        evil_file = sibling / "secret.mp3"
        evil_file.write_bytes(b"not yours")

        assert _is_audio_path_contained(evil_file) is False

    def test_path_traversal_outside_root_is_not_contained(self, tmp_path, monkeypatch):
        root = tmp_path / "podcasts"
        root.mkdir()
        monkeypatch.setattr("api.routers.podcasts.PODCASTS_FOLDER", str(root))

        outside = tmp_path / "outside.mp3"
        outside.write_bytes(b"etc passwd style file")
        traversal_path = Path(str(root)) / ".." / "outside.mp3"

        assert _is_audio_path_contained(traversal_path) is False

    def test_root_itself_is_contained(self, tmp_path, monkeypatch):
        monkeypatch.setattr("api.routers.podcasts.PODCASTS_FOLDER", str(tmp_path))
        assert _is_audio_path_contained(tmp_path) is True

    def test_real_podcasts_folder_resolves(self):
        """Sanity check against the real (non-monkeypatched) config constant."""
        inside = Path(PODCASTS_FOLDER) / "episodes" / "abc" / "out.mp3"
        assert _is_audio_path_contained(inside) is True
        outside = Path(os.path.realpath(PODCASTS_FOLDER)).parent / "elsewhere.mp3"
        assert _is_audio_path_contained(outside) is False


class TestResolveAudioPathHandlesFileUri:
    def test_plain_path(self):
        assert _resolve_audio_path("/data/podcasts/episodes/x/out.mp3") == Path(
            "/data/podcasts/episodes/x/out.mp3"
        )

    def test_file_uri(self):
        assert _resolve_audio_path("file:///data/podcasts/episodes/x/out.mp3") == Path(
            "/data/podcasts/episodes/x/out.mp3"
        )


class TestStreamEndpointRejectsOutOfRootAudio:
    def test_returns_403_for_audio_file_outside_podcasts_root(self, client, tmp_path):
        evil_file = tmp_path / "secret.mp3"
        evil_file.write_bytes(b"not a podcast")
        episode = make_episode(audio_file=str(evil_file))

        with patch(
            "api.routers.podcasts.PodcastService.get_episode",
            new=AsyncMock(return_value=episode),
        ):
            response = client.get("/api/podcasts/episodes/episode:test123/audio")

        assert response.status_code == 403

    def test_returns_404_for_missing_audio_inside_root(self, client):
        # Inside PODCASTS_FOLDER (passes containment) but the file doesn't exist.
        missing = Path(PODCASTS_FOLDER) / "episodes" / "does-not-exist" / "out.mp3"
        episode = make_episode(audio_file=str(missing))

        with patch(
            "api.routers.podcasts.PodcastService.get_episode",
            new=AsyncMock(return_value=episode),
        ):
            response = client.get("/api/podcasts/episodes/episode:test123/audio")

        assert response.status_code == 404
        assert "not found on disk" in response.json()["detail"]

    def test_serves_audio_file_inside_root(self, client):
        episode_dir = Path(PODCASTS_FOLDER) / "episodes" / "test-serve-uuid"
        episode_dir.mkdir(parents=True, exist_ok=True)
        audio_path = episode_dir / "out.mp3"
        audio_path.write_bytes(b"fake mp3 bytes")
        try:
            episode = make_episode(audio_file=str(audio_path))
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


class TestListAndGetOmitAudioUrlWhenOutOfRoot:
    def test_list_episodes_omits_audio_url_for_out_of_root_file(self, client, tmp_path):
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

    def test_get_episode_omits_audio_url_for_out_of_root_file(self, client, tmp_path):
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


class TestDeleteAndRetryRefuseOutOfRootUnlink:
    def test_delete_episode_does_not_unlink_out_of_root_file(self, client, tmp_path):
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

    def test_delete_episode_still_unlinks_in_root_file(self, client):
        episode_dir = Path(PODCASTS_FOLDER) / "episodes" / "test-delete-uuid"
        episode_dir.mkdir(parents=True, exist_ok=True)
        audio_path = episode_dir / "out.mp3"
        audio_path.write_bytes(b"fake mp3 bytes")
        episode = make_episode(audio_file=str(audio_path))

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
