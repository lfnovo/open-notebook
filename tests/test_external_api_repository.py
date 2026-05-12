from unittest.mock import AsyncMock

import pytest

from open_notebook.database.repositories.external_api_repository import ExternalApiRepository


@pytest.mark.asyncio
async def test_month_usage_count_excludes_search_operations(monkeypatch):
    captured = {}

    async def fake_repo_query(query, params):
        captured["query"] = query
        captured["params"] = params
        return [{"count": 3}]

    monkeypatch.setattr(
        "open_notebook.database.repositories.external_api_repository.repo_query",
        AsyncMock(side_effect=fake_repo_query),
    )

    count = await ExternalApiRepository.month_usage_count(
        grant_id="external_source_team_grant:grant",
        month="2026-05",
    )

    assert count == 3
    assert "operation != 'search'" in captured["query"]
    assert str(captured["params"]["grant_id"]) == "external_source_team_grant:grant"
    assert captured["params"]["month"] == "2026-05"
