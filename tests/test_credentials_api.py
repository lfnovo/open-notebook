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


class TestCredentialNumCtx:
    """Tests for the Ollama num_ctx override threaded into esperanto config."""

    def test_num_ctx_included_when_set(self):
        from open_notebook.domain.credential import Credential

        cred = Credential(
            name="Local Ollama",
            provider="ollama",
            modalities=["language", "embedding"],
            base_url="http://localhost:11434",
            num_ctx=32768,
        )
        config = cred.to_esperanto_config()
        assert config["num_ctx"] == 32768
        assert config["base_url"] == "http://localhost:11434"

    def test_num_ctx_absent_when_unset(self):
        from open_notebook.domain.credential import Credential

        cred = Credential(
            name="Local Ollama",
            provider="ollama",
            base_url="http://localhost:11434",
        )
        assert "num_ctx" not in cred.to_esperanto_config()


class TestAudioProviderWiring:
    """Tests for the new audio providers (Mistral STT/TTS, Deepgram TTS, xAI TTS)."""

    def test_classify_voxtral_and_aura(self):
        from open_notebook.ai.model_discovery import classify_model_type

        # Mistral Voxtral: TTS model must not be mis-detected as STT
        assert classify_model_type("voxtral-mini-tts-2603", "mistral") == "text_to_speech"
        assert classify_model_type("voxtral-mini-latest", "mistral") == "speech_to_text"
        assert classify_model_type("voxtral-small-latest", "mistral") == "speech_to_text"
        # Existing Mistral classification still holds
        assert classify_model_type("mistral-large-latest", "mistral") == "language"
        assert classify_model_type("mistral-embed", "mistral") == "embedding"
        # Deepgram Aura voices
        assert classify_model_type("aura-2-thalia-en", "deepgram") == "text_to_speech"

    def test_provider_modalities_include_audio(self):
        from api.credentials_service import PROVIDER_MODALITIES

        assert "speech_to_text" in PROVIDER_MODALITIES["mistral"]
        assert "text_to_speech" in PROVIDER_MODALITIES["mistral"]
        assert "text_to_speech" in PROVIDER_MODALITIES["xai"]
        assert PROVIDER_MODALITIES["deepgram"] == ["text_to_speech"]

    def test_deepgram_has_env_and_test_model(self):
        from api.credentials_service import PROVIDER_ENV_CONFIG
        from open_notebook.ai.connection_tester import TEST_MODELS

        assert PROVIDER_ENV_CONFIG["deepgram"]["required"] == ["DEEPGRAM_API_KEY"]
        assert TEST_MODELS["deepgram"][1] == "text_to_speech"


class TestAudioMatrixWiring:
    """Tests for completing the audio matrix (Google/Vertex TTS, Google/ElevenLabs STT)."""

    def test_provider_modalities_matrix(self):
        from api.credentials_service import PROVIDER_MODALITIES

        for m in ("speech_to_text", "text_to_speech"):
            assert m in PROVIDER_MODALITIES["google"]
        assert "text_to_speech" in PROVIDER_MODALITIES["vertex"]
        assert "speech_to_text" in PROVIDER_MODALITIES["elevenlabs"]

    def test_classify_matrix(self):
        from open_notebook.ai.model_discovery import classify_model_type

        # Gemini TTS preview is classifiable; plain Gemini STT name stays language
        assert classify_model_type("gemini-3.1-flash-tts-preview", "google") == "text_to_speech"
        assert classify_model_type("gemini-2.5-flash", "google") == "language"
        # ElevenLabs Scribe STT must not be caught by the TTS "eleven" pattern
        assert classify_model_type("scribe_v1", "elevenlabs") == "speech_to_text"
        assert classify_model_type("eleven_multilingual_v2", "elevenlabs") == "text_to_speech"

    def test_google_and_vertex_use_floating_alias(self):
        # Regression test for #970: the connection test used a hard-coded
        # Gemini id (gemini-2.0-flash) that Google later shut down, so a
        # valid key failed with 404. Use Google's floating alias, which the
        # provider repoints on each retirement, so it can't go stale.
        from open_notebook.ai.connection_tester import TEST_MODELS

        assert TEST_MODELS["google"] == ("gemini-flash-latest", "language")
        assert TEST_MODELS["vertex"] == ("gemini-flash-latest", "language")


class TestOmlxProviderWiring:
    """First-class oMLX provider (maps to Esperanto openai-compatible)."""

    def test_modalities_and_env_config(self):
        from api.credentials_service import PROVIDER_ENV_CONFIG, PROVIDER_MODALITIES
        from open_notebook.ai.connection_tester import TEST_MODELS

        assert PROVIDER_MODALITIES["omlx"] == ["language", "embedding"]
        assert PROVIDER_ENV_CONFIG["omlx"]["required"] == ["OMLX_API_BASE"]
        assert "OMLX_API_KEY" in PROVIDER_ENV_CONFIG["omlx"]["optional"]
        assert TEST_MODELS["omlx"] == (None, "language")

    def test_create_credential_from_env(self, monkeypatch):
        from api.credentials_service import create_credential_from_env

        monkeypatch.setenv("OMLX_API_BASE", "http://localhost:11435/v1")
        monkeypatch.setenv("OMLX_API_KEY", "test-key")
        cred = create_credential_from_env("omlx")
        assert cred.provider == "omlx"
        assert cred.base_url == "http://localhost:11435/v1"
        assert cred.api_key is not None
        assert cred.api_key.get_secret_value() == "test-key"
        assert set(cred.modalities) == {"language", "embedding"}

    def test_create_credential_from_env_without_api_key(self, monkeypatch):
        from api.credentials_service import create_credential_from_env

        monkeypatch.setenv("OMLX_API_BASE", "http://localhost:11435/v1")
        monkeypatch.delenv("OMLX_API_KEY", raising=False)
        cred = create_credential_from_env("omlx")
        assert cred.api_key is None
        assert cred.base_url == "http://localhost:11435/v1"

    def test_create_credential_from_env_defaults_base_url(self, monkeypatch):
        from api.credentials_service import create_credential_from_env

        monkeypatch.delenv("OMLX_API_BASE", raising=False)
        monkeypatch.delenv("OMLX_API_KEY", raising=False)
        cred = create_credential_from_env("omlx")
        assert cred.base_url == "http://localhost:11435/v1"

    def test_to_esperanto_config_defaults_base_url(self):
        from open_notebook.domain.credential import Credential

        cred = Credential(name="Local oMLX", provider="omlx", modalities=["language"])
        config = cred.to_esperanto_config()
        assert config["base_url"] == "http://localhost:11435/v1"

    def test_to_esperanto_config_keeps_explicit_base_url(self):
        from open_notebook.domain.credential import Credential

        cred = Credential(
            name="Remote oMLX",
            provider="omlx",
            modalities=["language"],
            base_url="http://192.168.1.10:11435/v1",
        )
        config = cred.to_esperanto_config()
        assert config["base_url"] == "http://192.168.1.10:11435/v1"

    def test_classify_embedding_models(self):
        from open_notebook.ai.model_discovery import classify_model_type

        assert classify_model_type("bge-m3", "omlx") == "embedding"
        assert classify_model_type("nomic-embed-text", "omlx") == "embedding"
        assert classify_model_type("llama-3.2-3b", "omlx") == "language"

    def test_esperanto_provider_remap(self):
        from open_notebook.ai.models import to_esperanto_provider

        assert to_esperanto_provider("omlx") == "openai-compatible"
        assert to_esperanto_provider("openai_compatible") == "openai-compatible"
        assert to_esperanto_provider("ollama") == "ollama"

    @pytest.mark.asyncio
    async def test_discover_omlx_models_avoids_double_models_path(self, monkeypatch):
        """Global oMLX discovery should not append /models twice."""
        from open_notebook.ai import model_discovery

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
                    json={"data": [{"id": "llama-3.2-3b"}]},
                    request=httpx.Request("GET", url, headers=headers or {}),
                )

        async def fake_get_by_provider(provider):
            return []

        async def fake_validate_url(url, provider):
            return None

        monkeypatch.setattr(
            model_discovery.Credential, "get_by_provider", fake_get_by_provider
        )
        monkeypatch.setattr(model_discovery, "validate_url", fake_validate_url)
        monkeypatch.setattr(model_discovery.httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setenv("OMLX_API_BASE", "http://localhost:11435/v1/models/")
        monkeypatch.delenv("OMLX_API_KEY", raising=False)

        models = await model_discovery.discover_omlx_models()

        assert requests == ["http://localhost:11435/v1/models"]
        assert len(models) == 1
        assert models[0].name == "llama-3.2-3b"
        assert models[0].provider == "omlx"

    @pytest.mark.asyncio
    async def test_discover_omlx_models_revalidates_url(self, monkeypatch):
        """DNS-rebinding guard: validate_url runs immediately before the request."""
        from open_notebook.ai import model_discovery

        validated = []

        async def fake_get_by_provider(provider):
            return []

        async def fake_validate_url(url, provider):
            validated.append((url, provider))
            raise ValueError("Blocked URL")

        monkeypatch.setattr(
            model_discovery.Credential, "get_by_provider", fake_get_by_provider
        )
        monkeypatch.setattr(model_discovery, "validate_url", fake_validate_url)
        monkeypatch.setenv("OMLX_API_BASE", "http://evil.example/v1")
        monkeypatch.delenv("OMLX_API_KEY", raising=False)

        models = await model_discovery.discover_omlx_models()

        assert validated == [("http://evil.example/v1", "omlx")]
        assert models == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
