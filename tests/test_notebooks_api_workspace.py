from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.domain.notebook import Notebook


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


@pytest.mark.asyncio
async def test_create_notebook_persists_workspace_id(client):
    saved_notebooks = []

    async def capture_save(self_notebook):
        saved_notebooks.append(self_notebook)
        self_notebook.id = "notebook:fake"

    with patch.object(Notebook, "save", autospec=True, side_effect=capture_save):
        response = client.post(
            "/api/notebooks",
            json={
                "name": "Team notebook",
                "description": "Shared research",
                "workspace_id": "workspace:team",
            },
        )

    assert response.status_code == 200
    assert response.json()["workspace_id"] == "workspace:team"
    assert len(saved_notebooks) == 1
    assert str(saved_notebooks[0].workspace_id) == "workspace:team"
