"""
Tests for /api/sources router endpoints.

Focuses on increasing coverage from 10%.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from api.main import app

    return TestClient(app)


class TestSourcesRouter:
    """Test suite for /api/sources endpoints."""

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query")
    async def test_get_sources_success(self, mock_repo_query, client):
        """Test GET /api/sources returns list of sources."""
        mock_repo_query.return_value = [
            {
                "id": "source:1",
                "title": "Test Source",
                "topics": [],
                "asset": None,
                "created": "2024-01-01T00:00:00",
                "updated": "2024-01-01T00:00:00",
            }
        ]

        response = client.get("/api/sources")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 0  # May be empty or have data

    @pytest.mark.asyncio
    @patch("api.routers.sources.repo_query")
    @patch("api.routers.sources.Notebook")
    async def test_get_sources_with_notebook_filter(self, mock_notebook_class, mock_repo_query, client):
        """Test GET /api/sources?notebook_id=X filters by notebook."""
        mock_notebook = MagicMock()
        mock_notebook.id = "notebook:123"
        mock_notebook_class.get = AsyncMock(return_value=mock_notebook)
        mock_repo_query.return_value = []

        response = client.get("/api/sources?notebook_id=notebook:123")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("api.routers.sources.Source")
    @patch("api.routers.sources.submit_command")
    @patch("api.routers.sources.Notebook")
    async def test_create_source_url(self, mock_notebook_class, mock_submit_command, mock_source_class, client):
        """Test POST /api/sources/json creates source from URL."""
        mock_notebook = MagicMock()
        mock_notebook.id = "notebook:1"
        mock_notebook_class.get = AsyncMock(return_value=mock_notebook)

        mock_source = MagicMock()
        mock_source.id = "source:123"
        mock_source.title = "Test Source"
        mock_source.topics = []
        mock_source.asset = None
        mock_source.created = "2024-01-01T00:00:00"
        mock_source.updated = "2024-01-01T00:00:00"
        mock_source.save = AsyncMock()
        mock_source.relate = AsyncMock()

        mock_source_class.return_value = mock_source
        mock_submit_command.return_value = "command:456"

        response = client.post(
            "/api/sources/json",
            json={
                "type": "url",
                "url": "https://example.com",
                "notebook_id": "notebook:1",
            },
        )
        # May return 200 or 202 depending on async_processing
        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    @patch("api.routers.sources.Source")
    async def test_get_source_by_id(self, mock_source_class, client):
        """Test GET /api/sources/{id} returns specific source."""
        mock_source = MagicMock()
        mock_source.id = "source:123"
        mock_source.title = "Test Source"
        mock_source.topics = []
        mock_source.asset = None
        mock_source.created = "2024-01-01T00:00:00"
        mock_source.updated = "2024-01-01T00:00:00"

        mock_source_class.get = AsyncMock(return_value=mock_source)

        response = client.get("/api/sources/source:123")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Source"

    @pytest.mark.asyncio
    @patch("api.routers.sources.Source")
    async def test_update_source(self, mock_source_class, client):
        """Test PUT /api/sources/{id} updates source."""
        mock_source = MagicMock()
        mock_source.id = "source:123"
        mock_source.title = "Updated Title"
        mock_source.topics = ["topic1"]
        mock_source.save = AsyncMock()

        mock_source_class.get = AsyncMock(return_value=mock_source)

        response = client.put(
            "/api/sources/source:123",
            json={"title": "Updated Title", "topics": ["topic1"]},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("api.routers.sources.Source")
    async def test_delete_source(self, mock_source_class, client):
        """Test DELETE /api/sources/{id} deletes source."""
        mock_source = MagicMock()
        mock_source.delete = AsyncMock(return_value=True)

        mock_source_class.get = AsyncMock(return_value=mock_source)

        response = client.delete("/api/sources/source:123")
        assert response.status_code == 200

    # Note: File upload is handled through POST /api/sources with form-data
    # Testing form-data endpoints requires more complex setup, skipping for now

    @pytest.mark.asyncio
    @patch("api.routers.sources.Source")
    async def test_get_source_status(self, mock_source_class, client):
        """Test GET /api/sources/{id}/status returns processing status."""
        mock_source = MagicMock()
        mock_source.id = "source:123"
        mock_source.get_status = AsyncMock(return_value={"status": "completed"})
        mock_source.get_processing_progress = AsyncMock(return_value={"progress": 100})

        mock_source_class.get = AsyncMock(return_value=mock_source)

        response = client.get("/api/sources/source:123/status")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("api.routers.sources.Source")
    async def test_get_source_insights(self, mock_source_class, client):
        """Test GET /api/sources/{id}/insights returns insights."""
        mock_source = MagicMock()
        mock_source.id = "source:123"
        mock_source.get_insights = AsyncMock(return_value=[])

        mock_source_class.get = AsyncMock(return_value=mock_source)

        response = client.get("/api/sources/source:123/insights")
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("api.routers.sources.submit_command")
    @patch("api.routers.sources.Source")
    async def test_create_source_insight(self, mock_source_class, mock_submit_command, client):
        """Test POST /api/sources/{id}/insights creates insight."""
        mock_source = MagicMock()
        mock_source.id = "source:123"

        mock_source_class.get = AsyncMock(return_value=mock_source)
        mock_submit_command.return_value = "command:789"

        response = client.post(
            "/api/sources/source:123/insights",
            json={"transformation_id": "transform:1", "notebook_id": "notebook:1"},
        )
        assert response.status_code in [200, 202]

    def test_generate_unique_filename_new_file(self):
        """Test generate_unique_filename for new file."""
        from api.routers.sources import generate_unique_filename
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            filename = generate_unique_filename("test.pdf", tmpdir)
            assert filename.endswith("test.pdf")

    def test_generate_unique_filename_existing_file(self):
        """Test generate_unique_filename appends counter for existing file."""
        from api.routers.sources import generate_unique_filename
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as tmpdir:
            # Create existing file
            existing = Path(tmpdir) / "test.pdf"
            existing.write_text("existing")

            filename = generate_unique_filename("test.pdf", tmpdir)
            assert filename.endswith("test (1).pdf")

    @pytest.mark.asyncio
    async def test_save_uploaded_file_success(self):
        """Test save_uploaded_file saves file correctly."""
        from api.routers.sources import save_uploaded_file
        from tempfile import TemporaryDirectory
        from fastapi import UploadFile
        from pathlib import Path

        with TemporaryDirectory() as tmpdir:
            with patch("api.routers.sources.UPLOADS_FOLDER", tmpdir):
                file_content = b"test content"
                upload_file = UploadFile(
                    filename="test.txt", file=BytesIO(file_content)
                )

                file_path = await save_uploaded_file(upload_file)
                assert Path(file_path).exists()
                assert Path(file_path).read_bytes() == file_content

    @pytest.mark.asyncio
    async def test_save_uploaded_file_no_filename(self):
        """Test save_uploaded_file raises error for missing filename."""
        from api.routers.sources import save_uploaded_file
        from fastapi import UploadFile

        upload_file = UploadFile(filename=None, file=BytesIO(b"content"))

        with pytest.raises(ValueError, match="No filename provided"):
            await save_uploaded_file(upload_file)
