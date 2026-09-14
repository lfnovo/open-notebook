from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("notebook_id", [None, "notebook:test"])
@pytest.mark.parametrize("count", [0, 120, 6243])
def test_source_list_reports_embedded_chunks(notebook_id, count):
    from api.main import app

    row = {
        "id": "source:test",
        "title": "Embedded document",
        "created": "2026-09-01T00:00:00Z",
        "updated": "2026-09-01T00:00:00Z",
        "embedded": count > 0,
        "embedded_chunks": count,
    }
    with (
        patch(
            "api.routers.sources.repo_query", new_callable=AsyncMock, return_value=[row]
        ) as query,
        patch(
            "api.routers.sources.Notebook.get",
            new_callable=AsyncMock,
            return_value=object(),
        ),
    ):
        response = TestClient(app).get(
            "/api/sources", params={"notebook_id": notebook_id} if notebook_id else {}
        )

    assert response.status_code == 200
    assert response.json()[0]["embedded_chunks"] == count
    assert response.json()[0]["embedded"] is (count > 0)
    query.assert_awaited_once()
    assert "AS embedded_chunks" in query.await_args.args[0]


def test_source_list_defaults_missing_embedded_chunks_to_zero():
    from api.main import app

    row = {
        "id": "source:test",
        "created": "2026-09-01T00:00:00Z",
        "updated": "2026-09-01T00:00:00Z",
    }
    with patch(
        "api.routers.sources.repo_query", new_callable=AsyncMock, return_value=[row]
    ):
        response = TestClient(app).get("/api/sources")

    assert response.status_code == 200
    assert response.json()[0]["embedded_chunks"] == 0
