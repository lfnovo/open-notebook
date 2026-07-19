"""
Tests for open_notebook.ai.model_discovery.

Covers the table-driven OpenAI-compatible discovery path and the
Anthropic model-listing API discovery (with static fallback).
All HTTP calls are mocked — no real provider APIs are hit.
"""

import httpx
import pytest

from open_notebook.ai import model_discovery
from open_notebook.ai.model_discovery import (
    ANTHROPIC_FALLBACK_MODELS,
    OPENAI_COMPAT_PROVIDERS,
    OPENROUTER_AUDIO_MODELS,
    PROVIDER_DISCOVERY_FUNCTIONS,
    discover_anthropic_models,
    discover_openai_compatible_provider,
    discover_openrouter_models,
)


def make_fake_client(handler):
    """Build a fake httpx.AsyncClient class whose .get() delegates to handler."""

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, headers=None, params=None, timeout=None):
            return handler(url=url, headers=headers, params=params, timeout=timeout)

    return FakeAsyncClient


def json_response(url, payload, status_code=200):
    return httpx.Response(
        status_code, json=payload, request=httpx.Request("GET", url)
    )


class TestOpenAICompatTable:
    """The provider table must keep covering every collapsed provider."""

    def test_table_covers_all_openai_compatible_providers(self):
        assert set(OPENAI_COMPAT_PROVIDERS) == {
            "openai",
            "groq",
            "mistral",
            "deepseek",
            "xai",
            "openrouter",
            "dashscope",
            "minimax",
            "novita",
            "ppq",
        }

    def test_provider_discovery_functions_keys_unchanged(self):
        assert set(PROVIDER_DISCOVERY_FUNCTIONS) == {
            "openai",
            "anthropic",
            "google",
            "ollama",
            "omlx",
            "groq",
            "mistral",
            "deepseek",
            "xai",
            "openrouter",
            "voyage",
            "elevenlabs",
            "deepgram",
            "openai_compatible",
            "anthropic_compatible",
            "dashscope",
            "minimax",
            "novita",
            "ppq",
            "cohere",
            "azure",
            "vertex",
        }
        # Azure/Vertex intentionally have no env-based discovery
        assert PROVIDER_DISCOVERY_FUNCTIONS["azure"] is None
        assert PROVIDER_DISCOVERY_FUNCTIONS["vertex"] is None

    def test_module_level_names_preserved(self):
        for provider in OPENAI_COMPAT_PROVIDERS:
            func = getattr(model_discovery, f"discover_{provider}_models")
            assert callable(func)
            assert PROVIDER_DISCOVERY_FUNCTIONS[provider] is func


class TestGenericOpenAICompatDiscovery:
    @pytest.mark.asyncio
    async def test_discovery_uses_spec_url_and_bearer_key(self, monkeypatch):
        requests = []

        def handler(url, headers, params, timeout):
            requests.append({"url": url, "headers": headers, "timeout": timeout})
            return json_response(
                url, {"data": [{"id": "whisper-large-v3"}, {"id": "llama-3.3-70b"}]}
            )

        monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
        monkeypatch.setattr(
            model_discovery.httpx, "AsyncClient", make_fake_client(handler)
        )

        models = await discover_openai_compatible_provider("groq")

        assert requests == [
            {
                "url": "https://api.groq.com/openai/v1/models",
                "headers": {"Authorization": "Bearer gsk-test"},
                "timeout": 30.0,
            }
        ]
        assert [(m.name, m.provider, m.model_type) for m in models] == [
            ("whisper-large-v3", "groq", "speech_to_text"),
            ("llama-3.3-70b", "groq", "language"),
        ]

    @pytest.mark.asyncio
    async def test_missing_env_key_returns_empty(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        assert await discover_openai_compatible_provider("deepseek") == []

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self, monkeypatch):
        def handler(url, headers, params, timeout):
            return json_response(url, {"error": "nope"}, status_code=500)

        monkeypatch.setenv("XAI_API_KEY", "xai-test")
        monkeypatch.setattr(
            model_discovery.httpx, "AsyncClient", make_fake_client(handler)
        )

        assert await discover_openai_compatible_provider("xai") == []

    @pytest.mark.asyncio
    async def test_mistral_capabilities_quirk(self, monkeypatch):
        def handler(url, headers, params, timeout):
            return json_response(
                url,
                {
                    "data": [
                        # capabilities flag wins over name-based classification
                        {"id": "magistral-medium", "capabilities": {"completion_chat": True}},
                        # no chat capability -> falls back to name patterns
                        {"id": "mistral-embed", "capabilities": {"completion_chat": False}},
                    ]
                },
            )

        monkeypatch.setenv("MISTRAL_API_KEY", "mk-test")
        monkeypatch.setattr(
            model_discovery.httpx, "AsyncClient", make_fake_client(handler)
        )

        models = await discover_openai_compatible_provider("mistral")
        assert [(m.name, m.model_type) for m in models] == [
            ("magistral-medium", "language"),
            ("mistral-embed", "embedding"),
        ]

    @pytest.mark.asyncio
    async def test_openrouter_quirk_language_and_description(self, monkeypatch):
        def handler(url, headers, params, timeout):
            return json_response(
                url,
                {"data": [{"id": "acme/embedding-x", "name": "Acme Embedding X"}]},
            )

        monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
        monkeypatch.setattr(
            model_discovery.httpx, "AsyncClient", make_fake_client(handler)
        )

        models = await discover_openai_compatible_provider("openrouter")
        assert len(models) == 1
        # OpenRouter models are always registered as language models
        assert models[0].model_type == "language"
        assert models[0].description == "Acme Embedding X"


class TestOpenRouterDiscovery:
    """discover_openrouter_models combines API discovery with an audio seed."""

    @pytest.mark.asyncio
    async def test_missing_key_returns_empty(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        assert await discover_openrouter_models() == []

    @pytest.mark.asyncio
    async def test_seeds_audio_models_alongside_api_models(self, monkeypatch):
        def handler(url, headers, params, timeout):
            return json_response(
                url,
                {"data": [{"id": "openai/gpt-4o", "name": "GPT-4o"}]},
            )

        monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
        monkeypatch.setattr(
            model_discovery.httpx, "AsyncClient", make_fake_client(handler)
        )

        models = await discover_openrouter_models()
        by_type = {(m.name, m.model_type) for m in models}

        # Language model from the /models endpoint is preserved.
        assert ("openai/gpt-4o", "language") in by_type
        # The esperanto default audio models are seeded.
        for model_type, names in OPENROUTER_AUDIO_MODELS.items():
            for name in names:
                assert (name, model_type) in by_type
        assert all(m.provider == "openrouter" for m in models)


class TestAnthropicDiscovery:
    @pytest.mark.asyncio
    async def test_missing_key_returns_empty(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert await discover_anthropic_models() == []

    @pytest.mark.asyncio
    async def test_discovery_paginates_and_sends_anthropic_headers(self, monkeypatch):
        requests = []

        def handler(url, headers, params, timeout):
            requests.append({"url": url, "headers": headers, "params": dict(params)})
            if "after_id" not in params:
                return json_response(
                    url,
                    {
                        "data": [{"id": "claude-opus-4-8"}],
                        "has_more": True,
                        "last_id": "claude-opus-4-8",
                    },
                )
            return json_response(
                url,
                {
                    "data": [{"id": "claude-haiku-4-5"}],
                    "has_more": False,
                    "last_id": "claude-haiku-4-5",
                },
            )

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setattr(
            model_discovery.httpx, "AsyncClient", make_fake_client(handler)
        )

        models = await discover_anthropic_models()

        assert len(requests) == 2
        assert all(
            r["url"] == "https://api.anthropic.com/v1/models" for r in requests
        )
        assert requests[0]["headers"] == {
            "x-api-key": "sk-ant-test",
            "anthropic-version": "2023-06-01",
        }
        assert requests[1]["params"]["after_id"] == "claude-opus-4-8"

        assert [(m.name, m.provider, m.model_type) for m in models] == [
            ("claude-opus-4-8", "anthropic", "language"),
            ("claude-haiku-4-5", "anthropic", "language"),
        ]

    @pytest.mark.asyncio
    async def test_api_failure_falls_back_to_static_list(self, monkeypatch):
        def handler(url, headers, params, timeout):
            return json_response(url, {"error": "boom"}, status_code=500)

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setattr(
            model_discovery.httpx, "AsyncClient", make_fake_client(handler)
        )

        models = await discover_anthropic_models()

        assert [m.name for m in models] == list(ANTHROPIC_FALLBACK_MODELS)
        assert all(m.provider == "anthropic" for m in models)
        assert all(m.model_type == "language" for m in models)


class TestCredentialServiceAnthropicDiscovery:
    """discover_with_config must use the same live-API-with-fallback path."""

    @pytest.mark.asyncio
    async def test_discover_with_config_uses_anthropic_api(self, monkeypatch):
        from api import credentials_service

        def handler(url, headers, params, timeout):
            assert url == "https://api.anthropic.com/v1/models"
            return json_response(
                url, {"data": [{"id": "claude-sonnet-4-6"}], "has_more": False}
            )

        monkeypatch.setattr(
            model_discovery.httpx, "AsyncClient", make_fake_client(handler)
        )

        models = await credentials_service.discover_with_config(
            "anthropic", {"api_key": "sk-ant-test"}
        )
        assert models == [{"name": "claude-sonnet-4-6", "provider": "anthropic"}]

    @pytest.mark.asyncio
    async def test_discover_with_config_falls_back_on_error(self, monkeypatch):
        from api import credentials_service

        def handler(url, headers, params, timeout):
            return json_response(url, {"error": "boom"}, status_code=503)

        monkeypatch.setattr(
            model_discovery.httpx, "AsyncClient", make_fake_client(handler)
        )

        models = await credentials_service.discover_with_config(
            "anthropic", {"api_key": "sk-ant-test"}
        )
        assert [m["name"] for m in models] == list(ANTHROPIC_FALLBACK_MODELS)

    @pytest.mark.asyncio
    async def test_discover_with_config_requires_key(self):
        from api import credentials_service

        models = await credentials_service.discover_with_config("anthropic", {})
        assert models == []


class TestNewEsperantoProviders:
    """Issue #1170: Cohere, Deepgram STT, PPQ and Novita wiring."""

    def test_ppq_and_novita_use_openai_compat_discovery(self):
        assert (
            OPENAI_COMPAT_PROVIDERS["ppq"].url == "https://api.ppq.ai/v1/models"
        )
        assert (
            OPENAI_COMPAT_PROVIDERS["novita"].url
            == "https://api.novita.ai/openai/models"
        )

    def test_ppq_classification_by_substring(self):
        from open_notebook.ai.model_discovery import classify_model_type

        assert classify_model_type("openai/text-embedding-3-small", "ppq") == "embedding"
        assert classify_model_type("nova-3", "ppq") == "speech_to_text"
        assert classify_model_type("deepgram_aura_2", "ppq") == "text_to_speech"
        assert classify_model_type("auto", "ppq") == "language"

    @pytest.mark.asyncio
    async def test_deepgram_discovery_includes_stt(self, monkeypatch):
        from open_notebook.ai.model_discovery import discover_deepgram_models

        monkeypatch.setenv("DEEPGRAM_API_KEY", "dg-test")
        models = await discover_deepgram_models()
        by_type = {m.model_type for m in models}
        assert "text_to_speech" in by_type
        assert "speech_to_text" in by_type
        stt_names = {m.name for m in models if m.model_type == "speech_to_text"}
        assert "nova-3" in stt_names

    @pytest.mark.asyncio
    async def test_cohere_discovery_missing_key_returns_empty(self, monkeypatch):
        from open_notebook.ai.model_discovery import discover_cohere_models

        monkeypatch.delenv("COHERE_API_KEY", raising=False)
        assert await discover_cohere_models() == []

    @pytest.mark.asyncio
    async def test_cohere_discovery_filters_to_language_and_embedding(
        self, monkeypatch
    ):
        from types import SimpleNamespace

        from open_notebook.ai import model_discovery as md

        monkeypatch.setenv("COHERE_API_KEY", "co-test")

        fake_models = [
            SimpleNamespace(id="command-a-03-2025", type="language"),
            SimpleNamespace(id="embed-v4.0", type="embedding"),
            SimpleNamespace(id="rerank-v3.5", type="reranker"),
            SimpleNamespace(id="mystery", type=None),
        ]

        class FakeFactory:
            @staticmethod
            def get_provider_models(provider, api_key=None):
                assert provider == "cohere"
                return fake_models

        import esperanto

        monkeypatch.setattr(esperanto, "AIFactory", FakeFactory)

        models = await md.discover_cohere_models()
        got = {(m.name, m.model_type) for m in models}
        assert got == {
            ("command-a-03-2025", "language"),
            ("embed-v4.0", "embedding"),
        }
