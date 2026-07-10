"""
Tests for the unsupported-file-type handling (#975).

Uploading a file content-core can't process (e.g. .odt) used to be
accepted silently, then burn process_source's 15 exponential-backoff
retries (~1 hour) before failing with a generic "Source processing
failed" and no log line. Three fixes, each locked in here:

1. create_source() rejects unsupported files at upload time with a 400
   by running content-core's own identification + routing
   (ensure_file_type_supported) - deliberately NOT an extension
   allowlist, so files content-core does handle (e.g. extensionless
   plain text) keep working.
2. content_process() re-raises UnsupportedTypeException as ValueError,
   which is in the command's stop_on list - the job fails on attempt 1
   instead of retrying a deterministic error.
3. get_source_status() surfaces the stored error_message for failed
   jobs instead of a generic message.
"""

import zipfile
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.routers.sources import ensure_file_type_supported
from open_notebook.exceptions import InvalidInputError


def make_fake_odt(path):
    """Minimal OpenDocument text file: a ZIP that isn't DOCX/XLSX/PPTX/EPUB."""
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        z.writestr("META-INF/manifest.xml", "<manifest/>")
        z.writestr("content.xml", "<office:document-content/>")


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestEnsureFileTypeSupported:
    @pytest.mark.asyncio
    async def test_odt_file_is_rejected(self, tmp_path):
        odt = tmp_path / "document.odt"
        make_fake_odt(odt)

        with pytest.raises(InvalidInputError, match=r"Unsupported file type: \.odt"):
            await ensure_file_type_supported(str(odt))

    @pytest.mark.asyncio
    async def test_plain_text_file_is_accepted(self, tmp_path):
        txt = tmp_path / "notes.txt"
        txt.write_text("Just some plain text content for testing purposes.")

        await ensure_file_type_supported(str(txt))

    @pytest.mark.asyncio
    async def test_extensionless_text_file_is_accepted(self, tmp_path):
        # The reason this isn't an extension allowlist: content-core
        # detects plain text by content and processes it fine.
        no_ext = tmp_path / "README"
        no_ext.write_text("Readable prose without any file extension at all.")

        await ensure_file_type_supported(str(no_ext))

    @pytest.mark.asyncio
    async def test_pdf_file_is_accepted(self, tmp_path):
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4 minimal header is enough for identification")

        await ensure_file_type_supported(str(pdf))

    @pytest.mark.asyncio
    async def test_fails_open_when_file_unreadable(self, tmp_path):
        # A pre-validation hiccup must not block the upload - the worker
        # remains the authority and would surface the failure instead.
        await ensure_file_type_supported(str(tmp_path / "does-not-exist.txt"))


class TestCreateSourceRejectsUnsupportedUpload:
    def test_odt_upload_returns_400_and_cleans_up_file(
        self, client, tmp_path, monkeypatch
    ):
        uploads = tmp_path / "uploads"
        uploads.mkdir()
        monkeypatch.setattr("api.routers.sources.UPLOADS_FOLDER", str(uploads))

        odt = tmp_path / "document.odt"
        make_fake_odt(odt)

        with patch(
            "api.routers.sources.Notebook.get",
            new=AsyncMock(return_value=MagicMock()),
        ):
            response = client.post(
                "/api/sources",
                data={
                    "type": "upload",
                    "notebooks": '["notebook:test123"]',
                    "async_processing": "true",
                },
                files={"file": ("document.odt", odt.read_bytes())},
            )

        assert response.status_code == 400
        assert "Unsupported file type: .odt" in response.json()["detail"]
        # The saved upload must not be left behind after rejection
        assert list(uploads.iterdir()) == []


class TestContentProcessDoesNotRetryUnsupportedTypes:
    @pytest.mark.asyncio
    async def test_unsupported_type_exception_becomes_value_error(self):
        from content_core.common import UnsupportedTypeException

        from open_notebook.graphs.source import content_process

        mock_manager = MagicMock()
        mock_manager.get_defaults = AsyncMock(side_effect=Exception("no db in test"))

        with (
            patch(
                "open_notebook.graphs.source.extract_content",
                new=AsyncMock(
                    side_effect=UnsupportedTypeException(
                        "Unsupported file type: application/zip"
                    )
                ),
            ),
            patch(
                "open_notebook.graphs.source.ModelManager",
                return_value=mock_manager,
            ),
        ):
            # ValueError is in process_source's stop_on list; anything else
            # would be retried 15 times with exponential backoff
            state: Any = {
                "content_state": {"file_path": "/tmp/document.odt"},
                "apply_transformations": [],
                "source_id": "source:test123",
                "notebook_ids": [],
                "transformation": [],
                "embed": False,
            }
            with pytest.raises(
                ValueError, match="Unsupported file type: application/zip"
            ):
                await content_process(state)


class TestSourceStatusSurfacesFailureReason:
    def _get_status(self, client, progress):
        from open_notebook.domain.notebook import Source

        source = Source(
            id="source:test123",
            title="Test Source",
            topics=[],
            command="command:test123",
        )

        with (
            patch(
                "api.routers.sources.Source.get",
                new=AsyncMock(return_value=source),
            ),
            patch.object(Source, "get_status", new=AsyncMock(return_value="failed")),
            patch.object(
                Source,
                "get_processing_progress",
                new=AsyncMock(return_value=progress),
            ),
        ):
            return client.get("/api/sources/source:test123/status")

    def test_failed_status_includes_error_message(self, client):
        response = self._get_status(
            client,
            {"status": "failed", "error": "Unsupported file type: application/zip"},
        )

        assert response.status_code == 200
        assert (
            response.json()["message"]
            == "Source processing failed: Unsupported file type: application/zip"
        )

    def test_failed_status_without_error_keeps_generic_message(self, client):
        response = self._get_status(client, {"status": "failed", "error": None})

        assert response.status_code == 200
        assert response.json()["message"] == "Source processing failed"
