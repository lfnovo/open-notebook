"""Episode profiles expose podcast-creator's pause between dialogue turns
(audio_gap_ms, #1436): None uses the 400 ms default, 0 means back-to-back
audio, and a negative value is rejected."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from open_notebook.podcasts.models import EpisodeProfile

MIGRATIONS_DIR = Path("open_notebook/database/migrations")


def _profile(**kwargs) -> EpisodeProfile:
    return EpisodeProfile(
        name="Test", speaker_config="speaker_profile:1", default_briefing="b", **kwargs
    )


class TestModel:
    def test_defaults_to_none(self):
        assert _profile().audio_gap_ms is None

    def test_accepts_zero(self):
        assert _profile(audio_gap_ms=0).audio_gap_ms == 0

    def test_rejects_negative(self):
        with pytest.raises(ValidationError):
            _profile(audio_gap_ms=-1)

    def test_none_is_saved_so_clearing_works(self):
        data = _profile(audio_gap_ms=None)._prepare_save_data()
        assert "audio_gap_ms" in data and data["audio_gap_ms"] is None


class TestMigration:
    def test_up_and_down(self):
        up = (MIGRATIONS_DIR / "27.surrealql").read_text()
        down = (MIGRATIONS_DIR / "27_down.surrealql").read_text()
        assert (
            "DEFINE FIELD IF NOT EXISTS audio_gap_ms ON TABLE episode_profile "
            "TYPE option<int>" in up
        )
        assert "REMOVE FIELD IF EXISTS audio_gap_ms ON TABLE episode_profile" in down

    def test_registered(self):
        from open_notebook.database.async_migrate import AsyncMigrationManager

        manager = AsyncMigrationManager()
        assert len(manager.up_migrations) == len(manager.down_migrations)
        assert "audio_gap_ms" in manager.up_migrations[26].sql
        assert "audio_gap_ms" in manager.down_migrations[26].sql


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app, raise_server_exceptions=False)


BODY = {"name": "Gap", "speaker_config": "speaker_profile:1", "default_briefing": "b"}


class TestApi:
    def _post(self, client, **extra):
        speaker = SimpleNamespace(id="speaker_profile:1", name="Hosts")
        with (
            patch(
                "api.routers.episode_profiles.SpeakerProfile.resolve",
                AsyncMock(return_value=speaker),
            ),
            patch(
                "api.routers.episode_profiles.EpisodeProfile.save", AsyncMock()
            ) as save,
        ):
            return client.post("/api/episode-profiles", json={**BODY, **extra}), save

    def test_create_round_trip(self, client):
        response, _ = self._post(client, audio_gap_ms=0)
        assert response.status_code == 200
        assert response.json()["audio_gap_ms"] == 0

    def test_create_without_value_returns_null(self, client):
        response, _ = self._post(client)
        assert response.status_code == 200
        assert response.json()["audio_gap_ms"] is None

    def test_create_negative_is_400(self, client):
        response, save = self._post(client, audio_gap_ms=-5)
        assert response.status_code == 400
        save.assert_not_awaited()

    def test_update_negative_is_400(self, client):
        with (
            patch(
                "api.routers.episode_profiles.EpisodeProfile.get",
                AsyncMock(return_value=_profile()),
            ),
            patch(
                "api.routers.episode_profiles.EpisodeProfile.save", AsyncMock()
            ) as save,
        ):
            response = client.put(
                "/api/episode-profiles/episode_profile:1",
                json={**BODY, "audio_gap_ms": -1},
            )
        assert response.status_code == 400
        save.assert_not_awaited()
