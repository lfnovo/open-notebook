from unittest.mock import AsyncMock

import pytest

from open_notebook.database.repositories.notebook_repository import NotebookRepository


@pytest.mark.asyncio
async def test_list_notebooks_selects_creator_username(monkeypatch):
    captured = {}

    async def fake_repo_query(query, params):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(
        "open_notebook.database.repositories.notebook_repository.repo_query",
        AsyncMock(side_effect=fake_repo_query),
    )

    await NotebookRepository.list_notebooks(
        user_id="app_user:member",
        team_ids=[],
        archived=None,
        order_by="updated desc",
    )

    assert "creator_username" in captured["query"]
    assert "FROM app_user WHERE id = $parent.owner_id" in captured["query"]


@pytest.mark.asyncio
async def test_list_public_notebooks_selects_metrics_and_paginates(monkeypatch):
    captured = {}

    async def fake_repo_query(query, params):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(
        "open_notebook.database.repositories.notebook_repository.repo_query",
        AsyncMock(side_effect=fake_repo_query),
    )

    await NotebookRepository.list_notebooks(
        user_id=None,
        archived=None,
        order_by="view_count desc",
        public_only=True,
        limit=20,
        offset=0,
    )

    assert "view_count" in captured["query"]
    assert "AS reference_count" in captured["query"]
    assert "LIMIT $limit START $offset" in captured["query"]
    assert captured["params"]["limit"] == 20
    assert captured["params"]["offset"] == 0


@pytest.mark.asyncio
async def test_increment_view_count_updates_notebook_metric(monkeypatch):
    captured = {}

    async def fake_repo_query(query, params):
        captured["query"] = query
        captured["params"] = params
        return [{"id": "notebook:public", "view_count": 5}]

    monkeypatch.setattr(
        "open_notebook.database.repositories.notebook_repository.repo_query",
        AsyncMock(side_effect=fake_repo_query),
    )

    result = await NotebookRepository.increment_view_count("notebook:public")

    assert "view_count = (view_count OR 0) + 1" in captured["query"]
    assert str(captured["params"]["notebook_id"]) == "notebook:public"
    assert result["view_count"] == 5


@pytest.mark.asyncio
async def test_list_notebooks_filters_by_workspace_id(monkeypatch):
    captured = {}

    async def fake_repo_query(query, params):
        captured["query"] = query
        captured["params"] = params
        return []

    monkeypatch.setattr(
        "open_notebook.database.repositories.notebook_repository.repo_query",
        AsyncMock(side_effect=fake_repo_query),
    )

    await NotebookRepository.list_notebooks(
        user_id="app_user:member",
        team_ids=[],
        archived=None,
        order_by="updated desc",
        workspace_id="workspace:team",
    )

    assert "workspace_id = $workspace_id" in captured["query"]
    assert str(captured["params"]["workspace_id"]) == "workspace:team"
