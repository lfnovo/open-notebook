from unittest.mock import AsyncMock

import pytest

from api.auth import CurrentUser
from api.services import team_context_service
from open_notebook.exceptions import InvalidInputError


def user(role: str = "user") -> CurrentUser:
    return CurrentUser(id=f"app_user:{role}", username=role, role=role)


@pytest.mark.asyncio
async def test_resolves_single_non_public_team_grant(monkeypatch):
    monkeypatch.setattr(
        team_context_service.ShareRepository,
        "list_resource_grants",
        AsyncMock(
            return_value=[
                {
                    "target_type": "team",
                    "target_id": "team:research",
                    "permission": "read",
                },
                {
                    "target_type": "team",
                    "target_id": team_context_service.PUBLIC_TEAM_ID,
                    "permission": "read",
                },
            ]
        ),
    )

    team_id = await team_context_service.resolve_resource_team_context(
        resource_type="notebook",
        resource_id="notebook:abc",
    )

    assert team_id == "team:research"


@pytest.mark.asyncio
async def test_resource_team_context_ignores_public_grant(monkeypatch):
    monkeypatch.setattr(
        team_context_service.ShareRepository,
        "list_resource_grants",
        AsyncMock(
            return_value=[
                {
                    "target_type": "team",
                    "target_id": team_context_service.PUBLIC_TEAM_ID,
                    "permission": "read",
                }
            ]
        ),
    )

    team_id = await team_context_service.resolve_resource_team_context(
        resource_type="notebook",
        resource_id="notebook:abc",
    )

    assert team_id is None


@pytest.mark.asyncio
async def test_resource_team_context_returns_none_when_ambiguous(monkeypatch):
    monkeypatch.setattr(
        team_context_service.ShareRepository,
        "list_resource_grants",
        AsyncMock(
            return_value=[
                {"target_type": "team", "target_id": "team:a", "permission": "read"},
                {"target_type": "team", "target_id": "team:b", "permission": "read"},
            ]
        ),
    )

    team_id = await team_context_service.resolve_resource_team_context(
        resource_type="notebook",
        resource_id="notebook:abc",
    )

    assert team_id is None


@pytest.mark.asyncio
async def test_explicit_team_context_requires_membership(monkeypatch):
    monkeypatch.setattr(
        team_context_service.TeamRepository,
        "get_member",
        AsyncMock(return_value=None),
    )

    with pytest.raises(InvalidInputError, match="Team access required"):
        await team_context_service.resolve_explicit_team_context(
            actor=user(),
            team_id="team:research",
        )


@pytest.mark.asyncio
async def test_explicit_team_context_allows_active_member(monkeypatch):
    monkeypatch.setattr(
        team_context_service.TeamRepository,
        "get_member",
        AsyncMock(return_value={"status": "active", "role": "member"}),
    )

    team_id = await team_context_service.resolve_explicit_team_context(
        actor=user(),
        team_id="team:research",
    )

    assert team_id == "team:research"
