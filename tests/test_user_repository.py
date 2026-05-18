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


@pytest.mark.asyncio
async def test_create_wechat_user_sets_schema_compatible_password(monkeypatch):
    captured = {}

    async def fake_repo_query(query, params):
        captured["query"] = query
        captured["params"] = params
        return [{"id": "app_user:wx_openid", "username": params["username"]}]

    monkeypatch.setattr(user_repository, "repo_query", fake_repo_query)

    row = await UserRepository.create_wechat_user(
        {
            "username": "wx_openid",
            "display_name": "WeChat User",
            "avatar_url": None,
            "wechat_openid": "openid",
            "wechat_unionid": None,
        }
    )

    assert row["username"] == "wx_openid"
    assert "hashed_password = $hashed_password" in captured["query"]
    assert captured["params"]["hashed_password"] == ""
