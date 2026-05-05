from unittest.mock import AsyncMock

import pytest

from api.auth import CurrentUser
from api.services import model_policy_service
from open_notebook.exceptions import InvalidInputError


def user(role: str = "user") -> CurrentUser:
    return CurrentUser(id=f"app_user:{role}", username=role, role=role)


@pytest.mark.asyncio
async def test_system_admin_can_use_any_explicit_model(monkeypatch):
    resolver = AsyncMock(return_value="model:system-chat")
    monkeypatch.setattr(
        model_policy_service,
        "resolve_default_model_id",
        resolver,
    )

    await model_policy_service.ensure_model_selection_allowed(
        actor=user("admin"),
        model_id="model:anything",
        default_type="chat",
        team_id=None,
    )

    resolver.assert_not_awaited()


@pytest.mark.asyncio
async def test_regular_user_can_only_use_effective_default(monkeypatch):
    monkeypatch.setattr(
        model_policy_service,
        "resolve_default_model_id",
        AsyncMock(return_value="model:team-chat"),
    )

    await model_policy_service.ensure_model_selection_allowed(
        actor=user(),
        model_id="model:team-chat",
        default_type="chat",
        team_id="team:research",
    )


@pytest.mark.asyncio
async def test_regular_user_cannot_override_to_non_default(monkeypatch):
    monkeypatch.setattr(
        model_policy_service,
        "resolve_default_model_id",
        AsyncMock(return_value="model:team-chat"),
    )

    with pytest.raises(InvalidInputError, match="Model selection is managed"):
        await model_policy_service.ensure_model_selection_allowed(
            actor=user(),
            model_id="model:other",
            default_type="chat",
            team_id="team:research",
        )


@pytest.mark.asyncio
async def test_optional_model_selection_skips_policy(monkeypatch):
    resolver = AsyncMock(return_value="model:team-chat")
    monkeypatch.setattr(model_policy_service, "resolve_default_model_id", resolver)

    await model_policy_service.ensure_model_selection_allowed(
        actor=user(),
        model_id=None,
        default_type="chat",
        team_id="team:research",
    )

    resolver.assert_not_awaited()
