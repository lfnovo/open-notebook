"""Regression tests for #1488: a speaker profile's voice_model, and every
per-speaker voice_model override, must be a text-to-speech model (create,
update and duplicate)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.routers.speaker_profiles import _validate_voice_models
from open_notebook.ai.models import Model
from open_notebook.exceptions import ConfigurationError
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


def _speakers(overrides=(None,)):
    speaker = {"name": "Host", "voice_id": "v", "backstory": "b", "personality": "p"}
    return [{**speaker, "voice_model": o} if o else dict(speaker) for o in overrides]


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


def _call(client, pget, method, url, voice_model, overrides=(None,), stored=None):
    """Send the request; `stored` = (voice_model, overrides) update/duplicate load."""
    stored_model, stored_overrides = stored or (voice_model, overrides)
    pget.return_value = SpeakerProfile(
        name="p", voice_model=stored_model, speakers=_speakers(stored_overrides)
    )
    body = {"name": "p", "voice_model": voice_model, "speakers": _speakers(overrides)}
    return client.request(method, url, json=body)


@pytest.mark.parametrize("method,url", ENDPOINTS)
@pytest.mark.parametrize(
    "voice_model,overrides",
    [
        ("model:llm", (None,)),
        ("model:tts", ("model:llm",)),
        ("model:tts", ("model:tts", "model:llm")),
        (None, ("model:llm",)),
    ],
    ids=["top-level", "per-speaker", "second-speaker", "override-only"],
)
def test_rejects_non_tts_voice_model(
    client, mocks, method, url, voice_model, overrides
):
    _, pget, save = mocks
    resp = _call(client, pget, method, url, voice_model, overrides)
    assert resp.status_code == 422
    save.assert_not_called()


@pytest.mark.parametrize("method,url", ENDPOINTS)
def test_accepts_tts_voice_models(client, mocks, method, url):
    _, pget, save = mocks
    resp = _call(client, pget, method, url, "model:tts", ("model:tts",))
    assert resp.status_code == 200
    save.assert_called_once()


def test_create_without_voice_model_skips_lookup(client, mocks):
    get, _, save = mocks
    body = {"name": "p", "speakers": _speakers()}
    assert client.post("/api/speaker-profiles", json=body).status_code == 200
    get.assert_not_called()
    save.assert_called_once()


def test_update_checks_the_incoming_voice_models(client, mocks):
    get, pget, save = mocks
    stored = ("model:llm", ("model:llm",))
    url = "/api/speaker-profiles/sp:1"
    resp = _call(client, pget, "put", url, "model:tts", ("model:tts",), stored)
    assert resp.status_code == 200
    save.assert_called_once()
    assert [c.args for c in get.await_args_list] == [("model:tts",), ("model:tts",)]


@pytest.mark.parametrize("method,url", ENDPOINTS)
@pytest.mark.parametrize("bad_id", ["model:", "model:a:b", "notebook:abc"])
def test_rejects_malformed_voice_model_id(client, mocks, method, url, bad_id):
    get, pget, save = mocks
    assert _call(client, pget, method, url, bad_id).status_code == 400
    get.assert_not_awaited()
    save.assert_not_called()


@pytest.mark.asyncio
async def test_non_tts_voice_model_raises_a_typed_error(mocks):
    with pytest.raises(ConfigurationError):
        await _validate_voice_models("model:llm", [])
