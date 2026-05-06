from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from api.auth import CurrentUser
from api.models import (
    TeamCreateRequest,
    TeamModelAllowlistUpdateRequest,
    TeamModelDefaultsUpdateRequest,
    TeamTransformationAllowlistUpdateRequest,
)
from api.services import team_service
from open_notebook.exceptions import InvalidInputError, NotFoundError


def regular_actor(role: str = "user") -> CurrentUser:
    return CurrentUser(id=f"app_user:{role}", username=role, role="user")


def system_admin() -> CurrentUser:
    return CurrentUser(id="app_user:admin", username="admin", role="admin")


def test_team_create_request_requires_owner_id():
    with pytest.raises(ValidationError):
        TeamCreateRequest(name="Research")


@pytest.mark.asyncio
@patch("api.services.team_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.team_service.ensure_team_workspace_for_team", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.create_member", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.create_team", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team_by_slug", new_callable=AsyncMock)
@patch("api.services.team_service.UserRepository.get_user", new_callable=AsyncMock)
async def test_create_team_assigns_requested_owner(
    mock_get_user,
    mock_get_team_by_slug,
    mock_create_team,
    mock_create_member,
    mock_ensure_workspace,
    mock_audit,
):
    mock_get_user.return_value = {"id": "app_user:owner", "status": "active"}
    mock_get_team_by_slug.return_value = None
    mock_create_team.return_value = {
        "id": "team:research",
        "slug": "research",
        "name": "Research",
        "type": "workspace",
        "created_by": "app_user:admin",
        "created": "2026-05-05T00:00:00Z",
        "updated": "2026-05-05T00:00:00Z",
    }

    response = await team_service.create_team_use_case(
        TeamCreateRequest(name="Research", owner_id="app_user:owner"),
        actor=system_admin(),
    )

    assert response.current_user_role is None
    assert response.can_manage is True
    mock_create_member.assert_awaited_once_with(
        team_id="team:research",
        user_id="app_user:owner",
        role="owner",
        status="active",
    )
    mock_ensure_workspace.assert_awaited_once_with(
        team_id="team:research",
        name="Research",
        created_by="app_user:admin",
    )
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
@patch("api.services.team_service.UserRepository.get_user", new_callable=AsyncMock)
async def test_create_team_rejects_disabled_owner(mock_get_user):
    mock_get_user.return_value = {"id": "app_user:owner", "status": "disabled"}

    with pytest.raises(InvalidInputError):
        await team_service.create_team_use_case(
            TeamCreateRequest(name="Research", owner_id="app_user:owner"),
            actor=system_admin(),
        )


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
@patch("api.services.team_service.UserRepository.count_users", new_callable=AsyncMock)
@patch("api.services.team_service.UserRepository.list_users", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_member", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_team_admin_can_list_active_users_for_member_assignment(
    mock_get_team,
    mock_get_member,
    mock_list_users,
    mock_count_users,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_get_member.return_value = {"role": "admin", "status": "active"}
    mock_list_users.return_value = [
        {
            "id": "app_user:writer",
            "username": "writer",
            "display_name": "Writer",
            "email": "writer@example.com",
            "role": "user",
            "status": "active",
        }
    ]
    mock_count_users.return_value = 1

    response = await team_service.list_team_assignable_users_use_case(
        "team:research",
        actor=regular_actor("admin"),
        q="wri",
        limit=20,
        offset=0,
    )

    assert response.total == 1
    assert response.items[0].id == "app_user:writer"
    assert response.items[0].username == "writer"
    mock_list_users.assert_awaited_once_with(
        q="wri",
        role=None,
        status="active",
        limit=20,
        offset=0,
    )


@pytest.mark.asyncio
@patch("api.services.team_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.clear_invalid_model_defaults", new_callable=AsyncMock)
@patch("api.services.team_service.TeamAllowlistRepository.replace_team_models", new_callable=AsyncMock)
@patch("api.services.team_service.Model.get", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_system_admin_can_replace_model_allowlist(
    mock_get_team,
    mock_get_model,
    mock_replace,
    mock_clear_invalid_defaults,
    mock_audit,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
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
        actor=system_admin(),
    )

    assert response.team_id == "team:research"
    assert response.model_ids == ["model:chat", "model:embed"]
    assert [model.id for model in response.models] == ["model:chat", "model:embed"]
    mock_replace.assert_awaited_once_with(
        "team:research",
        ["model:chat", "model:embed"],
        "app_user:admin",
    )
    mock_clear_invalid_defaults.assert_awaited_once_with(
        "team:research",
        ["model:chat", "model:embed"],
    )


@pytest.mark.asyncio
@patch("api.services.team_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch(
    "api.services.team_service.TeamAllowlistRepository.replace_team_transformations",
    new_callable=AsyncMock,
)
@patch("api.services.team_service.Transformation.get", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_system_admin_can_replace_transformation_allowlist(
    mock_get_team,
    mock_get_transformation,
    mock_replace,
    mock_audit,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
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
        actor=system_admin(),
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
async def test_team_owner_cannot_replace_model_allowlist(mock_get_team):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}

    with pytest.raises(PermissionError, match="Admin privileges required"):
        await team_service.replace_team_models_use_case(
            "team:research",
            TeamModelAllowlistUpdateRequest(model_ids=["model:chat"]),
            actor=regular_actor("owner"),
        )


@pytest.mark.asyncio
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_team_admin_cannot_replace_transformation_allowlist(mock_get_team):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}

    with pytest.raises(PermissionError, match="Admin privileges required"):
        await team_service.replace_team_transformations_use_case(
            "team:research",
            TeamTransformationAllowlistUpdateRequest(
                transformation_ids=["transformation:summary"]
            ),
            actor=regular_actor("admin"),
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
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_unknown_model_id_rejected(
    mock_get_team,
    mock_get_model,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_get_model.return_value = None

    with pytest.raises(NotFoundError):
        await team_service.replace_team_models_use_case(
            "team:research",
            TeamModelAllowlistUpdateRequest(model_ids=["model:missing"]),
            actor=system_admin(),
        )


@pytest.mark.asyncio
@patch("api.services.team_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.update_model_defaults", new_callable=AsyncMock)
@patch("api.services.team_service.TeamAllowlistRepository.list_team_models", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_member", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_team_owner_can_update_default_models_from_team_allowlist(
    mock_get_team,
    mock_get_member,
    mock_list_team_models,
    mock_update_defaults,
    mock_audit,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_get_member.return_value = {"role": "owner", "status": "active"}
    mock_list_team_models.return_value = [
        {"model": {"id": "model:chat", "type": "language"}},
        {"model": {"id": "model:embed", "type": "embedding"}},
        {"model": {"id": "model:tools", "type": "language"}},
    ]
    mock_update_defaults.return_value = {
        "default_chat_model": "model:chat",
        "default_embedding_model": "model:embed",
        "default_transformation_model": "model:chat",
        "default_tools_model": "model:tools",
        "large_context_model": None,
    }

    response = await team_service.update_team_model_defaults_use_case(
        "team:research",
        TeamModelDefaultsUpdateRequest(
            default_chat_model="model:chat",
            default_embedding_model="model:embed",
            default_transformation_model="model:chat",
            default_tools_model="model:tools",
            large_context_model=None,
        ),
        actor=regular_actor("owner"),
    )

    assert response.team_id == "team:research"
    assert response.default_chat_model == "model:chat"
    assert response.default_embedding_model == "model:embed"
    assert response.default_tools_model == "model:tools"
    mock_update_defaults.assert_awaited_once_with(
        "team:research",
        {
            "default_chat_model": "model:chat",
            "default_embedding_model": "model:embed",
            "default_transformation_model": "model:chat",
            "default_tools_model": "model:tools",
            "large_context_model": None,
        },
    )
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
@patch("api.services.team_service.TeamAllowlistRepository.list_team_models", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_member", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_team_default_model_must_be_allowed_for_team(
    mock_get_team,
    mock_get_member,
    mock_list_team_models,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_get_member.return_value = {"role": "owner", "status": "active"}
    mock_list_team_models.return_value = [
        {"model": {"id": "model:chat", "type": "language"}},
    ]

    with pytest.raises(InvalidInputError, match="allowed for this team"):
        await team_service.update_team_model_defaults_use_case(
            "team:research",
            TeamModelDefaultsUpdateRequest(default_embedding_model="model:embed"),
            actor=regular_actor("owner"),
        )


@pytest.mark.asyncio
@patch("api.services.team_service.TeamAllowlistRepository.list_team_models", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_member", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_team_default_model_must_match_slot_type(
    mock_get_team,
    mock_get_member,
    mock_list_team_models,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_get_member.return_value = {"role": "owner", "status": "active"}
    mock_list_team_models.return_value = [
        {"model": {"id": "model:embed", "type": "embedding"}},
    ]

    with pytest.raises(InvalidInputError, match="language model"):
        await team_service.update_team_model_defaults_use_case(
            "team:research",
            TeamModelDefaultsUpdateRequest(default_chat_model="model:embed"),
            actor=regular_actor("owner"),
        )


@pytest.mark.asyncio
@patch("api.services.team_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.update_model_defaults", new_callable=AsyncMock)
@patch("api.services.team_service.TeamAllowlistRepository.list_team_models", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_member", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_team_default_model_partial_update_preserves_unspecified_slots(
    mock_get_team,
    mock_get_member,
    mock_list_team_models,
    mock_update_defaults,
    mock_audit,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_get_member.return_value = {"role": "owner", "status": "active"}
    mock_list_team_models.return_value = [
        {"model": {"id": "model:chat", "type": "language"}},
    ]
    mock_update_defaults.return_value = {
        "default_chat_model": "model:chat",
        "default_embedding_model": "model:embed",
    }

    await team_service.update_team_model_defaults_use_case(
        "team:research",
        TeamModelDefaultsUpdateRequest(default_chat_model="model:chat"),
        actor=regular_actor("owner"),
    )

    mock_update_defaults.assert_awaited_once_with(
        "team:research",
        {"default_chat_model": "model:chat"},
    )


@pytest.mark.asyncio
@patch("api.services.team_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.delete_team", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.dependency_counts", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_system_admin_can_delete_team_with_members_when_no_shares(
    mock_get_team,
    mock_dependency_counts,
    mock_delete_team,
    mock_audit,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_dependency_counts.return_value = {"active_members": 2, "share_grants": 0}
    actor = CurrentUser(id="app_user:admin", username="admin", role="admin")

    response = await team_service.delete_team_use_case("team:research", actor=actor)

    assert response.success is True
    mock_delete_team.assert_awaited_once_with("team:research")
    mock_audit.assert_awaited_once()


@pytest.mark.asyncio
@patch("api.services.team_service.AuditLogRepository.create", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.delete_team", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.dependency_counts", new_callable=AsyncMock)
@patch("api.services.team_service.TeamRepository.get_team", new_callable=AsyncMock)
async def test_system_admin_can_delete_team_with_share_grants(
    mock_get_team,
    mock_dependency_counts,
    mock_delete_team,
    mock_audit,
):
    mock_get_team.return_value = {"id": "team:research", "type": "workspace"}
    mock_dependency_counts.return_value = {"active_members": 1, "share_grants": 1}
    actor = system_admin()

    response = await team_service.delete_team_use_case("team:research", actor=actor)

    assert response.success is True
    mock_delete_team.assert_awaited_once_with("team:research")
    mock_audit.assert_awaited_once()
