from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
from api.models import ContextConfig, ContextRequest, ResourceCapabilities
from api.routers.context import get_notebook_context


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
@patch("api.routers.context.resolve_resource_capabilities", new_callable=AsyncMock)
async def test_notebook_context_ignores_sources_not_referenced_by_notebook(
    mock_capabilities,
):
    mock_capabilities.return_value = ResourceCapabilities(can_read=True)
    actor = CurrentUser(id="app_user:member", username="member", role="user")
    notebook = SimpleNamespace(
        id="notebook:team",
        owner_id="app_user:owner",
        workspace_id="workspace:team",
        visibility="team",
        get_sources=AsyncMock(return_value=[]),
        get_notes=AsyncMock(return_value=[]),
    )
    with patch(
        "api.routers.context.Notebook.get",
        new_callable=AsyncMock,
        return_value=notebook,
    ):
        response = await get_notebook_context(
            "notebook:team",
            ContextRequest(
                notebook_id="notebook:team",
                context_config=ContextConfig(
                    sources={"source:external": "full content"},
                    notes={},
                ),
            ),
            request_for_actor(actor),
        )

    assert response.sources == []
    assert response.total_tokens == 0
