"""GET/PUT /api/settings for the Docling vision endpoint fields (#1561)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

VISION_URL = "http://192.168.1.20:1234/v1/chat/completions"


@pytest.fixture
def client():
    """Create test client after environment variables have been cleared by conftest."""
    from api.main import app

    return TestClient(app)


def _stored_settings(**overrides):
    """A ContentSettings stand-in whose update() keeps the assigned values."""
    fields = {
        "default_content_processing_engine_doc": "docling",
        "default_content_processing_engine_url": "auto",
        "default_embedding_option": "ask",
        "auto_delete_files": "yes",
        "docling_ocr": True,
        "docling_formulas": False,
        "docling_vision": True,
        "docling_vision_url": None,
        "docling_vision_model": None,
        "docling_vision_prompt": None,
        "youtube_preferred_languages": ["en"],
    }
    settings = SimpleNamespace(**{**fields, **overrides})
    settings.update = AsyncMock(return_value=settings)
    return settings


def _patch_settings(settings):
    """Serve `settings` from ContentSettings.get_instance in the router."""
    return patch(
        "api.routers.settings.ContentSettings.get_instance",
        new=AsyncMock(return_value=settings),
    )


class TestDoclingVisionSettings:
    def test_get_returns_vision_fields(self, client):
        settings = _stored_settings(
            docling_vision_url=VISION_URL,
            docling_vision_model="qwen2.5-vl-7b",
            docling_vision_prompt="Describe the chart.",
        )
        with _patch_settings(settings):
            response = client.get("/api/settings")

        assert response.status_code == 200
        body = response.json()
        assert body["docling_vision_url"] == VISION_URL
        assert body["docling_vision_model"] == "qwen2.5-vl-7b"
        assert body["docling_vision_prompt"] == "Describe the chart."
        assert "docling_vision_api_key" not in body

    def test_put_stores_trimmed_vision_fields(self, client):
        settings = _stored_settings()
        with _patch_settings(settings):
            response = client.put(
                "/api/settings",
                json={
                    "docling_vision_url": f"  {VISION_URL} ",
                    "docling_vision_model": " qwen2.5-vl-7b",
                    "docling_vision_prompt": "Describe the chart.\n",
                },
            )

        assert response.status_code == 200
        settings.update.assert_awaited_once()
        assert settings.docling_vision_url == VISION_URL
        assert settings.docling_vision_model == "qwen2.5-vl-7b"
        assert settings.docling_vision_prompt == "Describe the chart."
        assert response.json()["docling_vision_url"] == VISION_URL

    def test_put_empty_strings_clear_vision_fields(self, client):
        """Clearing a field stores None, so the env var applies again."""
        settings = _stored_settings(
            docling_vision_url=VISION_URL,
            docling_vision_model="qwen2.5-vl-7b",
            docling_vision_prompt="Describe the chart.",
        )
        with _patch_settings(settings):
            response = client.put(
                "/api/settings",
                json={
                    "docling_vision_url": "",
                    "docling_vision_model": "   ",
                    "docling_vision_prompt": "",
                },
            )

        assert response.status_code == 200
        assert settings.docling_vision_url is None
        assert settings.docling_vision_model is None
        assert settings.docling_vision_prompt is None

    def test_put_without_vision_fields_leaves_them_unchanged(self, client):
        settings = _stored_settings(
            docling_vision_url=VISION_URL, docling_vision_model="qwen2.5-vl-7b"
        )
        with _patch_settings(settings):
            response = client.put("/api/settings", json={"docling_ocr": False})

        assert response.status_code == 200
        assert settings.docling_ocr is False
        assert settings.docling_vision_url == VISION_URL
        assert settings.docling_vision_model == "qwen2.5-vl-7b"

    @pytest.mark.parametrize(
        "bad_url",
        [
            "http://169.254.169.254/latest/meta-data/",
            "file:///etc/passwd",
            "ftp://192.168.1.20/v1/chat/completions",
        ],
    )
    def test_put_rejects_unsafe_vision_url(self, bad_url, client):
        """The vision URL goes through validate_url() like every other
        user-supplied URL, and a rejected URL is not saved."""
        settings = _stored_settings(docling_vision_url=VISION_URL)
        with _patch_settings(settings):
            response = client.put("/api/settings", json={"docling_vision_url": bad_url})

        assert response.status_code == 400
        settings.update.assert_not_awaited()
        assert settings.docling_vision_url == VISION_URL

    def test_rejected_vision_url_leaves_other_fields_untouched(self, client):
        """The form sends every field in one PUT; a bad URL must not leave the
        other fields applied to the in-memory settings either."""
        settings = _stored_settings(docling_ocr=True)
        with _patch_settings(settings):
            response = client.put(
                "/api/settings",
                json={
                    "docling_ocr": False,
                    "docling_vision_url": "http://169.254.169.254/latest/meta-data/",
                },
            )

        assert response.status_code == 400
        assert settings.docling_ocr is True
        settings.update.assert_not_awaited()
