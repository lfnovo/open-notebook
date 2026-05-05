from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from open_notebook.ai import model_resolution


def defaults(**overrides):
    data = {
        "default_chat_model": "model:system-chat",
        "default_embedding_model": "model:system-embed",
        "default_transformation_model": "model:system-transform",
        "default_tools_model": "model:system-tools",
        "large_context_model": "model:system-large",
        "default_text_to_speech_model": None,
        "default_speech_to_text_model": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.mark.asyncio
async def test_resolves_system_default_without_team(monkeypatch):
    monkeypatch.setattr(
        model_resolution.DefaultModels,
        "get_instance",
        AsyncMock(return_value=defaults()),
    )

    model_id = await model_resolution.resolve_default_model_id("chat")

    assert model_id == "model:system-chat"


@pytest.mark.asyncio
async def test_resolves_team_default_when_allowed_and_type_matches(monkeypatch):
    monkeypatch.setattr(
        model_resolution.DefaultModels,
        "get_instance",
        AsyncMock(return_value=defaults()),
    )
    monkeypatch.setattr(
        model_resolution.TeamRepository,
        "get_team",
        AsyncMock(
            return_value={
                "id": "team:research",
                "type": "workspace",
                "default_chat_model": "model:team-chat",
            }
        ),
    )
    monkeypatch.setattr(
        model_resolution.TeamAllowlistRepository,
        "list_team_models",
        AsyncMock(
            return_value=[
                {"model": {"id": "model:team-chat", "type": "language"}},
            ]
        ),
    )

    model_id = await model_resolution.resolve_default_model_id(
        "chat", team_id="team:research"
    )

    assert model_id == "model:team-chat"


@pytest.mark.asyncio
async def test_team_default_falls_back_to_system_when_unset(monkeypatch):
    monkeypatch.setattr(
        model_resolution.DefaultModels,
        "get_instance",
        AsyncMock(return_value=defaults()),
    )
    monkeypatch.setattr(
        model_resolution.TeamRepository,
        "get_team",
        AsyncMock(return_value={"id": "team:research", "type": "workspace"}),
    )
    monkeypatch.setattr(
        model_resolution.TeamAllowlistRepository,
        "list_team_models",
        AsyncMock(return_value=[]),
    )

    model_id = await model_resolution.resolve_default_model_id(
        "chat", team_id="team:research"
    )

    assert model_id == "model:system-chat"


@pytest.mark.asyncio
async def test_team_default_falls_back_when_not_in_allowlist(monkeypatch):
    monkeypatch.setattr(
        model_resolution.DefaultModels,
        "get_instance",
        AsyncMock(return_value=defaults()),
    )
    monkeypatch.setattr(
        model_resolution.TeamRepository,
        "get_team",
        AsyncMock(
            return_value={
                "id": "team:research",
                "type": "workspace",
                "default_chat_model": "model:removed-chat",
            }
        ),
    )
    monkeypatch.setattr(
        model_resolution.TeamAllowlistRepository,
        "list_team_models",
        AsyncMock(
            return_value=[
                {"model": {"id": "model:team-chat", "type": "language"}},
            ]
        ),
    )

    model_id = await model_resolution.resolve_default_model_id(
        "chat", team_id="team:research"
    )

    assert model_id == "model:system-chat"


@pytest.mark.asyncio
async def test_transformation_system_default_falls_back_to_system_chat(monkeypatch):
    monkeypatch.setattr(
        model_resolution.DefaultModels,
        "get_instance",
        AsyncMock(return_value=defaults(default_transformation_model=None)),
    )

    model_id = await model_resolution.resolve_default_model_id("transformation")

    assert model_id == "model:system-chat"
