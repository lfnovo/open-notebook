"""POST /sources/{id}/insights refuses sources with no text, so the
transformation job is never queued (#1394)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


@pytest.mark.parametrize("full_text", [None, "", "  \n "])
def test_source_without_text_returns_400_and_queues_nothing(client, full_text):
    with (
        patch(
            "api.routers.sources.Source.get",
            new=AsyncMock(return_value=SimpleNamespace(full_text=full_text)),
        ),
        patch("api.routers.sources.Transformation.get", new=AsyncMock()),
        patch("api.routers.sources.submit_command", new=MagicMock()) as mock_submit,
    ):
        response = client.post(
            "/api/sources/source:abc/insights",
            json={"transformation_id": "transformation:t1"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Source has no text content"
    mock_submit.assert_not_called()


def test_source_with_text_is_queued(client):
    with (
        patch(
            "api.routers.sources.Source.get",
            new=AsyncMock(return_value=SimpleNamespace(full_text="some text")),
        ),
        patch("api.routers.sources.Transformation.get", new=AsyncMock()),
        patch(
            "api.routers.sources.submit_command",
            new=MagicMock(return_value="command:1"),
        ) as mock_submit,
    ):
        response = client.post(
            "/api/sources/source:abc/insights",
            json={"transformation_id": "transformation:t1"},
        )

    assert response.status_code == 202
    mock_submit.assert_called_once()
