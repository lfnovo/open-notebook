from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.models import NotebookCreate
from api.routers.notebooks import create_notebook
from open_notebook.domain.notebook import Notebook


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


@pytest.mark.asyncio
@patch("api.routers.notebooks.resolve_workspace_id_for_user", new_callable=AsyncMock)
async def test_create_notebook_persists_workspace_id(mock_workspace_id, client):
    mock_workspace_id.return_value = "workspace:team"
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


@pytest.mark.asyncio
@patch("api.routers.notebooks.resolve_workspace_id_for_user", new_callable=AsyncMock)
async def test_system_admin_cannot_create_notebooks(mock_workspace_id):
    class Request:
        state = type(
            "State",
            (),
            {
                "user_id": "app_user:admin",
                "username": "admin",
                "user_role": "admin",
                "user_status": "active",
            },
        )()

    with pytest.raises(Exception) as exc_info:
        await create_notebook(
            Request(),
            NotebookCreate(name="Admin notebook", description=""),
        )

    assert getattr(exc_info.value, "status_code", None) == 403
    mock_workspace_id.assert_not_awaited()
