"""
Regression tests documenting why the "no file type/content allowlist on
uploads" finding is low-risk without adding one.

Investigated adding an extension/MIME allowlist and decided against it:
- Downloads are always served as application/octet-stream regardless of
  the uploaded file's actual type (locked in below) - the classic "upload
  HTML/SVG, victim opens it, browser renders/executes it" vector is closed
  independent of any allowlist.
- Uploaded files are never executed server-side; content-core only reads
  and extracts text/media from them.
- content_core.content.identification.file_detector.FileDetector already
  does its own content-sniffing (magic bytes, not just extension) and
  raises UnsupportedTypeException for content it can't classify -
  duplicating that as a hand-maintained extension allowlist at the API
  layer would drift out of sync with content-core's 50+ supported types
  and either give false confidence or block legitimate uploads.
- Upload size is already bounded (see api/middleware.py).

So arbitrary bytes can still be written to disk under a
server-controlled filename (a generically accepted property of file
upload services), but not served in a way a browser would render/execute,
and not executed server-side either.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.domain.notebook import Asset, Source


def make_source(file_path, **overrides):
    defaults = dict(id="source:test123", title="Test Source", asset=Asset(file_path=file_path))
    defaults.update(overrides)
    return Source(**defaults)


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestDownloadsAlwaysServedAsOctetStream:
    def test_html_file_download_is_octet_stream_not_text_html(self, client, tmp_path, monkeypatch):
        """Even if an attacker got an .html file stored, downloading it
        must never come back as text/html (which a browser would render)."""
        real_root = tmp_path / "uploads"
        real_root.mkdir()
        monkeypatch.setattr("api.routers.sources.UPLOADS_FOLDER", str(real_root))

        malicious_html = real_root / "innocuous.html"
        malicious_html.write_text("<script>alert(document.cookie)</script>")

        source = make_source(file_path=str(malicious_html))
        with patch("api.routers.sources.Source.get", new=AsyncMock(return_value=source)):
            response = client.get("/api/sources/source:test123/download")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"

    def test_svg_file_download_is_octet_stream_not_svg_xml(self, client, tmp_path, monkeypatch):
        real_root = tmp_path / "uploads"
        real_root.mkdir()
        monkeypatch.setattr("api.routers.sources.UPLOADS_FOLDER", str(real_root))

        malicious_svg = real_root / "image.svg"
        malicious_svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        )

        source = make_source(file_path=str(malicious_svg))
        with patch("api.routers.sources.Source.get", new=AsyncMock(return_value=source)):
            response = client.get("/api/sources/source:test123/download")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"


class TestContentCoreRejectsUnrecognizedContent:
    @pytest.mark.asyncio
    async def test_file_detector_raises_for_unrecognized_content(self, tmp_path):
        from content_core.common.exceptions import UnsupportedTypeException
        from content_core.content.identification.file_detector import FileDetector

        garbage = tmp_path / "garbage.bin"
        garbage.write_bytes(bytes(range(256)) * 4)  # not any recognized signature/text pattern

        detector = FileDetector()
        with pytest.raises(UnsupportedTypeException):
            await detector.detect(str(garbage))
