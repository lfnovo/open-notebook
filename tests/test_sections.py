"""Sections: CRUD, folder placement, per-section folder-name uniqueness."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.domain.notebook import Folder, Section
from open_notebook.exceptions import NotFoundError


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


# --- sections -----------------------------------------------------------


def test_list_sections_sorted_with_folder_counts(client):
    rows = [
        {"id": "section:b", "name": "work", "created": "c", "updated": "u",
         "folder_count": 2},
        {"id": "section:a", "name": "Personal", "created": "c", "updated": "u",
         "folder_count": 0},
    ]  # fmt: skip
    with patch("api.routers.sections.repo_query", new=AsyncMock(return_value=rows)):
        response = client.get("/api/sections")
    assert response.status_code == 200
    body = response.json()
    assert [s["name"] for s in body] == ["Personal", "work"]
    assert body[1]["folder_count"] == 2


def test_create_section_trims_name(client):
    with (
        patch("api.routers.sections.repo_query", new=AsyncMock(return_value=[])),
        patch.object(Section, "save", new=AsyncMock()) as save,
    ):
        response = client.post("/api/sections", json={"name": "  Personal "})
    assert response.status_code == 200
    assert response.json()["name"] == "Personal"
    save.assert_awaited_once()


@pytest.mark.parametrize("name", ["", "   ", "x" * 81])
def test_create_section_invalid_name_400(client, name):
    with patch("api.routers.sections.repo_query", new=AsyncMock(return_value=[])):
        response = client.post("/api/sections", json={"name": name})
    assert response.status_code == 400


def test_create_section_duplicate_409(client):
    existing = [{"id": "section:s1", "name": "Personal"}]
    with (
        patch("api.routers.sections.repo_query", new=AsyncMock(return_value=existing)),
        patch.object(Section, "save", new=AsyncMock()) as save,
    ):
        response = client.post("/api/sections", json={"name": " personal"})
    assert response.status_code == 409
    save.assert_not_awaited()


def test_rename_section(client):
    section = Section(id="section:s1", name="Personal")
    with (
        patch("api.routers.sections.Section.get", new=AsyncMock(return_value=section)),
        patch(
            "api.routers.sections.repo_query",
            new=AsyncMock(
                side_effect=[[{"id": "section:s1", "name": "Personal"}], [{"n": 4}]]
            ),
        ),
        patch.object(Section, "save", new=AsyncMock()),
    ):
        response = client.put("/api/sections/section:s1", json={"name": " Home "})
    assert response.status_code == 200
    assert response.json()["name"] == "Home"
    assert response.json()["folder_count"] == 4


def test_rename_and_delete_missing_section_404(client):
    with patch(
        "api.routers.sections.Section.get",
        new=AsyncMock(side_effect=NotFoundError("nope")),
    ):
        assert (
            client.put("/api/sections/section:x", json={"name": "A"}).status_code == 404
        )
        assert client.delete("/api/sections/section:x").status_code == 404


def test_delete_section_ungroups_folders(client):
    section = Section(id="section:s1", name="Personal")
    with (
        patch("api.routers.sections.Section.get", new=AsyncMock(return_value=section)),
        patch(
            "api.routers.sections.repo_query",
            new=AsyncMock(return_value=[{"id": "folder:a"}, {"id": "folder:b"}]),
        ) as query,
        patch.object(Section, "delete", new=AsyncMock()) as delete,
    ):
        response = client.delete("/api/sections/section:s1")
    assert response.status_code == 200
    assert response.json()["folders_ungrouped"] == 2
    assert query.await_args is not None
    assert "SET section = NONE" in query.await_args.args[0]
    delete.assert_awaited_once()


# --- folders inside sections --------------------------------------------


def test_list_folders_includes_section_id(client):
    rows = [
        {"id": "folder:a", "name": "True crime", "section": "section:s1",
         "created": "c", "updated": "u", "notebook_count": 1},
        {"id": "folder:b", "name": "Loose", "created": "c", "updated": "u",
         "notebook_count": 0},
    ]  # fmt: skip
    with patch("api.routers.folders.repo_query", new=AsyncMock(return_value=rows)):
        body = client.get("/api/folders").json()
    by_name = {f["name"]: f for f in body}
    assert by_name["True crime"]["section_id"] == "section:s1"
    assert by_name["Loose"]["section_id"] is None


def test_create_folder_in_section(client):
    section = Section(id="section:s1", name="Personal")
    with (
        patch("api.routers.folders.Section.get", new=AsyncMock(return_value=section)),
        patch("api.routers.folders.repo_query", new=AsyncMock(return_value=[])),
        patch.object(Folder, "save", new=AsyncMock()) as save,
    ):
        response = client.post(
            "/api/folders", json={"name": "True crime", "section_id": "section:s1"}
        )
    assert response.status_code == 200
    assert response.json()["section_id"] == "section:s1"
    save.assert_awaited_once()


def test_create_folder_unknown_section_404(client):
    with (
        patch(
            "api.routers.folders.Section.get",
            new=AsyncMock(side_effect=NotFoundError("nope")),
        ),
        patch.object(Folder, "save", new=AsyncMock()) as save,
    ):
        response = client.post(
            "/api/folders", json={"name": "X", "section_id": "section:nope"}
        )
    assert response.status_code == 404
    save.assert_not_awaited()


def test_same_folder_name_allowed_in_different_sections(client):
    section = Section(id="section:s2", name="Work")
    existing = [{"id": "folder:f1", "name": "Misc", "section": "section:s1"}]
    with (
        patch("api.routers.folders.Section.get", new=AsyncMock(return_value=section)),
        patch("api.routers.folders.repo_query", new=AsyncMock(return_value=existing)),
        patch.object(Folder, "save", new=AsyncMock()),
    ):
        response = client.post(
            "/api/folders", json={"name": "misc", "section_id": "section:s2"}
        )
    assert response.status_code == 200


def test_duplicate_folder_name_in_same_section_409(client):
    section = Section(id="section:s1", name="Personal")
    existing = [{"id": "folder:f1", "name": "Misc", "section": "section:s1"}]
    with (
        patch("api.routers.folders.Section.get", new=AsyncMock(return_value=section)),
        patch("api.routers.folders.repo_query", new=AsyncMock(return_value=existing)),
        patch.object(Folder, "save", new=AsyncMock()),
    ):
        response = client.post(
            "/api/folders", json={"name": "misc", "section_id": "section:s1"}
        )
    assert response.status_code == 409


def test_move_folder_out_of_section_clears_link(client):
    folder = Folder(id="folder:f1", name="Misc", section="section:s1")
    with (
        patch("api.routers.folders.Folder.get", new=AsyncMock(return_value=folder)),
        patch(
            "api.routers.folders.repo_query",
            new=AsyncMock(side_effect=[[], [], [{"n": 0}]]),
        ) as query,
        patch.object(Folder, "save", new=AsyncMock()),
    ):
        response = client.put(
            "/api/folders/folder:f1", json={"name": "Misc", "section_id": None}
        )
    assert response.status_code == 200
    assert response.json()["section_id"] is None
    assert "section = NONE" in query.await_args_list[1].args[0]


def test_rename_without_section_id_keeps_section(client):
    folder = Folder(id="folder:f1", name="Misc", section="section:s1")
    with (
        patch("api.routers.folders.Folder.get", new=AsyncMock(return_value=folder)),
        patch(
            "api.routers.folders.repo_query",
            new=AsyncMock(side_effect=[[], [{"n": 0}]]),
        ),
        patch.object(Folder, "save", new=AsyncMock()),
    ):
        response = client.put("/api/folders/folder:f1", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json()["section_id"] == "section:s1"
