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
