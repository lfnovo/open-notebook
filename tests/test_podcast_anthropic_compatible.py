"""Podcast model resolution must retain Anthropic-compatible endpoints (#1347)."""

from unittest.mock import AsyncMock, patch

import pytest
from esperanto import AIFactory
from pydantic import SecretStr

from open_notebook.ai.models import Model
from open_notebook.domain.credential import Credential
from open_notebook.exceptions import ConfigurationError
from open_notebook.podcasts.models import EpisodeProfile, _resolve_model_config


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "resolver", ["resolve_outline_config", "resolve_transcript_config"]
)
@pytest.mark.parametrize("linked", [True, False], ids=["credential", "environment"])
async def test_compatible_podcast_model_reaches_its_endpoint(
    monkeypatch, resolver, linked
):
    base_url = "https://podcast.example.invalid/anthropic"
    api_key = "test-podcast-compatible-key"
    credential = Credential(
        name="Compatible podcast endpoint",
        provider="anthropic_compatible",
        api_key=SecretStr(api_key),
        base_url=base_url,
    )
    model = Model(
        id="model:podcast",
        name="compatible-podcast-model",
        provider="anthropic_compatible",
        type="language",
        credential="credential:podcast" if linked else None,
    )
    profile = EpisodeProfile(
        name="Compatible podcast",
        default_briefing="Discuss the source",
        outline_llm="model:podcast",
        transcript_llm="model:podcast",
        max_tokens=2048,
    )
    monkeypatch.setenv(
        "ANTHROPIC_COMPATIBLE_API_KEY", "other-env-key" if linked else api_key
    )
    monkeypatch.setenv(
        "ANTHROPIC_COMPATIBLE_BASE_URL",
        "https://other.example.invalid" if linked else base_url,
    )
    with (
        patch.object(Model, "get", AsyncMock(return_value=model)),
        patch.object(Model, "get_credential_obj", AsyncMock(return_value=credential)),
        patch("open_notebook.ai.key_provider.provision_provider_keys", AsyncMock()),
        patch("open_notebook.ai.models.validate_url", AsyncMock()),
    ):
        provider, name, config = await getattr(profile, resolver)()

    # Exercise the real factory boundary used by podcast-creator. Construction
    # performs no model request; the endpoint must not become api.anthropic.com.
    language_model = AIFactory.create_language(provider, name, config=config)
    assert provider == "anthropic"
    assert language_model.base_url == base_url + "/v1"
    assert config == {
        "api_key": api_key,
        "base_url": base_url + "/v1",
        "max_tokens": 2048,
    }
    assert model.provider == "anthropic_compatible"


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["api_key", "base_url"])
async def test_incomplete_compatible_config_cannot_fall_back_to_anthropic(
    monkeypatch, missing
):
    values = {
        "api_key": "test-compatible-key",
        "base_url": "https://podcast.example.invalid",
    }
    values.pop(missing)
    credential = Credential(
        name="Incomplete", provider="anthropic_compatible", **values
    )
    model = Model(
        id="model:incomplete",
        name="compatible-model",
        provider="anthropic_compatible",
        type="language",
        credential="credential:incomplete",
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "unrelated-official-key")
    with (
        patch.object(Model, "get", AsyncMock(return_value=model)),
        patch.object(Model, "get_credential_obj", AsyncMock(return_value=credential)),
        patch("open_notebook.ai.key_provider.provision_provider_keys", AsyncMock()),
        patch("open_notebook.ai.models.validate_url", AsyncMock()),
        pytest.raises(ConfigurationError, match="require a base URL and API key"),
    ):
        await _resolve_model_config("model:incomplete")


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["openai", "openai_compatible", "anthropic"])
async def test_other_podcast_providers_keep_existing_config(provider):
    credential = Credential(
        name="Existing",
        provider=provider,
        api_key=SecretStr("test-existing-key"),
        base_url="https://existing.example.invalid/v1",
    )
    model = Model(
        id="model:existing",
        name="existing-model",
        provider=provider,
        type="language",
        credential="credential:existing",
    )
    with (
        patch.object(Model, "get", AsyncMock(return_value=model)),
        patch.object(Model, "get_credential_obj", AsyncMock(return_value=credential)),
    ):
        assert await _resolve_model_config("model:existing") == (
            provider,
            "existing-model",
            credential.to_esperanto_config(),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["chat", "podcast"])
@pytest.mark.parametrize("invalid", ["missing_key", "missing_url", "rejected_url"])
async def test_both_paths_reject_invalid_compatible_environment(
    monkeypatch, path, invalid
):
    from open_notebook.ai.models import ModelManager

    monkeypatch.setenv(
        "ANTHROPIC_COMPATIBLE_API_KEY", "" if invalid == "missing_key" else "test-key"
    )
    monkeypatch.setenv(
        "ANTHROPIC_COMPATIBLE_BASE_URL",
        "" if invalid == "missing_url" else "https://rejected.example.invalid",
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "unrelated-official-key")
    model = Model(
        id="model:environment",
        name="compatible-model",
        provider="anthropic_compatible",
        type="language",
    )
    validator = AsyncMock(
        side_effect=ValueError("URL rejected") if invalid == "rejected_url" else None
    )
    with (
        patch.object(Model, "get", AsyncMock(return_value=model)),
        patch("open_notebook.ai.key_provider.provision_provider_keys", AsyncMock()),
        patch("open_notebook.ai.models.validate_url", validator),
        patch("open_notebook.ai.models.AIFactory.create_language") as factory,
    ):
        with pytest.raises(ConfigurationError):
            if path == "chat":
                await ModelManager().get_model("model:environment", max_tokens=2048)
            else:
                await _resolve_model_config("model:environment", max_tokens=2048)
    factory.assert_not_called()
    if invalid == "rejected_url":
        validator.assert_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["api_key", "base_url"])
@pytest.mark.parametrize("via_override", [False, True], ids=["config", "override"])
async def test_compatible_config_rejects_explicit_none(field, via_override):
    from open_notebook.ai.models import resolve_anthropic_compatible_config

    config: dict[str, str | None] = {
        "api_key": "test-compatible-key",
        "base_url": "https://podcast.example.invalid",
    }
    overrides: dict[str, str | None] = {}
    if via_override:
        overrides[field] = None
    else:
        config[field] = None

    with (
        patch("open_notebook.ai.models.validate_url", AsyncMock()) as validator,
        pytest.raises(ConfigurationError, match="require a base URL and API key"),
    ):
        await resolve_anthropic_compatible_config(config, **overrides)
    validator.assert_not_awaited()
