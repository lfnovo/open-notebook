"""Tests for the credentials API endpoint."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from api import credentials_service


@pytest.fixture
def client():
    """Create test client after environment variables have been cleared by conftest."""
    from api.main import app

    return TestClient(app)


class TestCredentialCascadeDelete:
    """Tests for #651 - deleting credential cascade-deletes linked models."""

    @pytest.mark.asyncio
    @patch("api.routers.credentials.Credential.get")
    async def test_cascade_delete_linked_models(self, mock_get, client):
        """Deleting credential without options cascade-deletes linked models."""
        mock_model1 = AsyncMock()
        mock_model1.id = "model:1"
        mock_model1.provider = "openai"
        mock_model1.name = "gpt-4"

        mock_model2 = AsyncMock()
        mock_model2.id = "model:2"
        mock_model2.provider = "openai"
        mock_model2.name = "gpt-3.5-turbo"

        mock_cred = AsyncMock()
        mock_cred.get_linked_models = AsyncMock(
            return_value=[mock_model1, mock_model2]
        )
        mock_cred.delete = AsyncMock()
        mock_get.return_value = mock_cred

        response = client.delete("/api/credentials/cred:123")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_models"] == 2
        assert data["message"] == "Credential deleted successfully"

        mock_model1.delete.assert_awaited_once()
        mock_model2.delete.assert_awaited_once()
        mock_cred.delete.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("api.routers.credentials.Credential.get")
    async def test_delete_credential_no_linked_models(self, mock_get, client):
        """Deleting credential with no linked models works cleanly."""
        mock_cred = AsyncMock()
        mock_cred.get_linked_models = AsyncMock(return_value=[])
        mock_cred.delete = AsyncMock()
        mock_get.return_value = mock_cred

        response = client.delete("/api/credentials/cred:123")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_models"] == 0
        mock_cred.delete.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("api.routers.credentials.Credential.get")
    async def test_migrate_models_instead_of_delete(self, mock_get, client):
        """Passing migrate_to reassigns models instead of deleting them."""
        mock_model = AsyncMock()
        mock_model.id = "model:1"
        mock_model.credential = "cred:123"
        mock_model.save = AsyncMock()

        mock_cred = AsyncMock()
        mock_cred.get_linked_models = AsyncMock(return_value=[mock_model])
        mock_cred.delete = AsyncMock()

        mock_target_cred = AsyncMock()
        mock_target_cred.id = "cred:456"

        # First call returns cred to delete, second returns target
        mock_get.side_effect = [mock_cred, mock_target_cred]

        response = client.delete(
            "/api/credentials/cred:123?migrate_to=cred:456"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_models"] == 0  # Models were migrated, not deleted
        mock_model.save.assert_awaited_once()
        assert mock_model.credential == "cred:456"
        mock_cred.delete.assert_awaited_once()


class TestCredentialModelDiscovery:
    """Tests for credential-backed model discovery."""

    @pytest.mark.asyncio
    async def test_openai_discovery_respects_base_url(self, monkeypatch):
        """OpenAI model discovery should call the configured API base URL."""

        requests = []

        class FakeAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None):
                requests.append(
                    {
                        "url": url,
                        "headers": headers,
                        "timeout": timeout,
                    }
                )
                return httpx.Response(
                    200,
                    json={"data": [{"id": "custom-openai-model"}]},
                    request=httpx.Request("GET", url, headers=headers or {}),
                )

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)

        models = await credentials_service.discover_with_config(
            "openai",
            {
                "api_key": "sk-test",
                "base_url": "https://llm-gateway.example.com/v1",
            },
        )

        assert models == [
            {
                "name": "custom-openai-model",
                "provider": "openai",
                "description": None,
            }
        ]
        assert requests == [
            {
                "url": "https://llm-gateway.example.com/v1/models",
                "headers": {"Authorization": "Bearer sk-test"},
                "timeout": 30.0,
            }
        ]

    @pytest.mark.asyncio
    async def test_model_discovery_base_url_can_include_models_path(self, monkeypatch):
        """Model discovery should not append /models twice."""

        requests = []

        class FakeAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None):
                requests.append(url)
                return httpx.Response(
                    200,
                    json={"data": [{"id": "model-a"}]},
                    request=httpx.Request("GET", url, headers=headers or {}),
                )

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)

        await credentials_service.discover_with_config(
            "openai_compatible",
            {
                "api_key": "sk-test",
                "base_url": "https://llm-gateway.example.com/v1/models/",
            },
        )

        assert requests == ["https://llm-gateway.example.com/v1/models"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
