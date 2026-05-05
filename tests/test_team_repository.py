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
