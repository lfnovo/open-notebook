import pytest

from open_notebook.database.repositories.team_allowlist_repository import (
    TeamAllowlistRepository,
)
from open_notebook.database.repositories import team_allowlist_repository as module


@pytest.mark.asyncio
async def test_list_team_models_fetches_model_records(monkeypatch):
    captured = {}

    async def fake_repo_query(query, vars=None):
        captured["query"] = query
        captured["vars"] = vars
        return [{"model": {"id": "model:chat", "name": "Chat"}}]

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    result = await TeamAllowlistRepository.list_team_models("team:research")

    assert result == [{"model": {"id": "model:chat", "name": "Chat"}}]
    assert "FROM team_model" in captured["query"]
    assert "FETCH model" in captured["query"]
    assert str(captured["vars"]["team_id"]) == "team:research"


@pytest.mark.asyncio
async def test_replace_team_models_replaces_allowlist_in_transaction(monkeypatch):
    captured = {}

    async def fake_repo_transaction(query_body, vars=None):
        captured["query_body"] = query_body
        captured["vars"] = vars
        return [[], {"ok": True}, {"ok": True}, [{"id": "team_model:1"}]]

    monkeypatch.setattr(module, "repo_transaction", fake_repo_transaction)

    result = await TeamAllowlistRepository.replace_team_models(
        "team:research",
        ["model:chat", "model:embed"],
        "app_user:admin",
    )

    assert result == [{"id": "team_model:1"}]
    assert "DELETE team_model WHERE team = $team_id" in captured["query_body"]
    assert captured["query_body"].count("CREATE team_model SET") == 2
    assert "SELECT * FROM team_model" in captured["query_body"]
    assert str(captured["vars"]["team_id"]) == "team:research"
    assert str(captured["vars"]["model_id_0"]) == "model:chat"
    assert str(captured["vars"]["model_id_1"]) == "model:embed"
    assert str(captured["vars"]["created_by"]) == "app_user:admin"


@pytest.mark.asyncio
async def test_replace_team_models_rejects_invalid_model_record_id(monkeypatch):
    async def fake_repo_transaction(query_body, vars=None):
        raise AssertionError("transaction should not run for invalid record ids")

    monkeypatch.setattr(module, "repo_transaction", fake_repo_transaction)

    with pytest.raises(Exception):
        await TeamAllowlistRepository.replace_team_models(
            "team:research",
            ["not-a-record-id"],
            "app_user:admin",
        )


@pytest.mark.asyncio
async def test_list_team_transformations_fetches_transformation_records(monkeypatch):
    captured = {}

    async def fake_repo_query(query, vars=None):
        captured["query"] = query
        captured["vars"] = vars
        return [
            {
                "transformation": {
                    "id": "transformation:summary",
                    "name": "summary",
                }
            }
        ]

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    result = await TeamAllowlistRepository.list_team_transformations("team:research")

    assert result[0]["transformation"]["id"] == "transformation:summary"
    assert "FROM team_transformation" in captured["query"]
    assert "FETCH transformation" in captured["query"]
    assert str(captured["vars"]["team_id"]) == "team:research"


@pytest.mark.asyncio
async def test_replace_team_transformations_replaces_allowlist_in_transaction(monkeypatch):
    captured = {}

    async def fake_repo_transaction(query_body, vars=None):
        captured["query_body"] = query_body
        captured["vars"] = vars
        return [[], {"ok": True}, [{"id": "team_transformation:1"}]]

    monkeypatch.setattr(module, "repo_transaction", fake_repo_transaction)

    result = await TeamAllowlistRepository.replace_team_transformations(
        "team:research",
        ["transformation:summary"],
        "app_user:admin",
    )

    assert result == [{"id": "team_transformation:1"}]
    assert "DELETE team_transformation WHERE team = $team_id" in captured["query_body"]
    assert captured["query_body"].count("CREATE team_transformation SET") == 1
    assert "SELECT * FROM team_transformation" in captured["query_body"]
    assert str(captured["vars"]["team_id"]) == "team:research"
    assert str(captured["vars"]["transformation_id_0"]) == "transformation:summary"
    assert str(captured["vars"]["created_by"]) == "app_user:admin"
