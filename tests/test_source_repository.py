from unittest.mock import AsyncMock

import pytest

from open_notebook.database.repositories.source_repository import SourceRepository


@pytest.mark.asyncio
async def test_list_sources_selects_numeric_insight_and_reference_counts(monkeypatch):
    captured = {}

    async def fake_repo_query(query, params):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(
        "open_notebook.database.repositories.source_repository.repo_query",
        AsyncMock(side_effect=fake_repo_query),
    )

    await SourceRepository.list_sources(
        user_id="app_user:member",
        team_ids=[],
        notebook_id=None,
        title_contains=None,
        limit=50,
        offset=0,
        sort_by="updated",
        sort_order="desc",
    )

    assert "AS insights_count" in captured["query"]
    assert "AS reference_count" in captured["query"]
    assert "[0].count" not in captured["query"]


@pytest.mark.asyncio
async def test_list_sources_filters_by_workspace_id(monkeypatch):
    captured = {}

    async def fake_repo_query(query, params):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(
        "open_notebook.database.repositories.source_repository.repo_query",
        AsyncMock(side_effect=fake_repo_query),
    )

    await SourceRepository.list_sources(
        user_id="app_user:member",
        team_ids=[],
        notebook_id=None,
        title_contains=None,
        limit=50,
        offset=0,
        sort_by="updated",
        sort_order="desc",
        workspace_id="workspace:team",
    )

    assert "workspace_id = $workspace_id" in captured["query"]
    assert str(captured["params"]["workspace_id"]) == "workspace:team"


@pytest.mark.asyncio
async def test_list_workspace_sources_excludes_team_share_grants(monkeypatch):
    captured = {}

    async def fake_repo_query(query, params):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(
        "open_notebook.database.repositories.source_repository.repo_query",
        AsyncMock(side_effect=fake_repo_query),
    )

    await SourceRepository.list_sources(
        user_id="app_user:member",
        team_ids=["team:research"],
        notebook_id=None,
        title_contains=None,
        limit=50,
        offset=0,
        sort_by="updated",
        sort_order="desc",
        workspace_id="workspace:team",
    )

    assert "workspace_id = $workspace_id" in captured["query"]
    assert "share_grant" not in captured["query"]
    assert "visibility = 'public'" not in captured["query"]
    assert "owner_id = $user_id OR team_id IN" in captured["query"]
