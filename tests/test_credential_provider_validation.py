"""
Tests for the Literal[...] constraint on CreateCredentialRequest.provider
(api/models.py). Previously `provider: str` accepted any string; a typo'd
or bogus provider would flow through to the domain layer and fail later
with a less clear error instead of a clean 422 at the API boundary.

Also the sync-enforcement for the provider registry
(open_notebook/ai/provider_registry.py): the registry is the backend
source of truth, and the one remaining manual copy (the
SupportedProvider Literal) must match it exactly. The frontend consumes
GET /api/providers at runtime, so it needs no cross-check.
"""

from typing import get_args

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.models import CreateCredentialRequest, SupportedProvider
from open_notebook.ai.provider_registry import PROVIDERS

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
    "omlx",
    "azure",
    "vertex",
    "openai_compatible",
]


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestProviderRegistryIsTheSourceOfTruth:
    """The registry drives every backend surface; the Literal is the only
    manual copy and must match it."""

    def test_literal_matches_registry_keys(self):
        assert set(get_args(SupportedProvider)) == set(PROVIDERS.keys())

    def test_registry_matches_known_good_provider_list(self):
        assert set(PROVIDERS.keys()) == set(KNOWN_GOOD_PROVIDERS)

    def test_registry_specs_are_internally_consistent(self):
        for name, spec in PROVIDERS.items():
            assert spec.name == name
            assert spec.display_name
            assert spec.modalities, f"{name} has no modalities"
            assert spec.required_env or spec.required_any_env, (
                f"{name} has no env var configuration"
            )
            if spec.openai_compat_discovery_url:
                # The discovery table takes the API key from required_env[0]
                assert len(spec.required_env) == 1, (
                    f"{name} uses openai-compat discovery but does not have "
                    f"exactly one required env var"
                )

    def test_discovery_functions_cover_registry(self):
        from open_notebook.ai.model_discovery import PROVIDER_DISCOVERY_FUNCTIONS

        assert set(PROVIDER_DISCOVERY_FUNCTIONS.keys()) == set(PROVIDERS.keys())

    def test_registry_rejects_duplicate_provider_names(self):
        """A plain dict comprehension would silently drop the earlier spec
        on a name collision; the registry builder must raise instead."""
        from open_notebook.ai.provider_registry import (
            ProviderSpec,
            _build_registry,
        )

        duplicate = (
            ProviderSpec(name="dupe", display_name="Dupe A", modalities=("language",)),
            ProviderSpec(name="dupe", display_name="Dupe B", modalities=("language",)),
        )
        with pytest.raises(ValueError, match="Duplicate provider name"):
            _build_registry(duplicate)

    def test_openai_compat_discovery_urls_are_exactly_as_expected(self):
        """Pin the derived provider -> discovery URL mapping so a registry
        edit can't silently drop or misassign a URL (both the model_discovery
        table and the credentials_service url_map are built from these)."""
        from open_notebook.ai.model_discovery import OPENAI_COMPAT_PROVIDERS

        expected = {
            "openai": "https://api.openai.com/v1/models",
            "groq": "https://api.groq.com/openai/v1/models",
            "mistral": "https://api.mistral.ai/v1/models",
            "deepseek": "https://api.deepseek.com/models",
            "xai": "https://api.x.ai/v1/models",
            "openrouter": "https://openrouter.ai/api/v1/models",
            "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
            "minimax": "https://api.minimax.io/v1/models",
        }
        assert {
            name: spec.openai_compat_discovery_url
            for name, spec in PROVIDERS.items()
            if spec.openai_compat_discovery_url
        } == expected
        assert {
            name: spec.url for name, spec in OPENAI_COMPAT_PROVIDERS.items()
        } == expected


class TestSupportedProviderMatchesOtherSourcesOfTruth:
    def test_matches_known_good_provider_list(self):
        assert set(get_args(SupportedProvider)) == set(KNOWN_GOOD_PROVIDERS)

    def test_matches_connection_tester_test_models_keys(self):
        from open_notebook.ai.connection_tester import TEST_MODELS

        assert set(get_args(SupportedProvider)) == set(TEST_MODELS.keys())

    def test_matches_credentials_service_provider_env_config_keys(self):
        from api.credentials_service import PROVIDER_ENV_CONFIG

        assert set(get_args(SupportedProvider)) == set(PROVIDER_ENV_CONFIG.keys())


class TestProvidersEndpoint:
    def test_get_providers_returns_registry_metadata(self, client):
        response = client.get("/api/providers")
        assert response.status_code == 200
        data = response.json()
        # The frontend renders providers in response order, so the endpoint
        # must preserve the registry declaration order (the display order).
        assert [p["name"] for p in data] == list(PROVIDERS.keys())

        openai = next(p for p in data if p["name"] == "openai")
        assert openai["display_name"] == "OpenAI"
        assert "language" in openai["modalities"]
        assert openai["docs_url"].startswith("https://")
        assert isinstance(openai["env_configured"], bool)


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
        """Doesn't assert overall success - just that a valid provider clears
        the 422 validation gate and reaches actual route logic.

        The encryption-key gate is forced to fail so the request never reaches
        the persistence layer: without this, running the suite with a real
        `.env` (SURREAL_URL + encryption key set) wrote a "Test" credential to
        the live dev database on every run.
        """
        from api.routers import credentials as credentials_router

        def _no_key():
            raise ValueError("encryption key intentionally absent in tests")

        monkeypatch.setattr(credentials_router, "require_encryption_key", _no_key)
        response = client.post(
            "/api/credentials",
            json={"name": "Test", "provider": "openai", "api_key": "sk-test"},
        )
        # Provider validation happens before the route body runs; the forced
        # key failure maps to a non-422 error, proving validation was cleared
        # without persisting anything.
        assert response.status_code != 422
