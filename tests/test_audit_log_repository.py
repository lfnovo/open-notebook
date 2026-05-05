import pytest

from open_notebook.database.repositories import audit_log_repository as module
from open_notebook.database.repositories.audit_log_repository import AuditLogRepository


@pytest.mark.asyncio
async def test_count_logs_uses_same_filters_as_list(monkeypatch):
    captured = {}

    async def fake_repo_query(query, vars=None):
        captured["query"] = query
        captured["vars"] = vars
        return [{"count": 7}]

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    count = await AuditLogRepository.count_logs(
        actor_id="app_user:admin",
        action="team.created",
        target_id="team:research",
    )

    assert count == 7
    assert "SELECT count() AS count FROM audit_log" in captured["query"]
    assert "actor_id = $actor_id" in captured["query"]
    assert "action = $action" in captured["query"]
    assert "target_id = $target_id" in captured["query"]
    assert str(captured["vars"]["actor_id"]) == "app_user:admin"
    assert captured["vars"]["action"] == "team.created"
    assert captured["vars"]["target_id"] == "team:research"


@pytest.mark.asyncio
async def test_list_logs_rotates_pages_with_limit_and_offset(monkeypatch):
    captured = {}

    async def fake_repo_query(query, vars=None):
        captured["query"] = query
        captured["vars"] = vars
        return []

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    await AuditLogRepository.list_logs(limit=25, offset=50)

    assert "ORDER BY created DESC" in captured["query"]
    assert "LIMIT $limit START $offset" in captured["query"]
    assert captured["vars"]["limit"] == 25
    assert captured["vars"]["offset"] == 50
