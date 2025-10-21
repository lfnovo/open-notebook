import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from open_notebook.domain.content_settings import ContentSettings

client = TestClient(app)


@pytest.fixture
def fresh_settings():
    ContentSettings.clear_instance()
    settings = ContentSettings()
    try:
        yield settings
    finally:
        ContentSettings.clear_instance()


def test_get_settings_returns_provider_credentials(monkeypatch, fresh_settings):
    settings = fresh_settings
    settings.provider_credentials = {"OPENAI_API_KEY": "sk-test"}

    apply_calls = {"count": 0}

    original_apply = ContentSettings.apply_provider_credentials

    def tracked_apply(self):
        apply_calls["count"] += 1
        original_apply(self)

    monkeypatch.setattr(
        ContentSettings,
        "apply_provider_credentials",
        tracked_apply,
    )

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    mock_get_instance = AsyncMock(return_value=settings)

    with patch(
        "api.routers.settings.ContentSettings.get_instance",
        new=mock_get_instance,
    ):
        response = client.get("/api/settings")

    mock_get_instance.assert_awaited_once()
    assert apply_calls["count"] == 1
    assert response.status_code == 200
    assert response.json()["provider_credentials"] == {"OPENAI_API_KEY": "sk-test"}
    assert os.environ["OPENAI_API_KEY"] == "sk-test"


def test_update_settings_normalizes_provider_credentials(monkeypatch, fresh_settings):
    settings = fresh_settings
    settings.provider_credentials = {
        "EXISTING_KEY": "keep-me",
        "SHOULD_REMOVE": "value",
    }
    update_mock = AsyncMock(return_value=settings)
    monkeypatch.setattr(ContentSettings, "update", update_mock)

    apply_calls = {"count": 0}

    original_apply = ContentSettings.apply_provider_credentials

    def tracked_apply(self):
        apply_calls["count"] += 1
        original_apply(self)

    monkeypatch.setattr(
        ContentSettings,
        "apply_provider_credentials",
        tracked_apply,
    )

    monkeypatch.setenv("EXISTING_KEY", "keep-me")
    monkeypatch.setenv("SHOULD_REMOVE", "value")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    payload = {
        "provider_credentials": {
            " openai_api_key ": "  new-key  ",
            "existing_key": None,
            "should_remove": "   ",
        }
    }

    mock_get_instance = AsyncMock(return_value=settings)

    with patch(
        "api.routers.settings.ContentSettings.get_instance",
        new=mock_get_instance,
    ):
        response = client.put("/api/settings", json=payload)

    mock_get_instance.assert_awaited_once()
    update_mock.assert_awaited_once()
    assert apply_calls["count"] == 1

    assert response.status_code == 200
    assert response.json()["provider_credentials"] == {"OPENAI_API_KEY": "new-key"}

    assert settings.provider_credentials == {"OPENAI_API_KEY": "new-key"}
    assert os.environ.get("OPENAI_API_KEY") == "new-key"
    assert "EXISTING_KEY" not in os.environ
    assert "SHOULD_REMOVE" not in os.environ
