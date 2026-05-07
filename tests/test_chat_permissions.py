from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from api.auth import CurrentUser
from api.models import ResourceCapabilities
from api.routers.chat import (
    CreateSessionRequest,
    _ensure_session_notebook_owner,
    create_session,
)
from open_notebook.domain.notebook import ChatSession


@pytest.mark.asyncio
async def test_session_owner_check_rejects_non_owner():
    with patch(
        "api.routers.chat._notebook_id_for_session",
        new_callable=AsyncMock,
        return_value="notebook:team",
    ), patch(
        "api.routers.chat.Notebook.get",
        new_callable=AsyncMock,
        return_value=SimpleNamespace(owner_id="app_user:owner", visibility="team"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await _ensure_session_notebook_owner(
                "chat_session:one",
                user_id="app_user:member",
            )

    assert exc_info.value.status_code == 403


def request_for_actor(actor: CurrentUser):
    return SimpleNamespace(
        state=SimpleNamespace(
            user_id=actor.id,
            username=actor.username,
            user_role=actor.role,
            user_status=actor.status,
        )
    )


@pytest.mark.asyncio
@patch("api.routers.chat.resolve_resource_capabilities", new_callable=AsyncMock)
@patch("api.routers.chat.ensure_model_selection_allowed", new_callable=AsyncMock)
@patch("api.routers.chat.resolve_team_context", new_callable=AsyncMock)
@patch("api.routers.chat.Notebook.get", new_callable=AsyncMock)
async def test_create_chat_session_inherits_notebook_workspace(
    mock_notebook_get,
    mock_team_context,
    mock_model_allowed,
    mock_capabilities,
):
    actor = CurrentUser(id="app_user:member", username="member", role="user")
    mock_notebook_get.return_value = SimpleNamespace(
        id="notebook:team",
        owner_id="app_user:owner",
        workspace_id="workspace:team",
        visibility="team",
    )
    mock_team_context.return_value = "team:research"
    mock_capabilities.return_value = ResourceCapabilities(can_read=True)
    saved_sessions = []

    async def capture_save(self_session):
        saved_sessions.append(self_session)
        self_session.id = "chat_session:team"

    with patch.object(ChatSession, "save", autospec=True, side_effect=capture_save), patch.object(
        ChatSession,
        "relate_to_notebook",
        new_callable=AsyncMock,
    ):
        response = await create_session(
            CreateSessionRequest(notebook_id="notebook:team", title="Team chat"),
            request_for_actor(actor),
    )

    assert response.id == "chat_session:team"
    assert str(saved_sessions[0].owner_id) == "app_user:member"
    assert str(saved_sessions[0].workspace_id) == "workspace:team"


@pytest.mark.asyncio
@patch("api.routers.chat.resolve_resource_capabilities", new_callable=AsyncMock)
@patch("api.routers.chat._notebook_id_for_session", new_callable=AsyncMock)
@patch("api.routers.chat.Notebook.get", new_callable=AsyncMock)
async def test_session_delete_uses_chat_session_capability(
    mock_notebook_get,
    mock_notebook_id,
    mock_capabilities,
):
    mock_notebook_id.return_value = "notebook:team"
    mock_notebook_get.return_value = SimpleNamespace(
        owner_id="app_user:owner",
        workspace_id="workspace:team",
        visibility="team",
    )
    mock_capabilities.return_value = ResourceCapabilities(can_delete=True)

    notebook_id = await _ensure_session_notebook_owner(
        "chat_session:one",
        user_id="app_user:member",
        actor=CurrentUser(id="app_user:member", username="member", role="user"),
    )

    assert notebook_id == "notebook:team"
