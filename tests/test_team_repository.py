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
    assert "DELETE share_grant WHERE target_type = 'team'" in captured["query_body"]
    assert "DELETE workspace WHERE team_id = $team_id" in captured["query_body"]
    assert "DELETE $team_id" in captured["query_body"]
    assert str(captured["vars"]["team_id"]) == "team:research"


@pytest.mark.asyncio
async def test_update_model_defaults_updates_only_team_default_fields(monkeypatch):
    captured = {}

    async def fake_repo_update(table, record_id, data):
        captured["table"] = table
        captured["record_id"] = record_id
        captured["data"] = data
        return [{**data, "id": record_id}]

    monkeypatch.setattr(module, "repo_update", fake_repo_update)

    result = await TeamRepository.update_model_defaults(
        "team:research",
        {
            "default_chat_model": "model:chat",
            "default_embedding_model": None,
            "default_transformation_model": "model:chat",
            "default_tools_model": None,
            "large_context_model": "model:large",
        },
    )

    assert str(result["default_chat_model"]) == "model:chat"
    assert captured["table"] == "team"
    assert captured["record_id"] == "team:research"
    assert {
        key: str(value) if value else None
        for key, value in captured["data"].items()
    } == {
        "default_chat_model": "model:chat",
        "default_embedding_model": None,
        "default_transformation_model": "model:chat",
        "default_tools_model": None,
        "large_context_model": "model:large",
    }


@pytest.mark.asyncio
async def test_clear_invalid_model_defaults_nulls_removed_allowlist_models(monkeypatch):
    captured = {}

    async def fake_repo_query(query, vars=None):
        captured["query"] = query
        captured["vars"] = vars
        return []

    monkeypatch.setattr(module, "repo_query", fake_repo_query)

    await TeamRepository.clear_invalid_model_defaults(
        "team:research",
        ["model:chat", "model:embed"],
    )

    assert "default_chat_model" in captured["query"]
    assert "default_embedding_model" in captured["query"]
    assert "default_transformation_model" in captured["query"]
    assert "default_tools_model" in captured["query"]
    assert "large_context_model" in captured["query"]
    assert str(captured["vars"]["team_id"]) == "team:research"
    assert [str(model_id) for model_id in captured["vars"]["model_ids"]] == [
        "model:chat",
        "model:embed",
    ]
