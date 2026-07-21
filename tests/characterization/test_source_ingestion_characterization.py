"""Characterization: source ingestion via file upload and via URL.

Captures the CURRENT behavior of POST /api/sources as of `upstream-base`.
See ./README.md before changing anything here.

The two ingestion modes that matter for the commercialization work are:
  - `type=link`  — a URL, guarded by the SSRF check
  - `type=upload` — a multipart file, guarded by the LFI/uploads-root check
plus `type=text` for completeness, since it shares the same pipeline.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.domain.notebook import Source


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


@pytest.fixture
def saved_sources():
    """Patch Source.save so ingestion never touches a real database."""
    captured = []

    async def capture_save(self_source):
        captured.append(self_source)
        if not self_source.id:
            self_source.id = "source:generated"

    with patch.object(Source, "save", autospec=True, side_effect=capture_save):
        yield captured


class TestUrlIngestion:
    """type=link — the URL path."""

    @patch("api.routers.sources.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.add_to_notebook", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_async_url_ingestion_queues_a_job_and_returns_status_new(
        self, mock_nb_get, mock_add_nb, mock_submit, client, saved_sources
    ):
        mock_nb_get.return_value = MagicMock()
        mock_submit.return_value = "command:job1"

        response = client.post(
            "/api/sources",
            data={
                "type": "link",
                "url": "https://example.com/article",
                "notebooks": '["notebook:1"]',
                "async_processing": "true",
            },
        )

        assert response.status_code == 200
        body = response.json()
        # Async ingestion returns immediately with a placeholder, before any
        # content has been fetched or extracted.
        assert body["status"] == "new"
        assert body["command_id"] == "command:job1"
        assert body["processing_info"] == {"async": True, "queued": True}
        assert body["full_text"] is None
        assert body["embedded"] is False
        assert body["embedded_chunks"] == 0

        # The URL is persisted on the source's asset before the job is queued,
        # so a failed job can still be retried.
        assert saved_sources[0].asset.url == "https://example.com/article"
        # Default placeholder title until extraction names it.
        assert saved_sources[0].title == "Processing..."

        # The job carries the url through as content_state.
        submitted = mock_submit.await_args.args
        assert submitted[1] == "process_source"
        assert submitted[2]["content_state"] == {"url": "https://example.com/article"}
        assert submitted[2]["notebook_ids"] == ["notebook:1"]
        # embed defaults to False.
        assert submitted[2]["embed"] is False

    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_link_without_url_returns_400(self, mock_nb_get, client):
        mock_nb_get.return_value = MagicMock()
        response = client.post(
            "/api/sources", data={"type": "link", "async_processing": "true"}
        )
        assert response.status_code == 400
        assert "URL is required" in response.json()["detail"]

    @patch("api.routers.sources.validate_url", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_ssrf_rejected_url_returns_400(self, mock_nb_get, mock_validate, client):
        """Every user-supplied URL goes through validate_url; a ValueError from
        it becomes a 400, not a 500."""
        mock_nb_get.return_value = MagicMock()
        mock_validate.side_effect = ValueError("URL points to a private address")

        response = client.post(
            "/api/sources",
            data={
                "type": "link",
                "url": "http://169.254.169.254/latest/meta-data/",
                "async_processing": "true",
            },
        )

        assert response.status_code == 400
        assert "private address" in response.json()["detail"]

    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_missing_notebook_returns_404(self, mock_nb_get, client):
        mock_nb_get.return_value = None
        response = client.post(
            "/api/sources",
            data={
                "type": "link",
                "url": "https://example.com",
                "notebooks": '["notebook:ghost"]',
                "async_processing": "true",
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestFileUploadIngestion:
    """type=upload — the multipart file path."""

    @patch("api.routers.sources.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources._assert_file_supported", new_callable=AsyncMock)
    @patch("api.routers.sources.save_uploaded_file", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.add_to_notebook", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_async_file_upload_persists_path_and_queues_job(
        self,
        mock_nb_get,
        mock_add_nb,
        mock_save_file,
        mock_supported,
        mock_submit,
        client,
        saved_sources,
        tmp_path,
    ):
        # save_uploaded_file returns a path inside the uploads root; the LFI
        # guard compares against that root, so point the router's root at tmp.
        uploads_root = tmp_path / "uploads"
        uploads_root.mkdir()
        stored = uploads_root / "document.pdf"
        stored.write_bytes(b"%PDF-1.4 fake")

        mock_nb_get.return_value = MagicMock()
        mock_save_file.return_value = str(stored)
        mock_submit.return_value = "command:job2"

        with patch("api.routers.sources.UPLOADS_FOLDER", str(uploads_root)):
            response = client.post(
                "/api/sources",
                data={"type": "upload", "async_processing": "true"},
                files={"file": ("document.pdf", b"%PDF-1.4 fake", "application/pdf")},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "new"
        assert body["command_id"] == "command:job2"

        # The stored path is persisted on the asset before queueing.
        assert saved_sources[0].asset.file_path == str(stored)

        submitted = mock_submit.await_args.args
        assert submitted[2]["content_state"]["file_path"] == str(stored)
        # delete_source defaults to False — the upload is kept after processing.
        assert submitted[2]["content_state"]["delete_source"] is False

    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_upload_without_file_or_path_returns_400(self, mock_nb_get, client):
        mock_nb_get.return_value = MagicMock()
        response = client.post(
            "/api/sources", data={"type": "upload", "async_processing": "true"}
        )
        assert response.status_code == 400
        assert "required for upload type" in response.json()["detail"]

    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_multipart_form_ignores_a_caller_supplied_file_path(
        self, mock_nb_get, client, tmp_path
    ):
        """The multipart form has NO file_path field: `parse_source_form_data`
        hard-codes `file_path=None`. A caller-supplied one is silently dropped,
        so the request fails as "no file" rather than reaching the LFI guard.

        This means the LFI guard below is only reachable via /api/sources/json.
        """
        outsider = tmp_path / "secrets.env"
        outsider.write_text("SECRET=1")

        mock_nb_get.return_value = MagicMock()

        response = client.post(
            "/api/sources",
            data={
                "type": "upload",
                "file_path": str(outsider),
                "async_processing": "true",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "File upload or file_path is required for upload type"
        )

    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_json_endpoint_rejects_file_path_outside_uploads_root(
        self, mock_nb_get, client, tmp_path
    ):
        """LFI guard: a file_path outside the uploads directory is rejected
        before any processing is queued. Reachable via the JSON endpoint, which
        (unlike the multipart form) does accept file_path."""
        uploads_root = tmp_path / "uploads"
        uploads_root.mkdir()
        outsider = tmp_path / "secrets.env"
        outsider.write_text("SECRET=1")

        mock_nb_get.return_value = MagicMock()

        with patch("api.routers.sources.UPLOADS_FOLDER", str(uploads_root)):
            response = client.post(
                "/api/sources/json",
                json={
                    "type": "upload",
                    "file_path": str(outsider),
                    "async_processing": True,
                },
            )

        assert response.status_code == 400
        assert "must be within the uploads directory" in response.json()["detail"]


class TestTextIngestion:
    """type=text — no fetch, no extraction, content passed straight through."""

    @patch("api.routers.sources.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.add_to_notebook", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_text_source_passes_content_through(
        self, mock_nb_get, mock_add_nb, mock_submit, client, saved_sources
    ):
        mock_nb_get.return_value = MagicMock()
        mock_submit.return_value = "command:job3"

        response = client.post(
            "/api/sources",
            data={
                "type": "text",
                "content": "some pasted text",
                "async_processing": "true",
            },
        )

        assert response.status_code == 200
        submitted = mock_submit.await_args.args
        assert submitted[2]["content_state"] == {"content": "some pasted text"}
        # No asset is created for text sources.
        assert saved_sources[0].asset is None

    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_text_without_content_returns_400(self, mock_nb_get, client):
        mock_nb_get.return_value = MagicMock()
        response = client.post(
            "/api/sources", data={"type": "text", "async_processing": "true"}
        )
        assert response.status_code == 400
        assert "Content is required" in response.json()["detail"]


class TestUnknownType:
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_unsupported_type_returns_400(self, mock_nb_get, client):
        mock_nb_get.return_value = MagicMock()
        response = client.post(
            "/api/sources", data={"type": "carrier-pigeon", "async_processing": "true"}
        )
        assert response.status_code == 400


class TestJobSubmissionFailureCleansUp:
    @patch("api.routers.sources.CommandService.submit_command_job", new_callable=AsyncMock)
    @patch("api.routers.sources.Source.add_to_notebook", new_callable=AsyncMock)
    @patch("api.routers.sources.Notebook.get", new_callable=AsyncMock)
    def test_failed_submission_deletes_the_source_record_and_returns_500(
        self, mock_nb_get, mock_add_nb, mock_submit, client
    ):
        """If queueing the job fails, the half-created source is deleted so no
        orphan row is left behind."""
        mock_nb_get.return_value = MagicMock()
        mock_submit.side_effect = RuntimeError("queue is down")

        deleted = []

        async def capture_save(self_source):
            self_source.id = "source:orphan"

        async def capture_delete(self_source):
            deleted.append(self_source.id)
            return True

        with (
            patch.object(Source, "save", autospec=True, side_effect=capture_save),
            patch.object(Source, "delete", autospec=True, side_effect=capture_delete),
        ):
            response = client.post(
                "/api/sources",
                data={
                    "type": "text",
                    "content": "x",
                    "async_processing": "true",
                },
            )

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to queue processing"
        assert deleted == ["source:orphan"]
