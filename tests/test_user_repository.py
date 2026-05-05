import pytest

from open_notebook.database.repositories import user_repository
from open_notebook.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_list_users_treats_missing_status_as_active(monkeypatch):
    async def fake_repo_query(query, params):
        assert "status = $status" not in query
        assert "LIMIT $limit START $offset" not in query
        assert params == {}
        return [
            {"id": "app_user:legacy", "username": "legacy"},
            {"id": "app_user:active", "username": "active", "status": "active"},
            {"id": "app_user:disabled", "username": "disabled", "status": "disabled"},
        ]

    monkeypatch.setattr(user_repository, "repo_query", fake_repo_query)

    rows = await UserRepository.list_users(status="active", limit=50, offset=0)

    assert [row["username"] for row in rows] == ["legacy", "active"]


@pytest.mark.asyncio
async def test_count_users_treats_missing_status_as_active(monkeypatch):
    async def fake_repo_query(query, params):
        assert "count()" not in query
        assert "status = $status" not in query
        assert params == {}
        return [
            {"id": "app_user:legacy", "username": "legacy"},
            {"id": "app_user:active", "username": "active", "status": "active"},
            {"id": "app_user:disabled", "username": "disabled", "status": "disabled"},
        ]

    monkeypatch.setattr(user_repository, "repo_query", fake_repo_query)

    total = await UserRepository.count_users(status="active")

    assert total == 2
