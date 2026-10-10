"""Tests for the credentials API endpoint."""

import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

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
        mock_cred.get_linked_models = AsyncMock(return_value=[mock_model1, mock_model2])
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

        response = client.delete("/api/credentials/cred:123?migrate_to=cred:456")

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
        from open_notebook.utils.url_validation import PinnedHttpTarget

        requests = []

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                # Accept httpx.AsyncClient kwargs (e.g. verify=...)
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, extensions=None):
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

        async def fake_prepare_pinned(url, provider):
            return PinnedHttpTarget(url=url)

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(
            credentials_service, "prepare_pinned_http_target", fake_prepare_pinned
        )

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
    @pytest.mark.parametrize(
        "provider,base_url,expected_url",
        [
            # Regional override: mainland-China SiliconFlow accounts (#1409)
            (
                "siliconflow",
                "https://api.siliconflow.cn/v1",
                "https://api.siliconflow.cn/v1/models",
            ),
            ("siliconflow", None, "https://api.siliconflow.com/v1/models"),
            ("zai", None, "https://api.z.ai/api/paas/v4/models"),
            (
                "zai",
                "https://open.bigmodel.cn/api/paas/v4",
                "https://open.bigmodel.cn/api/paas/v4/models",
            ),
        ],
    )
    async def test_registry_provider_discovery_honors_base_url(
        self, monkeypatch, provider, base_url, expected_url
    ):
        """Profile providers list models at the credential's base URL when it
        overrides the default endpoint (pinned like other user URLs)."""
        from open_notebook.utils.url_validation import PinnedHttpTarget

        requested = []
        pinned = []

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, extensions=None):
                requested.append(url)
                return httpx.Response(
                    200,
                    json={"data": [{"id": "model-a"}]},
                    request=httpx.Request("GET", url, headers=headers or {}),
                )

        async def fake_prepare_pinned(url, provider):
            pinned.append(url)
            return PinnedHttpTarget(url=url)

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(
            credentials_service, "prepare_pinned_http_target", fake_prepare_pinned
        )

        config = {"api_key": "sk-test"}
        if base_url:
            config["base_url"] = base_url
        models = await credentials_service.discover_with_config(provider, config)

        assert [m["name"] for m in models] == ["model-a"]
        assert requested == [expected_url]
        assert pinned == ([expected_url] if base_url else [])

    @pytest.mark.asyncio
    async def test_model_discovery_base_url_can_include_models_path(self, monkeypatch):
        """Model discovery should not append /models twice."""
        from open_notebook.utils.url_validation import PinnedHttpTarget

        requests = []

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                # Accept httpx.AsyncClient kwargs (e.g. verify=...)
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, extensions=None):
                requests.append(url)
                return httpx.Response(
                    200,
                    json={"data": [{"id": "model-a"}]},
                    request=httpx.Request("GET", url, headers=headers or {}),
                )

        async def fake_prepare_pinned(url, provider):
            return PinnedHttpTarget(url=url)

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(
            credentials_service, "prepare_pinned_http_target", fake_prepare_pinned
        )

        await credentials_service.discover_with_config(
            "openai_compatible",
            {
                "api_key": "sk-test",
                "base_url": "https://llm-gateway.example.com/v1/models/",
            },
        )

        assert requests == ["https://llm-gateway.example.com/v1/models"]

    @pytest.mark.asyncio
    async def test_anthropic_compatible_discovery_normalizes_models_path(
        self, monkeypatch
    ):
        from open_notebook.utils.url_validation import PinnedHttpTarget

        requests = []

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                # Accept httpx.AsyncClient kwargs (e.g. verify=...)
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, extensions=None):
                requests.append((url, headers))
                return httpx.Response(
                    200,
                    json={"data": [{"id": "model-a"}]},
                    request=httpx.Request("GET", url, headers=headers or {}),
                )

        async def fake_prepare_pinned(url, provider):
            return PinnedHttpTarget(url=url)

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(
            credentials_service, "prepare_pinned_http_target", fake_prepare_pinned
        )

        await credentials_service.discover_with_config(
            "anthropic_compatible",
            {
                "api_key": "sk-test",
                "base_url": "https://llm-gateway.example.com/models",
            },
        )

        assert requests == [
            (
                "https://llm-gateway.example.com/v1/models",
                {"x-api-key": "sk-test", "anthropic-version": "2023-06-01"},
            )
        ]

    @pytest.mark.asyncio
    async def test_openai_discovery_pins_user_supplied_base_url(self, monkeypatch):
        """OpenAI discovery with a custom base_url must go through DNS pinning:
        the rewritten (IP) URL, Host header and SNI extension reach httpx."""
        from open_notebook.utils.url_validation import PinnedHttpTarget

        captured = {}

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                # Accept httpx.AsyncClient kwargs (e.g. verify=...)
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, extensions=None):
                captured["url"] = url
                captured["headers"] = headers
                captured["extensions"] = extensions
                return httpx.Response(
                    200,
                    json={"data": [{"id": "model-a"}]},
                    request=httpx.Request("GET", url, headers=headers or {}),
                )

        pinned_calls = []

        async def fake_prepare_pinned(url, provider):
            pinned_calls.append((url, provider))
            return PinnedHttpTarget(
                url="https://93.184.216.34/v1/models",
                headers={"Host": "llm-gateway.example.com"},
                extensions={"sni_hostname": "llm-gateway.example.com"},
            )

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(
            credentials_service, "prepare_pinned_http_target", fake_prepare_pinned
        )

        await credentials_service.discover_with_config(
            "openai",
            {
                "api_key": "sk-test",
                "base_url": "https://llm-gateway.example.com/v1",
            },
        )

        # The user-supplied URL was pinned...
        assert pinned_calls == [("https://llm-gateway.example.com/v1/models", "openai")]
        # ...and the pinned IP URL + Host header + SNI extension reached httpx,
        # alongside the auth header.
        assert captured["url"] == "https://93.184.216.34/v1/models"
        assert captured["headers"] == {
            "Authorization": "Bearer sk-test",
            "Host": "llm-gateway.example.com",
        }
        assert captured["extensions"] == {"sni_hostname": "llm-gateway.example.com"}


class TestOmlxDiscovery:
    """oMLX uses OpenAI-compatible /v1/models with an optional API key."""

    @pytest.mark.asyncio
    async def test_omlx_discovery_defaults_base_url_and_pins(self, monkeypatch):
        from open_notebook.utils.url_validation import PinnedHttpTarget

        captured = {}
        pinned_calls = []

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                # Accept httpx.AsyncClient kwargs (e.g. verify=...)
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, extensions=None):
                captured["url"] = url
                captured["headers"] = headers
                return httpx.Response(
                    200,
                    json={"data": [{"id": "mlx-model"}]},
                    request=httpx.Request("GET", url, headers=headers or {}),
                )

        async def fake_prepare_pinned(url, provider):
            pinned_calls.append((url, provider))
            return PinnedHttpTarget(url=url)

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(
            credentials_service, "prepare_pinned_http_target", fake_prepare_pinned
        )

        models = await credentials_service.discover_with_config("omlx", {})

        assert models == [{"name": "mlx-model", "provider": "omlx"}]
        assert pinned_calls == [("http://localhost:11435/v1/models", "omlx")]
        assert captured["url"] == "http://localhost:11435/v1/models"
        assert "Authorization" not in (captured["headers"] or {})

    @pytest.mark.asyncio
    async def test_omlx_discovery_sends_optional_api_key(self, monkeypatch):
        from open_notebook.utils.url_validation import PinnedHttpTarget

        captured = {}

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                # Accept httpx.AsyncClient kwargs (e.g. verify=...)
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, extensions=None):
                captured["headers"] = headers
                return httpx.Response(
                    200,
                    json={"data": [{"id": "mlx-model"}]},
                    request=httpx.Request("GET", url, headers=headers or {}),
                )

        async def fake_prepare_pinned(url, provider):
            return PinnedHttpTarget(url=url)

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(
            credentials_service, "prepare_pinned_http_target", fake_prepare_pinned
        )

        await credentials_service.discover_with_config(
            "omlx",
            {
                "api_key": "secret",
                "base_url": "http://127.0.0.1:11435/v1",
            },
        )

        assert captured["headers"]["Authorization"] == "Bearer secret"

    def test_omlx_registry_modalities_and_env(self):
        from api.credentials_service import PROVIDER_ENV_CONFIG, PROVIDER_MODALITIES
        from open_notebook.ai.connection_tester import TEST_MODELS

        assert PROVIDER_MODALITIES["omlx"] == ["language", "embedding"]
        assert PROVIDER_ENV_CONFIG["omlx"]["required"] == ["OMLX_API_BASE"]
        assert PROVIDER_ENV_CONFIG["omlx"]["optional"] == ["OMLX_API_KEY"]
        assert TEST_MODELS["omlx"] == (None, "language")


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


class TestCredentialVertexConfig:
    """Tests for #1151 - Vertex credentials must emit vertex_project/vertex_location."""

    def test_vertex_emits_vertex_prefixed_keys(self):
        from open_notebook.domain.credential import Credential

        cred = Credential(
            name="Vertex",
            provider="vertex",
            modalities=["text_to_speech"],
            project="my-gcp-project",
            location="us-central1",
            credentials_path="/secrets/sa.json",
        )
        config = cred.to_esperanto_config()
        # esperanto's Vertex providers accept vertex_project/vertex_location
        assert config["vertex_project"] == "my-gcp-project"
        assert config["vertex_location"] == "us-central1"
        # The generic keys must NOT be emitted for vertex
        assert "project" not in config
        assert "location" not in config
        # credentials_path is passed through unchanged
        assert config["credentials_path"] == "/secrets/sa.json"

    def test_non_vertex_provider_keeps_generic_keys(self):
        from open_notebook.domain.credential import Credential

        cred = Credential(
            name="Other",
            provider="openai",
            project="my-project",
            location="us-central1",
        )
        config = cred.to_esperanto_config()
        assert config["project"] == "my-project"
        assert config["location"] == "us-central1"
        assert "vertex_project" not in config
        assert "vertex_location" not in config


class TestCredentialAzureApiVersion:
    """#1470 - an Azure credential without an API version must work for models,
    not only for the connection test."""

    AZURE_ENV = (
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_API_VERSION_LLM",
        "AZURE_OPENAI_API_VERSION_EMBEDDING",
        "AZURE_OPENAI_API_VERSION_STT",
        "AZURE_OPENAI_API_VERSION_TTS",
        "OPENAI_API_VERSION",
    )

    def _clear_azure_env(self, monkeypatch):
        # setenv registers an undo, so values the code writes are removed
        # after the test. Esperanto treats an empty value as unset.
        for var in self.AZURE_ENV:
            monkeypatch.setenv(var, "")

    def _azure_credential(self, api_version=None):
        from open_notebook.domain.credential import Credential

        return Credential(
            name="Azure",
            provider="azure",
            modalities=["language"],
            api_key=SecretStr("azure-key"),
            base_url="https://example.openai.azure.com",
            api_version=api_version,
        )

    def test_language_model_builds_without_a_configured_version(self, monkeypatch):
        from esperanto import AIFactory
        from esperanto.providers.llm.azure import AzureLanguageModel

        self._clear_azure_env(monkeypatch)
        config = self._azure_credential().to_esperanto_config()

        # Before the fix Esperanto raised "Azure OpenAI API version not found"
        model = AIFactory.create_language(
            model_name="gpt-4o-1470", provider="azure", config=config
        )
        assert isinstance(model, AzureLanguageModel)
        assert model.api_version == "2024-10-21"

    def test_saved_version_wins(self, monkeypatch):
        self._clear_azure_env(monkeypatch)
        monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
        config = self._azure_credential("2025-01-01-preview").to_esperanto_config()
        assert config["api_version"] == "2025-01-01-preview"

    def test_env_version_is_left_to_esperanto(self, monkeypatch):
        self._clear_azure_env(monkeypatch)
        monkeypatch.setenv("AZURE_OPENAI_API_VERSION_LLM", "2025-04-01-preview")
        assert "api_version" not in self._azure_credential().to_esperanto_config()

    def test_other_providers_get_no_api_version(self, monkeypatch):
        from open_notebook.domain.credential import Credential

        self._clear_azure_env(monkeypatch)
        cred = Credential(name="OpenAI", provider="openai", api_key=SecretStr("sk"))
        assert "api_version" not in cred.to_esperanto_config()

    @pytest.mark.asyncio
    async def test_env_provisioning_sets_the_default_version(self, monkeypatch):
        from types import SimpleNamespace

        from open_notebook.ai import key_provider

        self._clear_azure_env(monkeypatch)
        cred = SimpleNamespace(
            api_key=SecretStr("azure-key"),
            api_version=None,
            endpoint=None,
            base_url="https://example.openai.azure.com",
            endpoint_llm=None,
            endpoint_embedding=None,
            endpoint_stt=None,
            endpoint_tts=None,
        )
        monkeypatch.setattr(
            key_provider, "_get_default_credential", AsyncMock(return_value=cred)
        )

        assert await key_provider._provision_azure() is True
        assert os.environ["AZURE_OPENAI_API_VERSION"] == "2024-10-21"


class TestAudioProviderWiring:
    """Tests for the new audio providers (Mistral STT/TTS, Deepgram TTS, xAI TTS)."""

    def test_classify_voxtral_and_aura(self):
        from open_notebook.ai.model_discovery import classify_model_type

        # Mistral Voxtral: TTS model must not be mis-detected as STT
        assert (
            classify_model_type("voxtral-mini-tts-2603", "mistral") == "text_to_speech"
        )
        assert classify_model_type("voxtral-mini-latest", "mistral") == "speech_to_text"
        assert (
            classify_model_type("voxtral-small-latest", "mistral") == "speech_to_text"
        )
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
        # Deepgram now also does STT (Nova/Whisper), added alongside TTS.
        assert PROVIDER_MODALITIES["deepgram"] == ["text_to_speech", "speech_to_text"]
        # OpenRouter added TTS/STT in esperanto 2.25.0 (issue #987).
        assert "speech_to_text" in PROVIDER_MODALITIES["openrouter"]
        assert "text_to_speech" in PROVIDER_MODALITIES["openrouter"]

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
        assert (
            classify_model_type("gemini-3.1-flash-tts-preview", "google")
            == "text_to_speech"
        )
        assert classify_model_type("gemini-2.5-flash", "google") == "language"
        # ElevenLabs Scribe STT must not be caught by the TTS "eleven" pattern
        assert classify_model_type("scribe_v1", "elevenlabs") == "speech_to_text"
        assert (
            classify_model_type("eleven_multilingual_v2", "elevenlabs")
            == "text_to_speech"
        )

    def test_google_and_vertex_use_floating_alias(self):
        # Regression test for #970: the connection test used a hard-coded
        # Gemini id (gemini-2.0-flash) that Google later shut down, so a
        # valid key failed with 404. Use Google's floating alias, which the
        # provider repoints on each retirement, so it can't go stale.
        from open_notebook.ai.connection_tester import TEST_MODELS

        assert TEST_MODELS["google"] == ("gemini-flash-latest", "language")
        assert TEST_MODELS["vertex"] == ("gemini-flash-latest", "language")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestCredentialUpdateClearsFields:
    """PUT /credentials/{id} must distinguish 'field absent' (keep) from
    'field explicitly null/empty' (clear).

    The handler used `is not None` guards, so an explicit null sent to clear
    base_url (or the Vertex project/location/credentials_path) was silently
    ignored — the old value survived while the client saw success. Found in
    v1.11 release testing: an Ollama credential kept pointing at a stale IP
    after the user cleared the field. Now keyed on model_fields_set.
    """

    def _mock_cred(self):
        from unittest.mock import MagicMock

        cred = MagicMock()
        cred.base_url = "http://10.0.0.99:11434"
        cred.credentials_path = "/old/path.json"
        cred.save = AsyncMock()
        cred.get_linked_models = AsyncMock(return_value=[])
        return cred

    def _put(self, client, cred, body):
        from api.models import CredentialResponse

        fake_response = CredentialResponse(
            id="credential:1",
            name="n",
            provider="ollama",
            modalities=["language"],
            has_api_key=False,
            created="2026-01-01",
            updated="2026-01-01",
            model_count=0,
        )
        with (
            patch("api.routers.credentials.require_encryption_key"),
            patch(
                "api.routers.credentials.Credential.get",
                new=AsyncMock(return_value=cred),
            ),
            patch(
                "api.routers.credentials.credential_to_response",
                return_value=fake_response,
            ),
        ):
            return client.put("/api/credentials/credential:1", json=body)

    def test_explicit_null_clears_base_url(self, client):
        cred = self._mock_cred()
        response = self._put(client, cred, {"base_url": None})
        assert response.status_code == 200
        assert cred.base_url is None
        cred.save.assert_awaited_once()

    def test_empty_string_clears_base_url(self, client):
        cred = self._mock_cred()
        response = self._put(client, cred, {"base_url": ""})
        assert response.status_code == 200
        assert cred.base_url is None

    def test_absent_field_keeps_old_value(self, client):
        cred = self._mock_cred()
        response = self._put(client, cred, {"name": "renamed"})
        assert response.status_code == 200
        assert cred.base_url == "http://10.0.0.99:11434"

    def test_null_clears_vertex_credentials_path(self, client):
        cred = self._mock_cred()
        response = self._put(client, cred, {"credentials_path": None})
        assert response.status_code == 200
        assert cred.credentials_path is None


class TestRegionalBaseUrl:
    """Providers that declare a *_BASE_URL override (SiliconFlow, Z.ai) honor it
    in env migration and env-based discovery; other providers ignore a stored
    base URL for discovery (#1409, #1437)."""

    def test_env_migration_reads_base_url(self, monkeypatch):
        monkeypatch.setenv("SILICONFLOW_API_KEY", "sf-key")
        monkeypatch.setenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")

        cred = credentials_service.create_credential_from_env("siliconflow")

        assert cred.base_url == "https://api.siliconflow.cn/v1"
        assert cred.api_key is not None
        assert cred.api_key.get_secret_value() == "sf-key"

    def test_siliconflow_non_chat_models_are_not_language(self):
        from open_notebook.ai.model_discovery import classify_model_type

        assert classify_model_type("BAAI/bge-m3", "siliconflow") == "embedding"
        assert (
            classify_model_type("FunAudioLLM/SenseVoiceSmall", "siliconflow")
            == "speech_to_text"
        )
        assert (
            classify_model_type("FunAudioLLM/CosyVoice2-0.5B", "siliconflow")
            == "text_to_speech"
        )
        assert classify_model_type("Qwen/Qwen3-8B", "siliconflow") == "language"

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_env_migration_without_base_url(self, monkeypatch, value):
        monkeypatch.setenv("ZAI_API_KEY", "zai-key")
        if value is None:
            monkeypatch.delenv("ZAI_BASE_URL", raising=False)
        else:
            monkeypatch.setenv("ZAI_BASE_URL", value)

        assert credentials_service.create_credential_from_env("zai").base_url is None

    def test_env_migration_reads_zai_base_url(self, monkeypatch):
        monkeypatch.setenv("ZAI_API_KEY", "zai-key")
        monkeypatch.setenv("ZAI_BASE_URL", " https://open.bigmodel.cn/api/paas/v4 ")

        cred = credentials_service.create_credential_from_env("zai")

        assert cred.base_url == "https://open.bigmodel.cn/api/paas/v4"

    @pytest.mark.asyncio
    async def test_env_discovery_uses_base_url(self, monkeypatch):
        from open_notebook.ai import model_discovery

        requested = []

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, **kwargs):
                requested.append(url)
                return httpx.Response(
                    200,
                    json={"data": [{"id": "Qwen/Qwen3-8B"}]},
                    request=httpx.Request("GET", url),
                )

        from open_notebook.utils.url_validation import PinnedHttpTarget

        pinned = []

        async def fake_prepare_pinned(url, provider):
            pinned.append(url)
            return PinnedHttpTarget(url=url)

        monkeypatch.setenv("SILICONFLOW_API_KEY", "sf-key")
        monkeypatch.setenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1/")
        monkeypatch.setattr(model_discovery.httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(
            model_discovery, "prepare_pinned_http_target", fake_prepare_pinned
        )

        models = await model_discovery.discover_openai_compatible_provider(
            "siliconflow"
        )

        assert requested == ["https://api.siliconflow.cn/v1/models"]
        assert pinned == ["https://api.siliconflow.cn/v1/models"]
        assert [m.name for m in models] == ["Qwen/Qwen3-8B"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "env_value,expected",
        [
            (
                "https://open.bigmodel.cn/api/paas/v4",
                "https://open.bigmodel.cn/api/paas/v4/models",
            ),
            ("   ", "https://api.z.ai/api/paas/v4/models"),
        ],
    )
    async def test_zai_env_discovery_override(self, monkeypatch, env_value, expected):
        from open_notebook.ai import model_discovery
        from open_notebook.utils.url_validation import PinnedHttpTarget

        requested = []

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, **kwargs):
                requested.append(url)
                return httpx.Response(
                    200,
                    json={"data": [{"id": "glm-5.2"}]},
                    request=httpx.Request("GET", url),
                )

        async def fake_prepare_pinned(url, provider):
            return PinnedHttpTarget(url=url)

        monkeypatch.setenv("ZAI_API_KEY", "zai-key")
        monkeypatch.setenv("ZAI_BASE_URL", env_value)
        monkeypatch.setattr(model_discovery.httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(
            model_discovery, "prepare_pinned_http_target", fake_prepare_pinned
        )

        await model_discovery.discover_openai_compatible_provider("zai")

        assert requested == [expected]

    @pytest.mark.asyncio
    async def test_providers_without_override_keep_registry_url(self, monkeypatch):
        requested = []

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, extensions=None):
                requested.append(url)
                return httpx.Response(
                    200,
                    json={"data": [{"id": "m"}]},
                    request=httpx.Request("GET", url),
                )

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)

        await credentials_service.discover_with_config(
            "ppq", {"api_key": "k", "base_url": "https://elsewhere.example/v1"}
        )

        # ppq's registry URL carries a provider-specific query string.
        assert requested == ["https://api.ppq.ai/v1/models?type=all"]


class TestEndpointOverrideProvisioningAndMigration:
    """ADR-012: provisioning exposes the registry override name, and env
    migration validates the override before saving."""

    @pytest.mark.asyncio
    async def test_provisioning_sets_registry_base_url_env(self, monkeypatch):
        from types import SimpleNamespace

        from open_notebook.ai import key_provider

        # setenv registers an undo, so the values the code writes are removed
        # after the test.
        for var in (
            "SILICONFLOW_BASE_URL",
            "SILICONFLOW_API_KEY",
            "SILICONFLOW_API_BASE",
        ):
            monkeypatch.setenv(var, "")
        cred = SimpleNamespace(
            api_key=SecretStr("sf-key"), base_url="https://api.siliconflow.cn/v1"
        )
        monkeypatch.setattr(
            key_provider, "_get_default_credential", AsyncMock(return_value=cred)
        )

        assert await key_provider._provision_simple_provider("siliconflow") is True
        assert os.environ["SILICONFLOW_BASE_URL"] == "https://api.siliconflow.cn/v1"
        assert os.environ["SILICONFLOW_API_KEY"] == "sf-key"

    @pytest.mark.asyncio
    async def test_migration_rejects_invalid_base_url(self, monkeypatch):
        from open_notebook.exceptions import InvalidInputError

        monkeypatch.setattr(
            credentials_service,
            "check_env_configured",
            lambda provider: provider == "siliconflow",
        )
        monkeypatch.setattr(credentials_service, "require_encryption_key", lambda: None)
        monkeypatch.setenv("SILICONFLOW_API_KEY", "sf-key")
        monkeypatch.setenv("SILICONFLOW_BASE_URL", "http://169.254.169.254/latest")

        async def fake_validate(url, provider):
            raise InvalidInputError("link-local address not allowed")

        saved = []
        monkeypatch.setattr(credentials_service, "validate_url", fake_validate)
        monkeypatch.setattr(
            credentials_service.Credential,
            "get_by_provider",
            AsyncMock(return_value=[]),
        )

        async def fake_save(self):
            saved.append(self)

        monkeypatch.setattr(credentials_service.Credential, "save", fake_save)

        result = await credentials_service.migrate_from_env()

        assert saved == []
        assert "siliconflow" not in result["migrated"]
        assert any(e.startswith("siliconflow:") for e in result["errors"])


class TestMiniMaxCredentialDiscovery:
    """Credential-based MiniMax discovery seeds its TTS models (#1438)."""

    @pytest.mark.asyncio
    async def test_seeds_tts_models(self, monkeypatch):
        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, extensions=None):
                return httpx.Response(
                    200,
                    json={"data": [{"id": "MiniMax-M3"}]},
                    request=httpx.Request("GET", url, headers=headers or {}),
                )

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)

        models = await credentials_service.discover_with_config(
            "minimax", {"api_key": "mm-test"}
        )

        # Pinned independently of the seed constant.
        assert [m["name"] for m in models] == [
            "MiniMax-M3",
            "speech-2.8-hd",
            "speech-2.8-turbo",
        ]


class TestMiniMaxRegionalBaseUrl:
    """MiniMax declares MINIMAX_BASE_URL (ADR-012): mainland-China keys list
    their models at the regional endpoint (#1438)."""

    def test_registry_declares_override(self):
        from open_notebook.ai.provider_registry import PROVIDERS

        assert PROVIDERS["minimax"].base_url_env == "MINIMAX_BASE_URL"

    @pytest.mark.asyncio
    async def test_credential_discovery_honors_base_url(self, monkeypatch):
        from open_notebook.utils.url_validation import PinnedHttpTarget

        requested = []

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def get(self, url, headers=None, timeout=None, extensions=None):
                requested.append(url)
                return httpx.Response(
                    200,
                    json={"data": [{"id": "MiniMax-M3"}]},
                    request=httpx.Request("GET", url),
                )

        async def fake_prepare_pinned(url, provider):
            return PinnedHttpTarget(url=url)

        monkeypatch.setattr(credentials_service.httpx, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(
            credentials_service, "prepare_pinned_http_target", fake_prepare_pinned
        )

        models = await credentials_service.discover_with_config(
            "minimax", {"api_key": "k", "base_url": "https://api.minimax.cn/v1"}
        )

        assert requested == ["https://api.minimax.cn/v1/models"]
        assert "speech-2.8-hd" in [m["name"] for m in models]
