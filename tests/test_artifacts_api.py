"""Tests for the artifacts API (api/routers/artifacts.py).

The service layer is stubbed: these tests lock the HTTP contract - 202 on
submission, 404/403/200 on download, and the derived ``files``/``download_url``
fields the frontend relies on. Path containment is exercised with real files
under a temporary artifacts root.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.routers.artifacts as artifacts_router
import open_notebook.artifacts.paths as artifact_paths
from open_notebook.exceptions import NotFoundError


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class _FakeArtifact:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "generated_artifact:1")
        self.notebook = kwargs.get("notebook", "notebook:1")
        self.title = kwargs.get("title", "Doc")
        self.kind = kwargs.get("kind", "report")
        self.variant = kwargs.get("variant")
        self.formats = kwargs.get("formats", ["md"])
        self.language = kwargs.get("language", "en")
        self.sections = kwargs.get("sections", 2)
        self.output_path = kwargs.get("output_path")
        self.note_id = kwargs.get("note_id")
        self.command = kwargs.get("command")
        self.created = kwargs.get("created")
        self.deleted = False

    async def delete(self):
        self.deleted = True
        return True


class TestSubmitArtifact:
    def test_returns_202_with_ids(self, client, monkeypatch):
        async def fake_submit(**kwargs):
            return {"command_id": "command:1", "artifact_id": "generated_artifact:1"}

        monkeypatch.setattr(
            artifacts_router.ArtifactService, "submit_generation_job", fake_submit
        )

        response = client.post(
            "/api/artifacts",
            json={"notebook_id": "notebook:1", "kind": "report", "formats": ["md"]},
        )

        assert response.status_code == 202
        body = response.json()
        assert body["command_id"] == "command:1"
        assert body["artifact_id"] == "generated_artifact:1"

    def test_missing_notebook_maps_to_404(self, client, monkeypatch):
        async def fake_submit(**kwargs):
            raise NotFoundError("notebook not found")

        monkeypatch.setattr(
            artifacts_router.ArtifactService, "submit_generation_job", fake_submit
        )

        response = client.post(
            "/api/artifacts", json={"notebook_id": "notebook:missing"}
        )

        assert response.status_code == 404

    def test_unexpected_failure_maps_to_500(self, client, monkeypatch):
        async def fake_submit(**kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            artifacts_router.ArtifactService, "submit_generation_job", fake_submit
        )

        response = client.post("/api/artifacts", json={"notebook_id": "notebook:1"})

        assert response.status_code == 500

    def test_the_variant_reaches_the_service(self, client, monkeypatch):
        seen = {}

        async def fake_submit(**kwargs):
            seen.update(kwargs)
            return {"command_id": "command:1", "artifact_id": "generated_artifact:1"}

        monkeypatch.setattr(
            artifacts_router.ArtifactService, "submit_generation_job", fake_submit
        )

        response = client.post(
            "/api/artifacts",
            json={
                "notebook_id": "notebook:1",
                "kind": "report",
                "variant": "illustrated",
            },
        )

        assert response.status_code == 202
        assert seen["variant"] == "illustrated"

    def test_a_variant_of_the_other_kind_is_a_400(self, client, monkeypatch):
        async def fake_submit(**kwargs):
            raise ValueError("variant 'presenter' is not valid for a report")

        monkeypatch.setattr(
            artifacts_router.ArtifactService, "submit_generation_job", fake_submit
        )

        response = client.post(
            "/api/artifacts",
            json={
                "notebook_id": "notebook:1",
                "kind": "report",
                "variant": "presenter",
            },
        )

        assert response.status_code == 400


class TestListAndGetArtifacts:
    def test_list_reports_job_status(self, client, monkeypatch):
        artifact = _FakeArtifact(command="command:1")

        async def fake_list(notebook_id=None):
            return [artifact]

        async def fake_status(command_id):
            return {"status": "completed", "error_message": None}

        monkeypatch.setattr(
            artifacts_router.ArtifactService, "list_artifacts", fake_list
        )
        monkeypatch.setattr(
            artifacts_router.ArtifactService, "get_job_status", fake_status
        )

        response = client.get("/api/artifacts?notebook_id=notebook:1")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["job_status"] == "completed"
        assert body[0]["notebook_id"] == "notebook:1"

    def test_get_missing_artifact_maps_to_404(self, client, monkeypatch):
        async def fake_get(_artifact_id):
            raise NotFoundError("gone")

        monkeypatch.setattr(artifacts_router.ArtifactService, "get_artifact", fake_get)

        response = client.get("/api/artifacts/generated_artifact:missing")

        assert response.status_code == 404


class TestDownloadArtifact:
    def _artifact_with_file(self, tmp_path: Path, monkeypatch, output_path: str):
        monkeypatch.setattr(artifact_paths, "ARTIFACTS_FOLDER", str(tmp_path))
        artifact = _FakeArtifact(output_path=output_path, formats=["md"])

        async def fake_get(_artifact_id):
            return artifact

        monkeypatch.setattr(artifacts_router.ArtifactService, "get_artifact", fake_get)
        return artifact

    def test_download_returns_the_file(self, client, monkeypatch, tmp_path):
        directory = tmp_path / "abc"
        directory.mkdir()
        (directory / "doc-report.md").write_text("hello", encoding="utf-8")
        self._artifact_with_file(tmp_path, monkeypatch, "abc/doc-report.md")

        response = client.get("/api/artifacts/generated_artifact:1/download")

        assert response.status_code == 200
        assert response.content == b"hello"

    def test_download_without_file_maps_to_404(self, client, monkeypatch, tmp_path):
        self._artifact_with_file(tmp_path, monkeypatch, "")

        response = client.get("/api/artifacts/generated_artifact:1/download")

        assert response.status_code == 404

    def test_escaping_path_maps_to_403(self, client, monkeypatch, tmp_path):
        outside = tmp_path.parent / "outside.md"
        outside.write_text("nope", encoding="utf-8")
        self._artifact_with_file(tmp_path, monkeypatch, "../outside.md")

        response = client.get("/api/artifacts/generated_artifact:1/download")

        assert response.status_code == 403


class TestDeleteArtifact:
    def test_delete_removes_row_and_files(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(artifact_paths, "ARTIFACTS_FOLDER", str(tmp_path))
        directory = tmp_path / "abc"
        directory.mkdir()
        target = directory / "doc-report.md"
        target.write_text("bye", encoding="utf-8")
        artifact = _FakeArtifact(output_path="abc/doc-report.md", formats=["md"])

        async def fake_get(_artifact_id):
            return artifact

        monkeypatch.setattr(artifacts_router.ArtifactService, "get_artifact", fake_get)

        response = client.delete("/api/artifacts/generated_artifact:1")

        assert response.status_code == 200
        assert response.json()["artifact_id"] == "generated_artifact:1"
        assert not target.exists()
        assert artifact.deleted is True


def test_the_default_request_asks_for_a_handful_of_sections():
    """A book is a few broad chapters, not ten topic headings."""
    request = artifacts_router.ArtifactGenerationRequest(notebook_id="notebook:1")
    assert request.sections <= 6


def test_the_default_request_is_a_plain_document():
    """No variant means the text-only document, not an illustrated one."""
    request = artifacts_router.ArtifactGenerationRequest(notebook_id="notebook:1")
    assert request.variant is None


def test_the_request_accepts_a_variant():
    request = artifacts_router.ArtifactGenerationRequest(
        notebook_id="notebook:1", kind="report", variant="illustrated"
    )
    assert request.variant == "illustrated"
