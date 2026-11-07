"""
Source input checks (uploads-directory containment, URL validation) run in the
source graph itself, so they apply to every caller, and the unused generic
command-submission endpoint is gone.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.graphs import source as source_graph
from open_notebook.graphs.source import content_process, validate_content_state


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    root = tmp_path / "uploads"
    root.mkdir()
    monkeypatch.setattr(source_graph, "UPLOADS_FOLDER", str(root))
    return root


class TestGenericCommandSubmissionRemoved:
    def test_post_commands_jobs_is_not_routable(self, client):
        response = client.post(
            "/api/commands/jobs",
            json={"command": "process_source", "app": "open_notebook", "input": {}},
        )
        assert response.status_code == 405

    def test_job_status_endpoint_still_available(self, client):
        with patch(
            "api.routers.commands.CommandService.get_command_status",
            new=AsyncMock(return_value={"job_id": "command:abc", "status": "queued"}),
        ):
            response = client.get("/api/commands/jobs/command:abc")
        assert response.status_code == 200


class TestValidateContentState:
    @pytest.mark.asyncio
    async def test_rejects_file_outside_uploads(self, uploads):
        with pytest.raises(ValueError, match="uploads directory"):
            await validate_content_state({"file_path": "/etc/passwd"})

    @pytest.mark.asyncio
    async def test_rejects_traversal_out_of_uploads(self, uploads):
        with pytest.raises(ValueError, match="uploads directory"):
            await validate_content_state(
                {"file_path": str(uploads / ".." / "secret.txt")}
            )

    @pytest.mark.asyncio
    async def test_rejects_sibling_directory_with_matching_prefix(
        self, uploads, tmp_path
    ):
        sibling = tmp_path / "uploads_evil"
        sibling.mkdir()
        with pytest.raises(ValueError, match="uploads directory"):
            await validate_content_state({"file_path": str(sibling / "x.txt")})

    @pytest.mark.asyncio
    async def test_accepts_file_inside_uploads(self, uploads):
        await validate_content_state({"file_path": str(uploads / "doc.pdf")})

    @pytest.mark.asyncio
    async def test_rejects_link_local_url(self, uploads):
        with pytest.raises(ValueError, match="Link-local"):
            await validate_content_state(
                {"url": "http://169.254.169.254/latest/meta-data/"}
            )

    @pytest.mark.asyncio
    async def test_accepts_plain_content(self, uploads):
        await validate_content_state({"content": "hello"})


class TestContentProcessEnforcesGuards:
    @pytest.mark.asyncio
    async def test_file_outside_uploads_is_rejected_before_extraction(self, uploads):
        extract = AsyncMock()
        with (
            patch.object(source_graph, "extract_content", extract),
            patch.object(source_graph.os, "unlink") as unlink,
        ):
            with pytest.raises(ValueError, match="uploads directory"):
                await content_process(
                    {  # type: ignore[typeddict-item]
                        "content_state": {
                            "file_path": "/etc/passwd",
                            "delete_source": True,
                        }
                    }
                )
        extract.assert_not_called()
        unlink.assert_not_called()

    @pytest.mark.asyncio
    async def test_link_local_url_is_rejected_before_extraction(self, uploads):
        extract = AsyncMock()
        with patch.object(source_graph, "extract_content", extract):
            with pytest.raises(ValueError, match="Link-local"):
                await content_process(
                    {  # type: ignore[typeddict-item]
                        "content_state": {"url": "http://169.254.169.254/"}
                    }
                )
        extract.assert_not_called()
