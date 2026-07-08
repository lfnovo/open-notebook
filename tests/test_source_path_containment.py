"""
Tests for the sources.py path-containment fix in _resolve_source_file() and
_is_source_file_available() (api/routers/sources.py).

Both compared `resolved_path.startswith(safe_root)` without a trailing
separator - a sibling directory that merely starts with the same string
(e.g. "uploads_evil/") would incorrectly be treated as contained, unlike
the file's other two path checks (generate_unique_filename(), the inline
check in create_source()) which already guard with `+ os.sep`. Not
reachable today (source.asset.file_path is only ever set server-side), but
these lock in the fix and guard against regressions.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.routers.sources import _is_source_file_available, _resolve_source_file
from open_notebook.config import UPLOADS_FOLDER
from open_notebook.domain.notebook import Asset, Source


def make_source(file_path=None, **overrides):
    defaults = dict(
        id="source:test123",
        title="Test Source",
        asset=Asset(file_path=file_path) if file_path else None,
    )
    defaults.update(overrides)
    return Source(**defaults)


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestIsSourceFileAvailableRejectsSiblingDirectoryBypass:
    def test_sibling_directory_with_matching_prefix_is_not_available(
        self, tmp_path, monkeypatch
    ):
        real_root = tmp_path / "uploads"
        real_root.mkdir()
        monkeypatch.setattr("api.routers.sources.UPLOADS_FOLDER", str(real_root))

        sibling = tmp_path / "uploads_evil"
        sibling.mkdir()
        evil_file = sibling / "secret.txt"
        evil_file.write_bytes(b"not yours")

        source = make_source(file_path=str(evil_file))
        assert _is_source_file_available(source) is False

    def test_file_genuinely_inside_uploads_folder_is_available(
        self, tmp_path, monkeypatch
    ):
        real_root = tmp_path / "uploads"
        real_root.mkdir()
        monkeypatch.setattr("api.routers.sources.UPLOADS_FOLDER", str(real_root))

        legit_file = real_root / "document.pdf"
        legit_file.write_bytes(b"pdf bytes")

        source = make_source(file_path=str(legit_file))
        assert _is_source_file_available(source) is True

    def test_missing_file_inside_uploads_folder_is_unavailable_not_error(
        self, tmp_path, monkeypatch
    ):
        real_root = tmp_path / "uploads"
        real_root.mkdir()
        monkeypatch.setattr("api.routers.sources.UPLOADS_FOLDER", str(real_root))

        missing_file = real_root / "does-not-exist.pdf"
        source = make_source(file_path=str(missing_file))
        assert _is_source_file_available(source) is False

    def test_no_asset_returns_none(self):
        source = make_source(file_path=None)
        assert _is_source_file_available(source) is None

    def test_path_traversal_outside_root_is_not_available(self, tmp_path, monkeypatch):
        root = tmp_path / "uploads"
        root.mkdir()
        monkeypatch.setattr("api.routers.sources.UPLOADS_FOLDER", str(root))

        outside = tmp_path / "outside.pdf"
        outside.write_bytes(b"not yours")
        traversal_path = str(root / ".." / "outside.pdf")

        source = make_source(file_path=traversal_path)
        assert _is_source_file_available(source) is False


class TestResolveSourceFileRejectsSiblingDirectoryBypass:
    @pytest.mark.asyncio
    async def test_sibling_directory_raises_403(self, tmp_path, monkeypatch):
        real_root = tmp_path / "uploads"
        real_root.mkdir()
        monkeypatch.setattr("api.routers.sources.UPLOADS_FOLDER", str(real_root))

        sibling = tmp_path / "uploads_evil"
        sibling.mkdir()
        evil_file = sibling / "secret.txt"
        evil_file.write_bytes(b"not yours")

        source = make_source(file_path=str(evil_file))
        with patch(
            "api.routers.sources.Source.get", new=AsyncMock(return_value=source)
        ):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await _resolve_source_file("source:test123")
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_file_genuinely_inside_uploads_folder_resolves(
        self, tmp_path, monkeypatch
    ):
        real_root = tmp_path / "uploads"
        real_root.mkdir()
        monkeypatch.setattr("api.routers.sources.UPLOADS_FOLDER", str(real_root))

        legit_file = real_root / "document.pdf"
        legit_file.write_bytes(b"pdf bytes")

        source = make_source(file_path=str(legit_file))
        with patch(
            "api.routers.sources.Source.get", new=AsyncMock(return_value=source)
        ):
            resolved_path, filename = await _resolve_source_file("source:test123")

        assert filename == "document.pdf"
        assert resolved_path == str(legit_file.resolve())


class TestDownloadEndpointRejectsSiblingDirectoryBypass:
    """End-to-end through the actual HTTP endpoint."""

    def test_download_returns_403_for_sibling_directory_file(
        self, client, tmp_path, monkeypatch
    ):
        real_root = tmp_path / "uploads"
        real_root.mkdir()
        monkeypatch.setattr("api.routers.sources.UPLOADS_FOLDER", str(real_root))

        sibling = tmp_path / "uploads_evil"
        sibling.mkdir()
        evil_file = sibling / "secret.txt"
        evil_file.write_bytes(b"not yours")

        source = make_source(file_path=str(evil_file))
        with patch(
            "api.routers.sources.Source.get", new=AsyncMock(return_value=source)
        ):
            response = client.get("/api/sources/source:test123/download")

        assert response.status_code == 403


class TestRealUploadsFolderStillWorks:
    """Sanity check against the real (non-monkeypatched) UPLOADS_FOLDER."""

    def test_real_uploads_folder_file_is_available(self):
        from pathlib import Path

        test_file = Path(UPLOADS_FOLDER) / "containment_test_file.txt"
        test_file.write_bytes(b"test")
        try:
            source = make_source(file_path=str(test_file))
            assert _is_source_file_available(source) is True
        finally:
            test_file.unlink(missing_ok=True)
