import pytest

from open_notebook.database.repositories import workspace_repository as module
from open_notebook.database.repositories.workspace_repository import WorkspaceRepository


@pytest.mark.asyncio
async def test_ensure_personal_workspace_reuses_existing_workspace(monkeypatch):
    calls = []

    async def fake_repo_query(query, vars=None):
        calls.append((query, vars))
        if "WHERE type = 'personal'" in query:
            return [{"id": "workspace:personal", "name": "Alice", "type": "personal"}]
        raise AssertionError("create query should not run when workspace exists")

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    row = await WorkspaceRepository.ensure_personal_workspace(
        user_id="app_user:alice",
        display_name="Alice",
    )

    assert row["id"] == "workspace:personal"
    assert len(calls) == 1
    assert str(calls[0][1]["user_id"]) == "app_user:alice"


@pytest.mark.asyncio
async def test_ensure_personal_workspace_creates_missing_workspace(monkeypatch):
    calls = []

    async def fake_repo_query(query, vars=None):
        calls.append((query, vars))
        if "WHERE type = 'personal'" in query:
            return []
        return [
            {
                "id": "workspace:created",
                "name": "Alice",
                "type": "personal",
                "owner_id": vars["user_id"],
            }
        ]

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    row = await WorkspaceRepository.ensure_personal_workspace(
        user_id="app_user:alice",
        display_name="Alice",
    )

    assert row["id"] == "workspace:created"
    assert "CREATE workspace SET" in calls[1][0]
    assert calls[1][1]["name"] == "Alice"
    assert str(calls[1][1]["user_id"]) == "app_user:alice"


@pytest.mark.asyncio
async def test_ensure_team_workspace_creates_missing_workspace(monkeypatch):
    calls = []

    async def fake_repo_query(query, vars=None):
        calls.append((query, vars))
        if "WHERE type = 'team'" in query:
            return []
        return [
            {
                "id": "workspace:team",
                "name": "Research",
                "type": "team",
                "team_id": vars["team_id"],
            }
        ]

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    row = await WorkspaceRepository.ensure_team_workspace(
        team_id="team:research",
        name="Research",
        created_by="app_user:admin",
    )

    assert row["id"] == "workspace:team"
    assert "CREATE workspace SET" in calls[1][0]
    assert str(calls[1][1]["team_id"]) == "team:research"
    assert str(calls[1][1]["created_by"]) == "app_user:admin"


@pytest.mark.asyncio
async def test_get_workspace_for_resource_loads_resource_workspace(monkeypatch):
    calls = []

    async def fake_repo_query(query, vars=None):
        calls.append((query, vars))
        if "SELECT workspace_id FROM $resource_id" in query:
            return [{"workspace_id": "workspace:team"}]
        return [{"id": "workspace:team", "type": "team", "team_id": "team:research"}]

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    row = await WorkspaceRepository.get_workspace_for_resource(
        resource_type="notebook",
        resource_id="notebook:abc",
    )

    assert row["team_id"] == "team:research"
    assert str(calls[0][1]["resource_id"]) == "notebook:abc"
    assert str(calls[1][1]["workspace_id"]) == "workspace:team"


@pytest.mark.asyncio
async def test_get_workspace_for_resource_rejects_unknown_table(monkeypatch):
    async def fake_repo_query(query, vars=None):
        raise AssertionError("unknown resource types should not query")

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    row = await WorkspaceRepository.get_workspace_for_resource(
        resource_type="unknown",
        resource_id="unknown:abc",
    )

    assert row is None


@pytest.mark.asyncio
async def test_move_notebook_to_workspace_updates_notebook_notes_and_chat_sessions(
    monkeypatch,
):
    captured = {}

    async def fake_repo_query(query, vars=None):
        captured["query"] = query
        captured["vars"] = vars
        return []

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    await WorkspaceRepository.move_notebook_to_workspace(
        notebook_id="notebook:abc",
        workspace_id="workspace:team",
    )

    assert "UPDATE $notebook_id SET workspace_id = $workspace_id" in captured["query"]
    assert "UPDATE note SET workspace_id = $workspace_id" in captured["query"]
    assert "UPDATE chat_session SET workspace_id = $workspace_id" in captured["query"]
    assert str(captured["vars"]["notebook_id"]) == "notebook:abc"
    assert str(captured["vars"]["workspace_id"]) == "workspace:team"


@pytest.mark.asyncio
async def test_list_for_user_includes_personal_and_active_team_workspaces(monkeypatch):
    captured = {}

    async def fake_repo_query(query, vars=None):
        captured["query"] = query
        captured["vars"] = vars
        return [
            {"id": "workspace:personal", "type": "personal"},
            {"id": "workspace:team", "type": "team"},
        ]

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    rows = await WorkspaceRepository.list_for_user(
        user_id="app_user:alice",
        include_all_for_admin=False,
    )

    assert [row["id"] for row in rows] == ["workspace:personal", "workspace:team"]
    assert "owner_id = $user_id" in captured["query"]
    assert "team_member" in captured["query"]
    assert str(captured["vars"]["user_id"]) == "app_user:alice"


@pytest.mark.asyncio
async def test_list_for_admin_observes_all_workspaces_without_global_manage(monkeypatch):
    captured = {}

    async def fake_repo_query(query, vars=None):
        captured["query"] = query
        captured["vars"] = vars
        return [
            {"id": "workspace:personal", "type": "personal", "can_manage": False},
            {"id": "workspace:team", "type": "team", "can_manage": False},
        ]

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    rows = await WorkspaceRepository.list_for_user(
        user_id="app_user:admin",
        include_all_for_admin=True,
    )

    assert [row["id"] for row in rows] == ["workspace:personal", "workspace:team"]
    assert "FROM workspace" in captured["query"]
    assert "true AS can_manage" not in captured["query"]
    assert str(captured["vars"]["user_id"]) == "app_user:admin"
