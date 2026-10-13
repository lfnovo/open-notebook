"""Regression tests for #1488: a speaker profile must only accept a
text-to-speech model as its voice_model (create, update and duplicate)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.ai.models import Model
from open_notebook.podcasts.models import SpeakerProfile

SPEAKERS = [{"name": "Host", "voice_id": "v1", "backstory": "b", "personality": "p"}]
BODY = {"name": "p", "speakers": SPEAKERS, "voice_model": "model:m1"}


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def _model(model_type):
    return Model(name="m", provider="openai", type=model_type)


def _profile():
    return SpeakerProfile(name="p", speakers=SPEAKERS, voice_model="model:m1")


@pytest.fixture
def mocks():
    with (
        patch("open_notebook.ai.models.Model.get", new_callable=AsyncMock) as get,
        patch(
            "api.routers.speaker_profiles.SpeakerProfile.get", new_callable=AsyncMock
        ) as pget,
        patch(
            "api.routers.speaker_profiles.SpeakerProfile.save", new_callable=AsyncMock
        ) as save,
    ):
        pget.return_value = _profile()
        yield get, save


def test_create_rejects_non_tts_voice_model(client, mocks):
    get, save = mocks
    get.return_value = _model("language")
    assert client.post("/api/speaker-profiles", json=BODY).status_code == 422
    save.assert_not_called()


def test_create_accepts_tts_voice_model(client, mocks):
    get, save = mocks
    get.return_value = _model("text_to_speech")
    assert client.post("/api/speaker-profiles", json=BODY).status_code == 200
    save.assert_called_once()


def test_create_without_voice_model_skips_lookup(client, mocks):
    get, save = mocks
    body = {"name": "p", "speakers": SPEAKERS}
    assert client.post("/api/speaker-profiles", json=body).status_code == 200
    get.assert_not_called()
    save.assert_called_once()


def test_update_rejects_non_tts_voice_model(client, mocks):
    get, save = mocks
    get.return_value = _model("language")
    assert client.put("/api/speaker-profiles/sp:1", json=BODY).status_code == 422
    save.assert_not_called()


def test_duplicate_rejects_non_tts_voice_model(client, mocks):
    get, save = mocks
    get.return_value = _model("language")
    assert client.post("/api/speaker-profiles/sp:1/duplicate").status_code == 422
    save.assert_not_called()
