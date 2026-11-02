"""Notebook folders: folder CRUD, notebook move/unmove semantics, list filter."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.domain.notebook import Folder, Notebook
from open_notebook.exceptions import NotFoundError


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def _folder(fid="folder:f1", name="Work"):
    return Folder(id=fid, name=name)


# --- folders ------------------------------------------------------------


def test_list_folders_sorted_by_name_with_counts(client):
    rows = [
        {"id": "folder:b", "name": "beta", "created": "c", "updated": "u",
         "notebook_count": 2},
        {"id": "folder:a", "name": "Zed", "created": "c", "updated": "u",
         "notebook_count": 0},
        {"id": "folder:c", "name": "Alpha", "created": "c", "updated": "u",
         "notebook_count": 1},
    ]  # fmt: skip
    with patch("api.routers.folders.repo_query", new=AsyncMock(return_value=rows)):
        response = client.get("/api/folders")
    assert response.status_code == 200
    body = response.json()
    assert [f["name"] for f in body] == ["Alpha", "beta", "Zed"]
    assert body[1] == {
        "id": "folder:b",
        "name": "beta",
        "created": "c",
        "updated": "u",
        "notebook_count": 2,
    }


def test_create_folder_trims_name(client):
    with (
        patch("api.routers.folders.repo_query", new=AsyncMock(return_value=[])),
        patch.object(Folder, "save", new=AsyncMock()) as save,
    ):
        response = client.post("/api/folders", json={"name": "  Research  "})
    assert response.status_code == 200
    assert response.json()["name"] == "Research"
    assert response.json()["notebook_count"] == 0
    save.assert_awaited_once()


@pytest.mark.parametrize("name", ["", "   ", "x" * 81])
def test_create_folder_invalid_name(client, name):
    with patch("api.routers.folders.repo_query", new=AsyncMock(return_value=[])):
        response = client.post("/api/folders", json={"name": name})
    assert response.status_code == 400


def test_create_folder_max_length_ok(client):
    with (
        patch("api.routers.folders.repo_query", new=AsyncMock(return_value=[])),
        patch.object(Folder, "save", new=AsyncMock()),
    ):
        response = client.post("/api/folders", json={"name": "x" * 80})
    assert response.status_code == 200


def test_create_folder_duplicate_case_insensitive_409(client):
    existing = [{"id": "folder:f1", "name": "Work"}]
    with (
        patch("api.routers.folders.repo_query", new=AsyncMock(return_value=existing)),
        patch.object(Folder, "save", new=AsyncMock()) as save,
    ):
        response = client.post("/api/folders", json={"name": " wORK "})
    assert response.status_code == 409
    save.assert_not_awaited()


def test_rename_folder(client):
    folder = _folder()
    with (
        patch("api.routers.folders.Folder.get", new=AsyncMock(return_value=folder)),
        patch(
            "api.routers.folders.repo_query",
            new=AsyncMock(
                side_effect=[
                    [{"id": "folder:f1", "name": "Work"}],  # name check
                    [{"n": 3}],  # notebook count
                ]
            ),
        ),
        patch.object(Folder, "save", new=AsyncMock()),
    ):
        response = client.put("/api/folders/folder:f1", json={"name": " Play "})
    assert response.status_code == 200
    assert response.json()["name"] == "Play"
    assert response.json()["notebook_count"] == 3


def test_rename_folder_to_own_name_with_other_case_ok(client):
    folder = _folder()
    with (
        patch("api.routers.folders.Folder.get", new=AsyncMock(return_value=folder)),
        patch(
            "api.routers.folders.repo_query",
            new=AsyncMock(side_effect=[[{"id": "folder:f1", "name": "Work"}], []]),
        ),
        patch.object(Folder, "save", new=AsyncMock()),
    ):
        response = client.put("/api/folders/folder:f1", json={"name": "WORK"})
    assert response.status_code == 200


def test_rename_folder_duplicate_409(client):
    folder = _folder()
    rows = [{"id": "folder:f1", "name": "Work"}, {"id": "folder:f2", "name": "Play"}]
    with (
        patch("api.routers.folders.Folder.get", new=AsyncMock(return_value=folder)),
        patch("api.routers.folders.repo_query", new=AsyncMock(return_value=rows)),
    ):
        response = client.put("/api/folders/folder:f1", json={"name": "play"})
    assert response.status_code == 409


def test_rename_folder_empty_400(client):
    with patch("api.routers.folders.Folder.get", new=AsyncMock(return_value=_folder())):
        response = client.put("/api/folders/folder:f1", json={"name": " "})
    assert response.status_code == 400


def test_rename_and_delete_missing_folder_404(client):
    with patch(
        "api.routers.folders.Folder.get",
        new=AsyncMock(side_effect=NotFoundError("nope")),
    ):
        assert (
            client.put("/api/folders/folder:x", json={"name": "A"}).status_code == 404
        )
        assert client.delete("/api/folders/folder:x").status_code == 404


def test_folder_endpoints_reject_other_table_ids(client):
    # Folder.get() resolves by id prefix; a notebook id must not be deleted here.
    nb = Notebook(id="notebook:n1", name="N", description="")
    with (
        patch("api.routers.folders.Folder.get", new=AsyncMock(return_value=nb)),
        patch.object(Notebook, "delete", new=AsyncMock()) as delete,
    ):
        assert client.delete("/api/folders/notebook:n1").status_code == 404
    delete.assert_not_awaited()


def test_delete_folder_ungroups_notebooks_without_deleting_them(client):
    folder = _folder()
    query = AsyncMock(return_value=[{"id": "notebook:a"}, {"id": "notebook:b"}])
    with (
        patch("api.routers.folders.Folder.get", new=AsyncMock(return_value=folder)),
        patch("api.routers.folders.repo_query", new=query),
        patch.object(Folder, "delete", new=AsyncMock()) as delete,
        patch.object(Notebook, "delete", new=AsyncMock()) as nb_delete,
    ):
        response = client.delete("/api/folders/folder:f1")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Folder deleted successfully",
        "notebooks_ungrouped": 2,
    }
    assert query.await_args is not None
    sql = query.await_args.args[0]
    assert "UPDATE notebook SET folder = NONE" in sql
    delete.assert_awaited_once()
    nb_delete.assert_not_awaited()


# --- notebooks: folder_id ---------------------------------------------------


def _notebook(folder=None):
    return Notebook(id="notebook:n1", name="NB", description="d", folder=folder)


def _put(client, notebook, payload, folder_get=None, rows=None):
    folder_mock = folder_get or AsyncMock(return_value=_folder())
    query = AsyncMock(return_value=rows if rows is not None else [])
    with (
        patch(
            "api.routers.notebooks.Notebook.get", new=AsyncMock(return_value=notebook)
        ),
        patch("api.routers.notebooks.Folder.get", new=folder_mock),
        patch.object(Notebook, "save", new=AsyncMock()) as save,
        patch("api.routers.notebooks.repo_query", new=query),
    ):
        response = client.put("/api/notebooks/notebook:n1", json=payload)
    return response, save, query, folder_mock


def test_move_notebook_into_folder(client):
    nb = _notebook()
    row = {
        "id": "notebook:n1", "name": "NB", "description": "d", "folder": "folder:f1",
        "source_count": 0, "note_count": 0,
    }  # fmt: skip
    response, save, _, _ = _put(client, nb, {"folder_id": "folder:f1"}, rows=[row])
    assert response.status_code == 200
    assert response.json()["folder_id"] == "folder:f1"
    assert nb.folder == "folder:f1"
    save.assert_awaited_once()


@pytest.mark.parametrize("payload", [{"folder_id": None}, {"folder_id": ""}])
def test_unmove_notebook_with_null_or_empty(client, payload):
    nb = _notebook(folder="folder:f1")
    response, _, query, folder_mock = _put(client, nb, payload)
    assert response.status_code == 200
    assert nb.folder is None
    assert response.json()["folder_id"] is None
    folder_mock.assert_not_awaited()
    assert any("folder = NONE" in c.args[0] for c in query.await_args_list)


def test_omitted_folder_id_leaves_folder_unchanged(client):
    nb = _notebook(folder="folder:f1")
    response, _, query, folder_mock = _put(client, nb, {"name": "Renamed"})
    assert response.status_code == 200
    assert nb.folder == "folder:f1"
    folder_mock.assert_not_awaited()
    assert not any("folder = NONE" in c.args[0] for c in query.await_args_list)
    assert "folder" in nb._prepare_save_data()


def test_move_to_missing_folder_404(client):
    nb = _notebook()
    response, save, _, _ = _put(
        client,
        nb,
        {"folder_id": "folder:gone"},
        folder_get=AsyncMock(side_effect=NotFoundError("nope")),
    )
    assert response.status_code == 404
    save.assert_not_awaited()


def test_move_to_non_folder_id_404(client):
    nb = _notebook()
    other = _notebook()
    response, save, _, _ = _put(
        client,
        nb,
        {"folder_id": "notebook:n2"},
        folder_get=AsyncMock(return_value=other),
    )
    assert response.status_code == 404
    save.assert_not_awaited()


def test_prepare_save_data_converts_folder_to_record_id():
    from surrealdb import RecordID

    data = _notebook(folder="folder:f1")._prepare_save_data()
    assert data["folder"] == RecordID("folder", "f1")
    assert "folder" not in _notebook()._prepare_save_data()


def test_notebook_accepts_record_id_folder():
    from surrealdb import RecordID

    assert Notebook(
        name="a", description="", folder=RecordID("folder", "x")
    ).folder == ("folder:x")


def _list_rows():
    return [
        {"id": "notebook:a", "name": "a", "description": "", "folder": "folder:f1"},
        {"id": "notebook:b", "name": "b", "description": ""},
        {"id": "notebook:c", "name": "c", "description": "", "folder": "folder:f2"},
    ]


@pytest.mark.parametrize(
    "query,expected",
    [
        ("", ["notebook:a", "notebook:b", "notebook:c"]),
        ("?folder_id=folder:f1", ["notebook:a"]),
        ("?folder_id=none", ["notebook:b"]),
        ("?folder_id=folder:zzz", []),
    ],
)
def test_list_notebooks_folder_filter(client, query, expected):
    with patch(
        "api.routers.notebooks.repo_query", new=AsyncMock(return_value=_list_rows())
    ):
        response = client.get(f"/api/notebooks{query}")
    assert response.status_code == 200
    assert [n["id"] for n in response.json()] == expected
    if not query:
        assert [n["folder_id"] for n in response.json()] == [
            "folder:f1",
            None,
            "folder:f2",
        ]


def test_get_notebook_includes_folder_id(client):
    row = {"id": "notebook:a", "name": "a", "description": "", "folder": "folder:f1"}
    with patch("api.routers.notebooks.repo_query", new=AsyncMock(return_value=[row])):
        response = client.get("/api/notebooks/notebook:a")
    assert response.status_code == 200
    assert response.json()["folder_id"] == "folder:f1"


def test_create_notebook_response_has_null_folder_id(client):
    with patch.object(Notebook, "save", new=AsyncMock()):
        response = client.post("/api/notebooks", json={"name": "x"})
    assert response.status_code == 200
    assert response.json()["folder_id"] is None
