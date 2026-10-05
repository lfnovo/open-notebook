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
    assert str(conflict).startswith(("Episode profile", "Speaker profile"))


@pytest.mark.parametrize(
    "exc",
    [
        # The two RuntimeErrors repository.py can raise on a create, neither of
        # which is a rejected index, plus a different exception type to show the
        # check is on the text and not on the class.
        RuntimeError("Failed to create record"),
        RuntimeError("Failed to load default models configuration"),
        ValueError("Invalid GitHub repository URL"),
    ],
)
def test_as_name_conflict_ignores_every_other_failure(exc):
    # Anything not a duplicate-name rejection must keep its old handling, or
    # real server errors would start reporting themselves as conflicts.
    assert as_name_conflict(exc, "episode profile", "daily_briefing") is None


# --- create and rename both answer 409 on a rejected unique index ---------------


@pytest.mark.parametrize(
    "profile,body,driver_error,expected,url",
    [
        (
            "EpisodeProfile",
            EPISODE_BODY,
            DUPLICATE_EPISODE,
            "Episode profile",
            "/api/episode-profiles",
        ),
        (
            "SpeakerProfile",
            SPEAKER_BODY,
            DUPLICATE_SPEAKER,
            "Speaker profile",
            "/api/speaker-profiles",
        ),
    ],
)
def test_create_duplicate_name_returns_409(
    client, profile, body, driver_error, expected, url
):
    """The pre-check says the name is free, so the write is attempted and the
    unique index is what rejects it -- the concurrent-create case."""

    router = "episode_profiles" if profile == "EpisodeProfile" else "speaker_profiles"
    precheck = "episode" if profile == "EpisodeProfile" else "speaker"

    with (
        patch(
            f"api.routers.{router}._{precheck}_profile_named", new_callable=AsyncMock
        ) as taken,
        patch(
            f"open_notebook.podcasts.models.{profile}.save", new_callable=AsyncMock
        ) as save,
    ):
        taken.return_value = False
        save.side_effect = RuntimeError(driver_error)
        if profile == "EpisodeProfile":
            with patch(
                "api.routers.episode_profiles._resolve_speaker_config",
                new_callable=AsyncMock,
            ) as speaker:
                speaker.return_value = AsyncMock(id="speaker_profile:1", name="ava")
                response = client.post(url, json=body)
        else:
            response = client.post(url, json=body)

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert expected in detail
    assert "already exists" in detail
    assert body["name"] in detail
    # The old 500 answered a generic "Failed to create episode profile" and
    # logged the driver text; neither belongs in a client's 409.
    assert "Failed to create" not in detail
    assert "Database index" not in detail


@pytest.mark.parametrize(
    "profile,body,driver_error,record_id,url",
    [
        (
            "EpisodeProfile",
            EPISODE_BODY,
            DUPLICATE_EPISODE,
            "episode_profile:1",
            "/api/episode-profiles/episode_profile:1",
        ),
        (
            "SpeakerProfile",
            SPEAKER_BODY,
            DUPLICATE_SPEAKER,
            "speaker_profile:1",
            "/api/speaker-profiles/speaker_profile:1",
        ),
    ],
)
def test_rename_onto_taken_name_returns_409(
    client, profile, body, driver_error, record_id, url
):
    """Renaming onto a name another profile holds must be a 409, not a 500."""
    from open_notebook.podcasts.models import EpisodeProfile, SpeakerProfile

    model = EpisodeProfile if profile == "EpisodeProfile" else SpeakerProfile
    router = "episode_profiles" if profile == "EpisodeProfile" else "speaker_profiles"
    precheck = "episode" if profile == "EpisodeProfile" else "speaker"
    existing = model(
        id=record_id,
        name="old_name",
        **(
            {"default_briefing": "Summarise the day."}
            if profile == "EpisodeProfile"
            else {"speakers": SPEAKER_BODY["speakers"]}
        ),
    )

    with (
        patch(
            f"api.routers.{router}._{precheck}_profile_named", new_callable=AsyncMock
        ) as taken,
        patch(
            f"open_notebook.podcasts.models.{profile}.get",
            new_callable=AsyncMock,
            return_value=existing,
        ),
        patch(
            f"open_notebook.podcasts.models.{profile}.save", new_callable=AsyncMock
        ) as save,
    ):
        taken.return_value = False
        save.side_effect = RuntimeError(driver_error)
        if profile == "EpisodeProfile":
            with patch(
                "api.routers.episode_profiles._resolve_speaker_config",
                new_callable=AsyncMock,
            ) as speaker:
                speaker.return_value = AsyncMock(id="speaker_profile:1", name="ava")
                response = client.put(url, json=body)
        else:
            response = client.put(url, json=body)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


# --- the pre-check, which does not rely on the driver at all -----------------


@pytest.mark.parametrize(
    "endpoint,payload,entity,patch_target",
    [
        (
            "/api/episode-profiles",
            EPISODE_BODY,
            "episode profile",
            "api.routers.episode_profiles._episode_profile_named",
        ),
        (
            "/api/speaker-profiles",
            SPEAKER_BODY,
            "speaker profile",
            "api.routers.speaker_profiles._speaker_profile_named",
        ),
    ],
)
def test_create_conflict_is_detected_before_touching_the_database(
    client, endpoint, payload, entity, patch_target
):
    """A pre-check answers 409 even if the driver swallows the message.

    The pre-check does not depend on the driver's wording, so the 409 survives
    either exception shape.

    Both save methods are patched and both are asserted. Asserting only
    `SpeakerProfile.save` left the episode case vacuous: that router persists
    through `EpisodeProfile.save`, so `SpeakerProfile.save.call_count` was 0
    whether or not an insert was attempted. The assertion now fails if
    *either* endpoint reaches its write.
    """
    with (
        patch(
            "open_notebook.podcasts.models.SpeakerProfile.save",
            new_callable=AsyncMock,
        ) as speaker_save,
        patch(
            "open_notebook.podcasts.models.EpisodeProfile.save",
            new_callable=AsyncMock,
        ) as episode_save,
        patch(patch_target, new_callable=AsyncMock) as taken,
    ):
        taken.return_value = True
        if "episode" in endpoint:
            with patch(
                "api.routers.episode_profiles._resolve_speaker_config",
                new_callable=AsyncMock,
            ) as speaker:
                speaker.return_value = AsyncMock(id="speaker_profile:1", name="ava")
                response = client.post(endpoint, json=payload)
        else:
            response = client.post(endpoint, json=payload)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    # The insert must never be attempted once the name is known to be taken.
    assert speaker_save.call_count == 0
    assert episode_save.call_count == 0


# --- the 500 must survive for every other failure -----------------------------


@pytest.mark.parametrize(
    "method,endpoint,profile,error",
    [
        ("post", "/api/episode-profiles", "EpisodeProfile", None),
        ("post", "/api/speaker-profiles", "SpeakerProfile", None),
        (
            "put",
            "/api/episode-profiles/episode_profile:1",
            "EpisodeProfile",
            "episode_profile:1",
        ),
        (
            "put",
            "/api/speaker-profiles/speaker_profile:1",
            "SpeakerProfile",
            "speaker_profile:1",
        ),
    ],
)
def test_other_failure_still_returns_500(client, method, endpoint, profile, error):
    """A failure that is not a rejected unique index must still answer 500.

    Each router's catch-all has its own translation branch, so all four
    method/entity combinations are covered.
    """
    from open_notebook.podcasts.models import EpisodeProfile, SpeakerProfile

    body = EPISODE_BODY if profile == "EpisodeProfile" else SPEAKER_BODY
    model = EpisodeProfile if profile == "EpisodeProfile" else SpeakerProfile
    router = "episode_profiles" if profile == "EpisodeProfile" else "speaker_profiles"
    existing = model(
        id=error,
        name="old_name",
        **(
            {"default_briefing": "Summarise the day."}
            if profile == "EpisodeProfile"
            else {"speakers": SPEAKER_BODY["speakers"]}
        ),
    )

    with (
        patch(
            f"api.routers.{router}._"
            + ("episode" if profile == "EpisodeProfile" else "speaker")
            + "_profile_named",
            new_callable=AsyncMock,
        ) as taken,
        patch(
            f"open_notebook.podcasts.models.{profile}.save", new_callable=AsyncMock
        ) as save,
        patch.object(model, "get", new_callable=AsyncMock, return_value=existing)
        if error
        else _null(),
    ):
        taken.return_value = False
        # What save() really raises when the write fails for a reason other
        # than a rejected index: repo_create replaces any non-RuntimeError
        # from the driver with exactly this.
        save.side_effect = RuntimeError("Failed to create record")
        if profile == "EpisodeProfile":
            with patch(
                "api.routers.episode_profiles._resolve_speaker_config",
                new_callable=AsyncMock,
            ) as speaker:
                speaker.return_value = AsyncMock(id="speaker_profile:1", name="ava")
                response = getattr(client, method)(endpoint, json=body)
        else:
            response = getattr(client, method)(endpoint, json=body)

    assert response.status_code == 500


class _null:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


# --- the repository boundary ----------------------------------------------------


@pytest.mark.asyncio
async def test_repo_create_preserves_the_unique_index_message():
    """The 409 depends on repo_create re-raising the driver's own wording.

    SurrealDB does not raise on a rejected unique index -- `connection.insert`
    hands the error back as a string, `parse_record_ids` passes it through, and
    repo_create turns it into a RuntimeError itself. That lands on its
    `except RuntimeError` arm, so the "already contains" text that
    `as_name_conflict` keys off survives. The other arm would replace it with
    "Failed to create record" and put every duplicate create back at 500.

    Checked against SurrealDB 2.3.7, which reports
    ``Database index `idx` already contains 'daily', with record `ep:...```.
    Mocking at the connection is the point: every other test here mocks
    `EpisodeProfile.save` and so never reaches this translation.
    """
    from open_notebook.database.repository import repo_create

    connection = AsyncMock()
    connection.insert.return_value = DUPLICATE_EPISODE
    session = AsyncMock()
    session.__aenter__.return_value = connection

    with (
        patch("open_notebook.database.repository.db_connection", return_value=session),
        pytest.raises(RuntimeError) as caught,
    ):
        await repo_create("episode_profile", {"name": "daily_briefing"})

    connection.insert.assert_awaited_once()
    assert "already contains" in str(caught.value)
    conflict = as_name_conflict(caught.value, "episode profile", "daily_briefing")
    assert isinstance(conflict, ConflictError)
    assert conflict.args[0] == "Episode profile 'daily_briefing' already exists"
