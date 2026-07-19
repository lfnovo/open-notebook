"""Wiring tests for Anthropic-compatible credentials."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from open_notebook.domain.credential import Credential
from open_notebook.exceptions import ConfigurationError


def test_credential_config_preserves_anthropic_compatible_fields():
    credential = Credential(
        name="Kimi Coding",
        provider="anthropic_compatible",
        modalities=["language"],
        api_key=SecretStr("sk-test"),
        base_url="https://api.example.com/v1",
    )

    assert credential.to_esperanto_config() == {
        "api_key": "sk-test",
        "base_url": "https://api.example.com/v1",
    }


@pytest.mark.asyncio
async def test_update_rejects_clearing_compatible_base_url():
    from api.models import UpdateCredentialRequest
    from api.routers.credentials import update_credential

    credential = Credential(
        id="credential:test",
        name="Kimi Coding",
        provider="anthropic_compatible",
        modalities=["language"],
        api_key=SecretStr("sk-test"),
        base_url="https://api.example.com",
    )

    with (
        patch(
            "api.routers.credentials.Credential.get",
            AsyncMock(return_value=credential),
        ),
        patch("api.routers.credentials.require_encryption_key"),
        pytest.raises(HTTPException) as exc_info,
    ):
        await update_credential(
            "credential:test", UpdateCredentialRequest(base_url="")
        )

    assert exc_info.value.status_code == 400
    assert "require a base URL" in exc_info.value.detail


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("base_url", "models_url"),
    [
        ("https://api.example.com/v1", "https://api.example.com/v1/models"),
        ("https://api.example.com", "https://api.example.com/v1/models"),
        ("https://api.example.com/models", "https://api.example.com/v1/models"),
        ("https://api.example.com/v1/models", "https://api.example.com/v1/models"),
    ],
)
async def test_connection_handler_normalizes_url_and_uses_anthropic_headers(
    monkeypatch, base_url, models_url
):
    from open_notebook.ai import connection_tester
    from open_notebook.utils.url_validation import PinnedHttpTarget

    requests = []

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, headers=None, extensions=None):
            requests.append((url, headers, extensions))
            return httpx.Response(
                200,
                json={"data": [{"id": "kimi-for-coding"}]},
                request=httpx.Request("GET", url, headers=headers or {}),
            )

    async def fake_prepare_pinned(url, provider):
        return PinnedHttpTarget(url=url)

    monkeypatch.setattr(connection_tester.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        connection_tester, "prepare_pinned_http_target", fake_prepare_pinned
    )

    success, message = await connection_tester._test_anthropic_compatible_connection(
        base_url, "sk-test"
    )

    assert success is True
    assert "kimi-for-coding" in message
    assert requests == [
        (
            models_url,
            {"anthropic-version": "2023-06-01", "x-api-key": "sk-test"},
            {},
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("base_url", "expected_base_url"),
    [
        ("https://api.example.com/v1", "https://api.example.com/v1"),
        ("https://api.example.com", "https://api.example.com/v1"),
        ("https://api.example.com/models", "https://api.example.com/v1"),
        ("https://api.example.com/v1/models", "https://api.example.com/v1"),
    ],
)
async def test_model_manager_maps_normalized_url_to_anthropic_factory(
    base_url, expected_base_url
):
    from open_notebook.ai.models import Model, ModelManager

    credential = Credential(
        name="Compatible endpoint",
        provider="anthropic_compatible",
        api_key=SecretStr("sk-test"),
        base_url=base_url,
    )
    model = Model(
        id="model:test",
        name="compatible-model",
        provider="anthropic_compatible",
        type="language",
        credential="credential:test",
    )
    factory_model = SimpleNamespace()

    with (
        patch.object(Model, "get", AsyncMock(return_value=model)),
        patch.object(Model, "get_credential_obj", AsyncMock(return_value=credential)),
        patch("open_notebook.ai.models.validate_url", AsyncMock()) as validate_url_mock,
        patch(
            "open_notebook.ai.models.AIFactory.create_language",
            return_value=factory_model,
        ) as create_language,
    ):
        result = await ModelManager().get_model("model:test")

    assert result is factory_model
    assert validate_url_mock.await_count >= 1
    assert validate_url_mock.await_args_list[0].args == (base_url, "anthropic_compatible")
    create_language.assert_called_once_with(
        model_name="compatible-model",
        provider="anthropic",
        config={"api_key": "sk-test", "base_url": expected_base_url},
    )
    assert getattr(result, "_open_notebook_provider") == "anthropic_compatible"


@pytest.mark.asyncio
async def test_model_manager_uses_default_database_credential_when_unlinked(monkeypatch):
    from open_notebook.ai.models import Model, ModelManager

    credential = Credential(
        name="Default compatible endpoint",
        provider="anthropic_compatible",
        api_key=SecretStr("sk-database"),
        base_url="https://api.example.com/models",
    )
    model = Model(
        id="model:test",
        name="compatible-model",
        provider="anthropic_compatible",
        type="language",
    )
    factory_model = SimpleNamespace()
    monkeypatch.delenv("ANTHROPIC_COMPATIBLE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_COMPATIBLE_BASE_URL", raising=False)

    with (
        patch.object(Model, "get", AsyncMock(return_value=model)),
        patch.object(Credential, "get_by_provider", AsyncMock(return_value=[credential])),
        patch(
            "open_notebook.ai.models.AIFactory.create_language",
            return_value=factory_model,
        ) as create_language,
    ):
        result = await ModelManager().get_model("model:test")

    assert result is factory_model
    create_language.assert_called_once_with(
        model_name="compatible-model",
        provider="anthropic",
        config={"api_key": "sk-database", "base_url": "https://api.example.com/v1"},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [404, 405])
async def test_connection_handler_accepts_unsupported_model_listing(
    monkeypatch, status_code
):
    from open_notebook.ai import connection_tester
    from open_notebook.utils.url_validation import PinnedHttpTarget

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, headers=None, extensions=None):
            return httpx.Response(
                status_code,
                request=httpx.Request("GET", url, headers=headers or {}),
            )

    async def fake_prepare_pinned(url, provider):
        return PinnedHttpTarget(url=url)

    monkeypatch.setattr(connection_tester.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        connection_tester, "prepare_pinned_http_target", fake_prepare_pinned
    )

    success, message = await connection_tester._test_anthropic_compatible_connection(
        "https://api.example.com", "sk-test"
    )

    assert success is True
    assert f"status {status_code}" in message
    assert "add models manually" in message


@pytest.mark.asyncio
async def test_model_manager_rejects_missing_compatible_endpoint():
    from open_notebook.ai.models import Model, ModelManager

    credential = Credential(
        name="Incomplete endpoint",
        provider="anthropic_compatible",
        api_key=SecretStr("sk-test"),
    )
    model = Model(
        id="model:test",
        name="compatible-model",
        provider="anthropic_compatible",
        type="language",
        credential="credential:test",
    )

    with (
        patch.object(Model, "get", AsyncMock(return_value=model)),
        patch.object(Model, "get_credential_obj", AsyncMock(return_value=credential)),
        patch("open_notebook.ai.models.AIFactory.create_language") as create_language,
        pytest.raises(ConfigurationError, match="require a base URL and API key"),
    ):
        await ModelManager().get_model("model:test")

    create_language.assert_not_called()


def test_langchain_bridge_forwards_base_url():
    from open_notebook.ai.provision import _to_langchain

    esperanto_model = MagicMock()
    esperanto_model._open_notebook_provider = "anthropic_compatible"
    esperanto_model.base_url = "https://api.example.com/v1"
    esperanto_model.api_key = "sk-test"
    esperanto_model.max_tokens = 850
    esperanto_model.temperature = 0.5
    esperanto_model.top_p = 0.9
    esperanto_model.get_model_name.return_value = "compatible-model"

    with patch("langchain_anthropic.ChatAnthropic") as chat_anthropic:
        _to_langchain(esperanto_model)

    chat_anthropic.assert_called_once_with(
        model="compatible-model",
        max_tokens=850,
        api_key="sk-test",
        base_url="https://api.example.com",
        temperature=0.5,
    )
