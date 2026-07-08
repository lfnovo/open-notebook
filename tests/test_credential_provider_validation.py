"""
Tests for the Literal[...] constraint on CreateCredentialRequest.provider
(api/models.py). Previously `provider: str` accepted any string; a typo'd
or bogus provider would flow through to the domain layer and fail later
with a less clear error instead of a clean 422 at the API boundary.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.models import CreateCredentialRequest, SupportedProvider

KNOWN_GOOD_PROVIDERS = [
    "openai",
    "anthropic",
    "google",
    "groq",
    "mistral",
    "deepseek",
    "xai",
    "openrouter",
    "dashscope",
    "minimax",
    "voyage",
    "elevenlabs",
    "deepgram",
    "ollama",
    "azure",
    "vertex",
    "openai_compatible",
]


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestSupportedProviderMatchesOtherSourcesOfTruth:
    def test_matches_frontend_backend_and_env_config_provider_lists(self):
        """Cross-checked against ALL_PROVIDERS in
        frontend/src/app/(dashboard)/settings/api-keys/page.tsx,
        TEST_MODELS in open_notebook/ai/connection_tester.py, and
        PROVIDER_ENV_CONFIG in api/credentials_service.py - all three
        independently agree on this exact set."""
        assert set(SupportedProvider.__args__) == set(KNOWN_GOOD_PROVIDERS)

    def test_matches_connection_tester_test_models_keys(self):
        from open_notebook.ai.connection_tester import TEST_MODELS

        assert set(SupportedProvider.__args__) == set(TEST_MODELS.keys())

    def test_matches_credentials_service_provider_env_config_keys(self):
        from api.credentials_service import PROVIDER_ENV_CONFIG

        assert set(SupportedProvider.__args__) == set(PROVIDER_ENV_CONFIG.keys())


class TestCreateCredentialRequestValidation:
    @pytest.mark.parametrize("provider", KNOWN_GOOD_PROVIDERS)
    def test_accepts_every_known_provider(self, provider):
        request = CreateCredentialRequest(name="Test", provider=provider)
        assert request.provider == provider

    @pytest.mark.parametrize(
        "bad_provider",
        ["openai ", " openai", "OpenAI", "opnai", "not_a_real_provider", "", "sqlite"],
    )
    def test_rejects_unknown_or_malformed_provider(self, bad_provider):
        with pytest.raises(ValidationError):
            CreateCredentialRequest(name="Test", provider=bad_provider)


class TestCreateCredentialEndpointRejectsBadProvider:
    def test_post_credentials_with_bogus_provider_returns_422(self, client):
        response = client.post(
            "/api/credentials",
            json={"name": "Test", "provider": "not_a_real_provider"},
        )
        assert response.status_code == 422

    def test_post_credentials_with_valid_provider_passes_validation(
        self, client, monkeypatch
    ):
        """Doesn't assert overall success (that needs DB/encryption setup,
        covered elsewhere) - just that a valid provider clears the 422
        validation gate and reaches actual route logic."""
        response = client.post(
            "/api/credentials",
            json={"name": "Test", "provider": "openai", "api_key": "sk-test"},
        )
        assert response.status_code != 422
