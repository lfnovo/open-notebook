"""The podcasts router's catch-all 500s go through typed exceptions (#1430).

Each endpoint's final `except Exception` arm raises `OpenNotebookError` chained to the original error, so the global handler in api/main.py returns it as a 500. The client must still see the same generic message and the raw exception text must never reach the response.

- `test_untyped_error_returns_generic_500` goes through the API and checks that the client still gets 500 with the same message and that the error text doesn't leak.

- `test_fallback_raises_typed_error_chained_to_original` calls the router functions directly and checks that they raise `OpenNotebookError` with the original error as `__cause__`.

- `test_router_calls_service_once_with_request_arguments` checks that the router called the service once and passed the request's arguments through unchanged.
"""

from unittest.mock import AsyncMock, call, patch

import pytest
from fastapi.testclient import TestClient

from api.podcast_service import PodcastGenerationRequest
from api.routers.podcasts import (
    delete_podcast_episode,
    generate_podcast,
    get_podcast_job_status,
    list_podcast_episodes,
    retry_podcast_episode,
)
from open_notebook.exceptions import OpenNotebookError

SECRET = "connection to db-primary-7f3a.internal:5432 refused"

GENERATE_BODY = {
    "episode_profile": "default",
    "speaker_profile": "default",
    "episode_name": "Test Episode",
}

# (name, patched PodcastService method, method, url, json body, generic message)
CASES = [
    (
        "generate",
        "submit_generation_job",
        "POST",
        "/api/podcasts/generate",
        GENERATE_BODY,
        "Failed to generate podcast",
    ),
    (
        "job_status",
        "get_job_status",
        "GET",
        "/api/podcasts/jobs/command:abc",
        None,
        "Failed to fetch job status",
    ),
    (
        "list_episodes",
        "list_episodes",
        "GET",
        "/api/podcasts/episodes",
        None,
        "Failed to list podcast episodes",
    ),
    (
        "retry",
        "get_episode",
        "POST",
        "/api/podcasts/episodes/episode:abc/retry",
        None,
        "Failed to retry episode",
    ),
    (
        "delete",
        "get_episode",
        "DELETE",
        "/api/podcasts/episodes/episode:abc",
        None,
        "Failed to delete episode",
    ),
]


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app, raise_server_exceptions=False)


# STUB: What the client sees
@pytest.mark.parametrize(
    "name, service_method, method, url, body, message",
    CASES,
    ids=[case[0] for case in CASES],
)
def test_untyped_error_returns_generic_500(
    client, name, service_method, method, url, body, message
):
    with patch(
        f"api.routers.podcasts.PodcastService.{service_method}",
        new=AsyncMock(side_effect=RuntimeError(SECRET)),
    ):
        response = client.request(method, url, json=body)

    assert response.status_code == 500
    assert SECRET not in response.text
    assert response.json()["detail"] == message


# (name, patched PodcastService method, endpoint call)
DIRECT_CASES = [
    (
        "generate",
        "submit_generation_job",
        lambda: generate_podcast(PodcastGenerationRequest(**GENERATE_BODY)),
    ),
    ("job_status", "get_job_status", lambda: get_podcast_job_status("command:abc")),
    ("list_episodes", "list_episodes", lambda: list_podcast_episodes()),
    ("retry", "get_episode", lambda: retry_podcast_episode("episode:abc")),
    ("delete", "get_episode", lambda: delete_podcast_episode("episode:abc")),
]


# STUB: Which exception the router raises
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name, service_method, call",
    DIRECT_CASES,
    ids=[case[0] for case in DIRECT_CASES],
)
async def test_fallback_raises_typed_error_chained_to_original(
    name, service_method, call
):
    original = RuntimeError(SECRET)
    with patch(
        f"api.routers.podcasts.PodcastService.{service_method}",
        new=AsyncMock(side_effect=original),
    ):
        with pytest.raises(OpenNotebookError) as exc_info:
            await call()

    assert exc_info.value.__cause__ is original
    assert SECRET not in str(exc_info.value)


# (name, patched PodcastService method, endpoint call, expected service call)
MOCK_CASES = [
    (
        "generate",
        "submit_generation_job",
        lambda: generate_podcast(PodcastGenerationRequest(**GENERATE_BODY)),
        call(
            episode_profile_name="default",
            speaker_profile_name="default",
            episode_name="Test Episode",
            notebook_id=None,
            content=None,
            briefing_suffix=None,
        ),
    ),
    (
        "job_status",
        "get_job_status",
        lambda: get_podcast_job_status("command:abc"),
        call("command:abc"),
    ),
    (
        "list_episodes",
        "list_episodes",
        lambda: list_podcast_episodes(),
        call(),
    ),
    (
        "retry",
        "get_episode",
        lambda: retry_podcast_episode("episode:abc"),
        call("episode:abc"),
    ),
    (
        "delete",
        "get_episode",
        lambda: delete_podcast_episode("episode:abc"),
        call("episode:abc"),
    ),
]


# MOCK: how the router calls the service (once, with the request's arguments)
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name, service_method, endpoint_call, expected_call",
    MOCK_CASES,
    ids=[case[0] for case in MOCK_CASES],
)
async def test_router_calls_service_once_with_request_arguments(
    name, service_method, endpoint_call, expected_call
):
    with patch(
        f"api.routers.podcasts.PodcastService.{service_method}",
        new=AsyncMock(side_effect=RuntimeError(SECRET)),
    ) as service_mock:
        with pytest.raises(OpenNotebookError):
            await endpoint_call()

    service_mock.assert_awaited_once()
    assert service_mock.await_args == expected_call
