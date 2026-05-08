from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.auth import CurrentUser
from api.models import ResourceCapabilities, SearchRequest
from api.routers.search import (
    _dedupe_search_results,
    _resolve_ask_models,
    _search_result_resource_id,
    search_knowledge_base,
)
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


def test_search_result_resource_id_accepts_record_objects():
    record_id = SimpleNamespace(tb="source", id="bsd_source")

    assert _search_result_resource_id({"parent_id": record_id}) == "source:bsd_source"
    assert _search_result_resource_id({"parent_id": [record_id]}) == "source:bsd_source"


def test_search_results_are_deduped_by_resource_score():
    results = _dedupe_search_results(
        [
            {"id": "source:item", "parent_id": "source:item", "relevance": 0.2},
            {"id": "source:item", "parent_id": "source:item", "relevance": 0.8},
            {"id": "note:item", "parent_id": "note:item", "relevance": 0.5},
        ]
    )

    assert [item["parent_id"] for item in results] == ["source:item", "note:item"]
    assert [item["relevance"] for item in results] == [0.8, 0.5]


@pytest.mark.asyncio
@patch("api.routers.search.text_search", new_callable=AsyncMock)
async def test_system_admin_cannot_use_search(mock_text_search):
    actor = CurrentUser(id="app_user:admin", username="admin", role="admin")

    with pytest.raises(Exception) as exc_info:
        await search_knowledge_base(
            SearchRequest(query="source", type="text"),
            request_for_actor(actor),
        )

    assert getattr(exc_info.value, "status_code", None) == 403
    mock_text_search.assert_not_awaited()


@pytest.mark.asyncio
async def test_system_admin_cannot_use_ask():
    actor = CurrentUser(id="app_user:admin", username="admin", role="admin")

    with pytest.raises(Exception) as exc_info:
        await _resolve_ask_models(
            SimpleNamespace(question="BSD") ,
            request_for_actor(actor),
        )

    assert getattr(exc_info.value, "status_code", None) == 403


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
            "id": SimpleNamespace(tb="source", id="team"),
            "parent_id": [SimpleNamespace(tb="source", id="team")],
            "owner_id": "app_user:owner",
            "workspace_id": "workspace:team",
            "visibility": "team",
            "title": ["Team source"],
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
    assert [item["parent_id"] for item in response.results] == ["source:team"]
    assert [item["title"] for item in response.results] == ["Team source"]



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
