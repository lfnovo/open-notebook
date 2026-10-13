"""Regression tests for #1488: a speaker profile's voice_model, and every
per-speaker voice_model override, must be a text-to-speech model (create,
update and duplicate)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.ai.models import Model
from open_notebook.podcasts.models import SpeakerProfile

MODELS = {
    "model:tts": Model(name="t", provider="openai", type="text_to_speech"),
    "model:llm": Model(name="l", provider="openai", type="language"),
}
ENDPOINTS = [
    ("post", "/api/speaker-profiles"),
    ("put", "/api/speaker-profiles/sp:1"),
    ("post", "/api/speaker-profiles/sp:1/duplicate"),
]


def _speakers(override=None):
    speaker = {"name": "Host", "voice_id": "v", "backstory": "b", "personality": "p"}
    return [{**speaker, "voice_model": override} if override else speaker]


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


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
        get.side_effect = MODELS.__getitem__
        yield get, pget, save


def _call(client, pget, method, url, voice_model, override=None, stored=None):
    """Send the request; `stored` is the profile that update/duplicate load."""
    pget.return_value = SpeakerProfile(
        name="p", voice_model=stored or voice_model, speakers=_speakers(override)
    )
    body = {"name": "p", "voice_model": voice_model, "speakers": _speakers(override)}
    return client.request(method, url, json=body)


@pytest.mark.parametrize("method,url", ENDPOINTS)
@pytest.mark.parametrize(
    "voice_model,override",
    [("model:llm", None), ("model:tts", "model:llm")],
    ids=["top-level", "per-speaker"],
)
def test_rejects_non_tts_voice_model(client, mocks, method, url, voice_model, override):
    _, pget, save = mocks
    resp = _call(client, pget, method, url, voice_model, override)
    assert resp.status_code == 422
    save.assert_not_called()


@pytest.mark.parametrize("method,url", ENDPOINTS)
def test_accepts_tts_voice_models(client, mocks, method, url):
    _, pget, save = mocks
    resp = _call(client, pget, method, url, "model:tts", "model:tts")
    assert resp.status_code == 200
    save.assert_called_once()


def test_create_without_voice_model_skips_lookup(client, mocks):
    get, _, save = mocks
    body = {"name": "p", "speakers": _speakers()}
    assert client.post("/api/speaker-profiles", json=body).status_code == 200
    get.assert_not_called()
    save.assert_called_once()


def test_update_checks_the_incoming_voice_model(client, mocks):
    get, pget, save = mocks
    url = "/api/speaker-profiles/sp:1"
    resp = _call(client, pget, "put", url, "model:tts", stored="model:llm")
    assert resp.status_code == 200
    save.assert_called_once()
    assert [c.args for c in get.await_args_list] == [("model:tts",)]
