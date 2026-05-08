from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
from api.models import SourceCreate, WorkspacePermissionPolicy
from api.services.source_service import (
    create_source_and_queue_processing,
    resolve_source_workspace_id,
    retry_source_processing_use_case,
)
from open_notebook.domain.notebook import Asset, Source


@pytest.mark.asyncio
async def test_retry_marks_submitted_command_failed_when_source_update_fails():
    source = Source(
        id="source:retry",
        title="Retry me",
        asset=Asset(url="https://example.com/article"),
        owner_id="user:owner",
        visibility="private",
    )

    async def fail_save(self):
        raise RuntimeError("database update failed")

    with patch.object(Source, "get", new_callable=AsyncMock, return_value=source):
        with patch.object(Source, "save", autospec=True, side_effect=fail_save):
            with patch(
                "api.services.source_service.SourceRepository.referenced_notebook_ids",
                new_callable=AsyncMock,
                return_value=["notebook:one"],
            ):
                with patch(
                    "api.services.source_service.submit_process_source_command",
                    new_callable=AsyncMock,
                    return_value="command:retry",
                ):
                    with patch(
                        "api.services.source_service.resolve_resource_team_context",
                        new_callable=AsyncMock,
                        return_value=None,
                    ):
                        with patch(
                            "api.services.source_service.mark_command_failed",
                            new_callable=AsyncMock,
                        ) as mark_failed:
                            with pytest.raises(
                                RuntimeError, match="database update failed"
                            ):
                                await retry_source_processing_use_case(
                                    "source:retry",
                                    user_id="user:owner",
                                )

    mark_failed.assert_awaited_once()
    args = mark_failed.await_args.args
    assert args[0] == "command:retry"
    assert "Failed to attach command to source source:retry" in args[1]


@pytest.mark.asyncio
@patch("api.services.workspace_service.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
async def test_resolve_source_workspace_id_rejects_requested_workspace_without_membership(
    mock_current_role,
):
    mock_current_role.return_value = {
        "type": "team",
        "current_user_role": None,
    }

    with pytest.raises(PermissionError, match="Workspace access denied"):
        await resolve_source_workspace_id(
            SourceCreate(type="text", content="hello", workspace_id="workspace:observed"),
            user_id="app_user:admin",
        )


def actor() -> CurrentUser:
    return CurrentUser(id="app_user:member", username="member", role="user")


@pytest.mark.asyncio
@patch("api.services.source_service.resolve_source_workspace_id", new_callable=AsyncMock)
async def test_system_admin_cannot_create_sources(mock_workspace_id):
    with pytest.raises(PermissionError, match="System admins cannot create workspace resources"):
        await create_source_and_queue_processing(
            SourceCreate(type="text", content="Admin source"),
            user_id="app_user:admin",
            actor=CurrentUser(id="app_user:admin", username="admin", role="admin"),
        )

    mock_workspace_id.assert_not_awaited()


@pytest.mark.asyncio
@patch("api.services.source_service.ShareRepository.create_grant", new_callable=AsyncMock)
@patch("api.services.source_service.WorkspacePolicyRepository.get_effective_policy", new_callable=AsyncMock)
@patch("api.services.workspace_service.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
@patch("api.services.source_service.submit_process_source_command", new_callable=AsyncMock)
@patch("api.services.source_service.resolve_default_model_id", new_callable=AsyncMock)
async def test_team_workspace_source_create_forces_team_visibility_and_grant(
    mock_resolve_model,
    mock_submit,
    mock_role,
    mock_policy,
    mock_create_grant,
):
    mock_resolve_model.return_value = "model:tools"
    mock_submit.return_value = "command:source"
    mock_role.return_value = {
        "type": "team",
        "team_id": "team:research",
        "current_user_role": "member",
    }
    mock_policy.return_value = WorkspacePermissionPolicy(member_can_create_source=True)
    saved_sources = []

    async def capture_save(self_source):
        saved_sources.append(self_source)
        self_source.id = "source:team"

    with patch.object(Source, "save", autospec=True, side_effect=capture_save):
        response = await create_source_and_queue_processing(
            SourceCreate(
                type="text",
                content="Team source",
                workspace_id="workspace:team",
            ),
            user_id="app_user:member",
            actor=actor(),
        )

    assert response.visibility == "team"
    assert saved_sources[0].visibility == "team"
    mock_create_grant.assert_awaited_with(
        resource_type="source",
        resource_id="source:team",
        target_type="team",
        target_id="team:research",
        permission="read",
        created_by="app_user:member",
    )


@pytest.mark.asyncio
@patch("api.services.source_service.WorkspacePolicyRepository.get_effective_policy", new_callable=AsyncMock)
@patch("api.services.workspace_service.WorkspaceRepository.current_user_role", new_callable=AsyncMock)
@patch("api.services.source_service.submit_process_source_command", new_callable=AsyncMock)
@patch("api.services.source_service.resolve_default_model_id", new_callable=AsyncMock)
async def test_team_workspace_source_create_respects_create_policy(
    mock_resolve_model,
    mock_submit,
    mock_role,
    mock_policy,
):
    mock_resolve_model.return_value = "model:tools"
    mock_submit.return_value = "command:source"
    mock_role.return_value = {
        "type": "team",
        "team_id": "team:research",
        "current_user_role": "member",
    }
    mock_policy.return_value = WorkspacePermissionPolicy(member_can_create_source=False)

    with pytest.raises(PermissionError, match="Source creation permission required"):
        await create_source_and_queue_processing(
            SourceCreate(
                type="text",
                content="Team source",
                workspace_id="workspace:team",
            ),
            user_id="app_user:member",
            actor=actor(),
        )
