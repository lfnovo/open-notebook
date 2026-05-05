from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
from api.models import (
    TeamModelAllowlistUpdateRequest,
    TeamTransformationAllowlistUpdateRequest,
)
from api.services import team_service
from open_notebook.exceptions import InvalidInputError, NotFoundError


def regular_actor(role: str = "user") -> CurrentUser:
    return CurrentUser(id=f"app_user:{role}", username=role, role="user")


@pytest.mark.asyncio
@patch("api.services.team_service.TeamRepository.list_teams", new_callable=AsyncMock)
async def test_list_teams_marks_manageable_team_for_team_admin(mock_list_teams):
    mock_list_teams.return_value = [
        {
            "id": "team:research",
            "slug": "research",
            "name": "Research",
            "type": "workspace",
            "created": "2026-05-05T00:00:00Z",
            "updated": "2026-05-05T00:00:00Z",
            "member_count": 3,
            "share_count": 0,
            "current_user_role": "admin",
        }
    ]

    response = await team_service.list_teams_use_case(
        actor=regular_actor("admin"),
        q=None,
        limit=50,
        offset=0,
    )

    assert response.items[0].current_user_role == "admin"
    assert response.items[0].can_manage is True


@pytest.mark.asyncio
@patch("api.services.team_service.TeamRepository.list_teams", new_callable=AsyncMock)
async def test_list_teams_does_not_mark_member_as_manager(mock_list_teams):
    mock_list_teams.return_value = [
        {
            "id": "team:research",
            "slug": "research",
            "name": "Research",
            "type": "workspace",
            "created": "2026-05-05T00:00:00Z",
            "updated": "2026-05-05T00:00:00Z",
            "member_count": 3,
            "share_count": 0,
            "current_user_role": "member",
        }
    ]

    response = await team_service.list_teams_use_case(
        actor=regular_actor("member"),
        q=None,
        limit=50,
        offset=0,
    )

    assert response.items[0].current_user_role == "member"
    assert response.items[0].can_manage is False


@pytest.mark.asyncio
@patch("api.services.team_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.team_service.TeamAllowlistRepository.replace_team_models", new_callable=AsyncMock)
@patch("api.services.team_service.Model.get", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_member", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_team_owner_can_replace_model_allowlist(
    mock_get_team,
    mock_get_member,
    mock_get_model,
    mock_replace,
    mock_audit,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_get_member.return_value = {"role": "owner", "status": "active"}
    mock_get_model.side_effect = [
        SimpleNamespace(id="model:chat"),
        SimpleNamespace(id="model:embed"),
    ]
    mock_replace.return_value = [
        {
            "model": {
                "id": "model:chat",
                "name": "Chat",
                "provider": "openai",
                "type": "language",
                "credential": None,
                "created": "2026-05-05T00:00:00Z",
                "updated": "2026-05-05T00:00:00Z",
            }
        },
        {
            "model": {
                "id": "model:embed",
                "name": "Embed",
                "provider": "openai",
                "type": "embedding",
                "credential": None,
                "created": "2026-05-05T00:00:00Z",
                "updated": "2026-05-05T00:00:00Z",
            }
        },
    ]

    response = await team_service.replace_team_models_use_case(
        "team:research",
        TeamModelAllowlistUpdateRequest(model_ids=["model:chat", "model:embed"]),
        actor=regular_actor("owner"),
    )

    assert response.team_id == "team:research"
    assert response.model_ids == ["model:chat", "model:embed"]
    assert [model.id for model in response.models] == ["model:chat", "model:embed"]
    mock_replace.assert_awaited_once_with(
        "team:research",
        ["model:chat", "model:embed"],
        "app_user:owner",
    )


@pytest.mark.asyncio
@patch("api.services.team_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch(
    "api.services.team_service.TeamAllowlistRepository.replace_team_transformations",
    new_callable=AsyncMock,
)
@patch("api.services.team_service.Transformation.get", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_member", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_team_admin_can_replace_transformation_allowlist(
    mock_get_team,
    mock_get_member,
    mock_get_transformation,
    mock_replace,
    mock_audit,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_get_member.return_value = {"role": "admin", "status": "active"}
    mock_get_transformation.return_value = SimpleNamespace(id="transformation:summary")
    mock_replace.return_value = [
        {
            "transformation": {
                "id": "transformation:summary",
                "name": "summary",
                "title": "Summary",
                "description": "Summarize text",
                "prompt": "Summarize",
                "apply_default": False,
                "created": "2026-05-05T00:00:00Z",
                "updated": "2026-05-05T00:00:00Z",
            }
        }
    ]

    response = await team_service.replace_team_transformations_use_case(
        "team:research",
        TeamTransformationAllowlistUpdateRequest(
            transformation_ids=["transformation:summary"]
        ),
        actor=regular_actor("admin"),
    )

    assert response.team_id == "team:research"
    assert response.transformation_ids == ["transformation:summary"]
    assert [item.id for item in response.transformations] == ["transformation:summary"]
    mock_replace.assert_awaited_once_with(
        "team:research",
        ["transformation:summary"],
        "app_user:admin",
    )


@pytest.mark.asyncio
@patch("api.services.team_service.TeamRepository.get_member", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_team_member_cannot_replace_model_allowlist(
    mock_get_team,
    mock_get_member,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_get_member.return_value = {"role": "member", "status": "active"}

    with pytest.raises(PermissionError):
        await team_service.replace_team_models_use_case(
            "team:research",
            TeamModelAllowlistUpdateRequest(model_ids=["model:chat"]),
            actor=regular_actor("member"),
        )


@pytest.mark.asyncio
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_system_team_allowlist_cannot_be_managed(mock_get_team):
    mock_get_team.return_value = {"id": "team:public", "type": "system"}

    with pytest.raises(InvalidInputError):
        await team_service.replace_team_models_use_case(
            "team:public",
            TeamModelAllowlistUpdateRequest(model_ids=["model:chat"]),
            actor=CurrentUser(id="app_user:admin", username="admin", role="admin"),
        )


@pytest.mark.asyncio
@patch("api.services.team_service.Model.get", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_member", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_unknown_model_id_rejected(
    mock_get_team,
    mock_get_member,
    mock_get_model,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_get_member.return_value = {"role": "owner", "status": "active"}
    mock_get_model.return_value = None

    with pytest.raises(NotFoundError):
        await team_service.replace_team_models_use_case(
            "team:research",
            TeamModelAllowlistUpdateRequest(model_ids=["model:missing"]),
            actor=regular_actor("owner"),
        )
