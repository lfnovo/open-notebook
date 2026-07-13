"""Typed domain exceptions must reach the global handlers in api/main.py.

The routers used to wrap endpoint bodies in a broad `except Exception` that
re-raised everything as a generic HTTPException(500), swallowing the typed
`open_notebook.exceptions` hierarchy before the global handlers could map it
to its documented status code (NotFoundError -> 404, InvalidInputError -> 400,
ConfigurationError -> 422, RateLimitError -> 429, NetworkError /
ExternalServiceError -> 502, ...).

Each case here mocks a domain-layer call inside one router to raise
`ConfigurationError` and asserts the response is 422 (per the global handler)
instead of a generic 500. One case per fixed router.

Untyped exceptions must still be caught by the routers' final
`except Exception` arm and return a sanitized 500 (see
tests/test_error_message_sanitization.py); a regression case for that
guarantee is included at the bottom.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.exceptions import ConfigurationError, NotFoundError

CONFIG_ERROR_MESSAGE = "No default model configured. Set one in the Models section."


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app, raise_server_exceptions=False)


def _boom(*_args, **_kwargs):
    raise ConfigurationError(CONFIG_ERROR_MESSAGE)


# (router, patch target, method, url, json body) — one per fixed router.
CASES = [
    ("chat", "api.routers.chat.Notebook.get", "GET", "/api/chat/sessions?notebook_id=notebook:1", None),
    ("source_chat", "api.routers._chat_shared.Source.get", "GET", "/api/sources/xyz/chat/sessions", None),
    ("sources", "api.routers.sources.repo_query", "GET", "/api/sources", None),
    ("notebooks", "api.routers.notebooks.repo_query", "GET", "/api/notebooks", None),
    ("notes", "api.routers.notes.Note.get_all", "GET", "/api/notes", None),
    ("models", "api.routers.models.Model.get_all", "GET", "/api/models", None),
    ("commands", "api.routers.commands.CommandService.get_command_status", "GET", "/api/commands/jobs/command:abc", None),
    ("credentials", "api.routers.credentials.Credential.get_all", "GET", "/api/credentials", None),
    ("embedding", "api.routers.embedding.model_manager.get_embedding_model", "POST", "/api/embed", {"item_id": "source:1", "item_type": "source"}),
    ("embedding_rebuild", "api.routers.embedding_rebuild.repo_query", "POST", "/api/embeddings/rebuild", {"mode": "existing"}),
    ("episode_profiles", "api.routers.episode_profiles.EpisodeProfile.get_all", "GET", "/api/episode-profiles", None),
    ("insights", "api.routers.insights.SourceInsight.get", "GET", "/api/insights/source_insight:1", None),
    ("podcasts", "api.routers.podcasts.PodcastService.list_episodes", "GET", "/api/podcasts/episodes", None),
    ("search", "api.routers.search.text_search", "POST", "/api/search", {"query": "hello", "type": "text"}),
    ("settings", "api.routers.settings.ContentSettings.get_instance", "GET", "/api/settings", None),
    ("speaker_profiles", "api.routers.speaker_profiles.SpeakerProfile.get_all", "GET", "/api/speaker-profiles", None),
    ("transformations", "api.routers.transformations.Transformation.get_all", "GET", "/api/transformations", None),
]


@pytest.mark.parametrize(
    "router, target, method, url, body",
    CASES,
    ids=[case[0] for case in CASES],
)
def test_configuration_error_maps_to_422(client, router, target, method, url, body):
    with patch(target, new=AsyncMock(side_effect=_boom)):
        response = client.request(method, url, json=body)

    assert response.status_code == 422, (
        f"{router}: expected ConfigurationError to reach the global handler "
        f"(422), got {response.status_code}: {response.text}"
    )
    assert response.json()["detail"] == CONFIG_ERROR_MESSAGE


class TestNotFoundErrorPropagation:
    """NotFoundError raised by the domain layer maps to 404 where the router
    has no dedicated `except NotFoundError` arm (it used to become a 500)."""

    def test_get_credential_missing_returns_404(self, client):
        with patch(
            "api.routers.credentials.Credential.get",
            new=AsyncMock(side_effect=NotFoundError("Credential not found")),
        ):
            response = client.get("/api/credentials/credential:missing")

        assert response.status_code == 404
        assert response.json()["detail"] == "Credential not found"


class TestUnsupportedTypeErrorPropagation:
    """UnsupportedTypeException maps to 415 (Unsupported Media Type) via its
    dedicated global handler, instead of falling through to the base
    OpenNotebookError handler's 500 (#975)."""

    def test_unsupported_type_maps_to_415(self, client):
        from open_notebook.exceptions import UnsupportedTypeException

        with patch(
            "api.routers.sources.repo_query",
            new=AsyncMock(
                side_effect=UnsupportedTypeException(
                    "Unsupported file type: application/zip"
                )
            ),
        ):
            response = client.get("/api/sources")

        assert response.status_code == 415
        assert "application/zip" in response.json()["detail"]


class TestUntypedExceptionsStillSanitized:
    """The final `except Exception` arm must keep catching untyped errors and
    returning a fixed, sanitized 500 (never the raw exception text)."""

    SECRET = "password authentication failed for db-primary"

    def test_runtime_error_stays_generic_500(self, client):
        with patch(
            "api.routers.sources.repo_query",
            new=AsyncMock(side_effect=RuntimeError(self.SECRET)),
        ):
            response = client.get("/api/sources")

        assert response.status_code == 500
        assert self.SECRET not in response.text
        assert response.json()["detail"] == "Error fetching sources"
