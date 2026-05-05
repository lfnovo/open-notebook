import pytest

from open_notebook.database.repositories import team_repository as module
from open_notebook.database.repositories.team_repository import TeamRepository


@pytest.mark.asyncio
async def test_dependency_counts_accepts_return_object(monkeypatch):
    async def fake_repo_query(query, vars=None):
        return {"active_members": 0, "share_grants": 0}

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    result = await TeamRepository.dependency_counts("team:research")

    assert result == {"active_members": 0, "share_grants": 0}


@pytest.mark.asyncio
async def test_delete_team_cleans_related_team_records(monkeypatch):
    captured = {}

    async def fake_repo_transaction(query_body, vars=None):
        captured["query_body"] = query_body
        captured["vars"] = vars
        return []

    monkeypatch.setattr(module, "repo_transaction", fake_repo_transaction)

    await TeamRepository.delete_team("team:research")

    assert "DELETE team_member WHERE team = $team_id" in captured["query_body"]
    assert "DELETE team_model WHERE team = $team_id" in captured["query_body"]
    assert "DELETE team_transformation WHERE team = $team_id" in captured["query_body"]
    assert "DELETE $team_id" in captured["query_body"]
    assert str(captured["vars"]["team_id"]) == "team:research"
