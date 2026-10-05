"""Regression tests for #1451: a duplicate profile name must be a 409, not a 500.

`POST /api/episode-profiles` and `POST /api/speaker-profiles` with a name that
already exists were rejected by the unique indexes from migration 7
(`idx_episode_profile_name` / `idx_speaker_profile_name`). Each router's
catch-all `except Exception` arm then answered 500 with a generic
"Failed to create ... profile", so a client could not tell "that name is taken"
from "the server is broken" — and the same happened when an update renamed a
profile onto a name another profile already held.

SurrealDB signals a rejected unique index in the message text rather than
through a typed driver exception, so the fix keys off the same
"already contains" wording the repository layer already uses for bulk inserts
(`open_notebook/database/repository.py`), and raises a typed `ConflictError`
that the global handler in api/main.py maps to 409. The issue asked for a typed
exception over a bare HTTPException, so the routers keep their existing
`except OpenNotebookError: raise` arm and the new translation sits inside the
catch-all, ahead of the 500.

DB access is mocked following the style of tests/test_crud_404.py and
tests/test_recently_viewed_api.py.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.exceptions import ConflictError, as_name_conflict

# The message SurrealDB produces when a unique index rejects the write, taken
# verbatim from the issue's API log.
DUPLICATE_EPISODE = (
    "Database index `idx_episode_profile_name` already contains "
    "'daily_briefing', with record `episode_profile:abc`"
)
DUPLICATE_SPEAKER = (
    "Database index `idx_speaker_profile_name` already contains "
    "'ava', with record `speaker_profile:abc`"
)


@pytest.fixture
def client():
    from api.main import app

    # raise_server_exceptions=False so an exception that escapes the app shows
    # up as a 500 response instead of blowing up the test.
    return TestClient(app, raise_server_exceptions=False)


EPISODE_BODY = {
    "name": "daily_briefing",
    "description": "weekday news",
    "speaker_config": "ava",
    "default_briefing": "Summarise the day.",
    "num_segments": 5,
}
SPEAKER_BODY = {
    "name": "ava",
    "description": "main host",
    "speakers": [
        {
            "name": "Ava",
            "voice_id": "en-US-AvaNeural",
            "backstory": "hosts the show",
            "personality": "brisk",
        }
    ],
}


# --- the translation itself ----------------------------------------------------


def test_as_name_conflict_translates_a_rejected_unique_index():
    conflict = as_name_conflict(
        RuntimeError(DUPLICATE_EPISODE), "episode profile", "daily_briefing"
    )

    assert isinstance(conflict, ConflictError)
    assert "daily_briefing" in str(conflict)
    assert "already exists" in str(conflict)


@pytest.mark.parametrize(
    "exc",
    [
        RuntimeError("connection reset by peer"),
        RuntimeError("Failed to create record"),
        ValueError("something else entirely"),
    ],
)
def test_as_name_conflict_ignores_every_other_failure(exc):
    # Anything not a duplicate-name rejection must keep its old handling, or
    # real server errors would start reporting themselves as conflicts.
    assert as_name_conflict(exc, "episode profile", "daily_briefing") is None


# --- create --------------------------------------------------------------------


@patch("api.routers.episode_profiles._resolve_speaker_config", new_callable=AsyncMock)
@patch("open_notebook.podcasts.models.EpisodeProfile.save", new_callable=AsyncMock)
def test_create_episode_profile_duplicate_name_returns_409(
    mock_save, mock_speaker, client
):
    mock_speaker.return_value = AsyncMock(id="speaker_profile:1", name="ava")
    mock_save.side_effect = RuntimeError(DUPLICATE_EPISODE)

    response = client.post("/api/episode-profiles", json=EPISODE_BODY)

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "daily_briefing" in detail
    assert "already exists" in detail
    # The old 500 answered a generic "Failed to create episode profile" and
    # logged the driver text; neither belongs in a client's 409.
    assert "Failed to create" not in detail
    assert "Database index" not in detail


@patch("open_notebook.podcasts.models.SpeakerProfile.save", new_callable=AsyncMock)
def test_create_speaker_profile_duplicate_name_returns_409(mock_save, client):
    mock_save.side_effect = RuntimeError(DUPLICATE_SPEAKER)

    response = client.post("/api/speaker-profiles", json=SPEAKER_BODY)

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "ava" in detail
    assert "already exists" in detail


# --- update (renaming onto a taken name) ---------------------------------------


@patch("api.routers.episode_profiles._resolve_speaker_config", new_callable=AsyncMock)
@patch("open_notebook.podcasts.models.EpisodeProfile.get", new_callable=AsyncMock)
@patch("open_notebook.podcasts.models.EpisodeProfile.save", new_callable=AsyncMock)
def test_rename_episode_profile_onto_taken_name_returns_409(
    mock_save, mock_get, mock_speaker, client
):
    from open_notebook.podcasts.models import EpisodeProfile

    mock_get.return_value = EpisodeProfile(
        id="episode_profile:1",
        name="old_name",
        default_briefing="Summarise the day.",
    )
    mock_speaker.return_value = AsyncMock(id="speaker_profile:1", name="ava")
    mock_save.side_effect = RuntimeError(DUPLICATE_EPISODE)

    response = client.put("/api/episode-profiles/episode_profile:1", json=EPISODE_BODY)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@patch("open_notebook.podcasts.models.SpeakerProfile.get", new_callable=AsyncMock)
@patch("open_notebook.podcasts.models.SpeakerProfile.save", new_callable=AsyncMock)
def test_rename_speaker_profile_onto_taken_name_returns_409(
    mock_save, mock_get, client
):
    from open_notebook.podcasts.models import SpeakerProfile

    mock_get.return_value = SpeakerProfile(
        id="speaker_profile:1",
        name="old_name",
        speakers=SPEAKER_BODY["speakers"],
    )
    mock_save.side_effect = RuntimeError(DUPLICATE_SPEAKER)

    response = client.put("/api/speaker-profiles/speaker_profile:1", json=SPEAKER_BODY)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


# --- the 500 must survive for every other failure -----------------------------


@patch("api.routers.episode_profiles._resolve_speaker_config", new_callable=AsyncMock)
@patch("open_notebook.podcasts.models.EpisodeProfile.save", new_callable=AsyncMock)
def test_create_episode_profile_other_failure_still_returns_500(
    mock_save, mock_speaker, client
):
    mock_speaker.return_value = AsyncMock(id="speaker_profile:1", name="ava")
    mock_save.side_effect = RuntimeError("connection reset by peer")

    response = client.post("/api/episode-profiles", json=EPISODE_BODY)

    assert response.status_code == 500


@patch("open_notebook.podcasts.models.SpeakerProfile.save", new_callable=AsyncMock)
def test_create_speaker_profile_other_failure_still_returns_500(mock_save, client):
    mock_save.side_effect = RuntimeError("connection reset by peer")

    response = client.post("/api/speaker-profiles", json=SPEAKER_BODY)

    assert response.status_code == 500
