from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
from api.models import ResourceCapabilities, SearchRequest
from api.routers.search import search_knowledge_base
from open_notebook.domain.notebook import Source
from open_notebook.graphs.ask import _filter_results_for_scope


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
@patch("api.routers.search.resolve_resource_capabilities", new_callable=AsyncMock)
@patch("api.routers.search.text_search", new_callable=AsyncMock)
@patch("api.routers.search.resolve_explicit_team_context", new_callable=AsyncMock)
async def test_search_filters_results_by_resource_capability(
    mock_team_context,
    mock_text_search,
    mock_capabilities,
):
    actor = CurrentUser(id="app_user:member", username="member", role="user")
    mock_team_context.return_value = None
    mock_text_search.return_value = [
        {
            "id": "source:private",
            "owner_id": "app_user:other",
            "workspace_id": "workspace:other",
            "visibility": "private",
            "title": "Private source",
        },
        {
            "id": "source:team",
            "owner_id": "app_user:owner",
            "workspace_id": "workspace:team",
            "visibility": "team",
            "title": "Team source",
        },
    ]
    mock_capabilities.side_effect = [
        ResourceCapabilities(can_read=False),
        ResourceCapabilities(can_read=True),
    ]

    response = await search_knowledge_base(
        SearchRequest(query="source", type="text"),
        request_for_actor(actor),
    )

    assert [item["id"] for item in response.results] == ["source:team"]


@pytest.mark.asyncio
@patch("open_notebook.graphs.ask.ShareRepository.has_read_grant", new_callable=AsyncMock)
@patch("open_notebook.graphs.ask.Source.get", new_callable=AsyncMock)
async def test_ask_search_filters_results_by_workspace_scope(
    mock_source_get,
    mock_read_grant,
):
    mock_read_grant.return_value = False
    mock_source_get.side_effect = [
        Source(
            id="source:private",
            owner_id="app_user:other",
            workspace_id="workspace:other",
            visibility="private",
        ),
        Source(
            id="source:team",
            owner_id="app_user:owner",
            workspace_id="workspace:team",
            visibility="team",
        ),
    ]

    filtered = await _filter_results_for_scope(
        [
            {"id": "source:private", "title": "Private"},
            {"id": "kg_entity:item", "source_id": "source:team", "title": "Team KG"},
        ],
        {
            "actor_id": "app_user:member",
            "actor_role": "user",
            "team_ids": ["team:research"],
            "workspace_ids": ["workspace:team"],
        },
    )

    assert [item["title"] for item in filtered] == ["Team KG"]
