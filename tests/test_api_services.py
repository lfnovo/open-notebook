"""
Tests for API service layer modules.

These tests focus on the service layer that wraps API client calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.chat_service import ChatService
from api.notebook_service import NotebookService
from api.sources_service import SourceProcessingResult, SourceWithMetadata, SourcesService


class TestChatService:
    """Test suite for ChatService."""

    @pytest.fixture
    def chat_service(self):
        """Create ChatService instance."""
        with patch.dict("os.environ", {"API_BASE_URL": "http://test:5055"}):
            return ChatService()

    @pytest.mark.asyncio
    async def test_get_sessions_success(self, chat_service):
        """Test successful retrieval of chat sessions."""
        mock_sessions = [
            {"id": "session:1", "title": "Test Session", "notebook_id": "notebook:1"}
        ]

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_sessions
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await chat_service.get_sessions("notebook:1")
            assert result == mock_sessions

    @pytest.mark.asyncio
    async def test_get_sessions_error(self, chat_service):
        """Test error handling in get_sessions."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                Exception("Connection error")
            )

            with pytest.raises(Exception, match="Connection error"):
                await chat_service.get_sessions("notebook:1")

    @pytest.mark.asyncio
    async def test_create_session_with_title(self, chat_service):
        """Test creating a session with title."""
        mock_session = {"id": "session:1", "title": "My Session"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_session
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await chat_service.create_session("notebook:1", title="My Session")
            assert result == mock_session

    @pytest.mark.asyncio
    async def test_create_session_with_model_override(self, chat_service):
        """Test creating a session with model override."""
        mock_session = {"id": "session:1", "model_override": "gpt-4"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_session
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await chat_service.create_session(
                "notebook:1", model_override="gpt-4"
            )
            assert result == mock_session

    @pytest.mark.asyncio
    async def test_get_session(self, chat_service):
        """Test getting a specific session."""
        mock_session = {"id": "session:1", "messages": []}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_session
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await chat_service.get_session("session:1")
            assert result == mock_session

    @pytest.mark.asyncio
    async def test_update_session(self, chat_service):
        """Test updating a session."""
        mock_session = {"id": "session:1", "title": "Updated Title"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_session
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.put.return_value = (
                mock_response
            )

            result = await chat_service.update_session("session:1", title="Updated Title")
            assert result == mock_session

    @pytest.mark.asyncio
    async def test_delete_session(self, chat_service):
        """Test deleting a session."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.delete.return_value = (
                mock_response
            )

            await chat_service.delete_session("session:1")
            # Should not raise

    def test_chat_service_with_password(self):
        """Test ChatService initializes with password auth."""
        with patch.dict(
            "os.environ",
            {
                "API_BASE_URL": "http://test:5055",
                "OPEN_NOTEBOOK_PASSWORD": "testpass",
            },
        ):
            service = ChatService()
            assert "Authorization" in service.headers
            assert service.headers["Authorization"] == "Bearer testpass"

    def test_chat_service_without_password(self):
        """Test ChatService initializes without password."""
        with patch.dict("os.environ", {"API_BASE_URL": "http://test:5055"}):
            service = ChatService()
            assert service.headers == {}


class TestNotebookService:
    """Test suite for NotebookService."""

    @pytest.fixture
    def notebook_service(self):
        """Create NotebookService instance."""
        return NotebookService()

    @patch("api.notebook_service.api_client")
    def test_get_all_notebooks(self, mock_client, notebook_service):
        """Test getting all notebooks."""
        mock_data = [
            {
                "id": "notebook:1",
                "name": "Test Notebook",
                "description": "Test",
                "archived": False,
                "created": "2024-01-01T00:00:00",
                "updated": "2024-01-01T00:00:00",
            }
        ]
        mock_client.get_notebooks.return_value = mock_data

        notebooks = notebook_service.get_all_notebooks()
        assert len(notebooks) == 1
        assert notebooks[0].name == "Test Notebook"
        assert notebooks[0].id == "notebook:1"

    @patch("api.notebook_service.api_client")
    def test_get_notebook(self, mock_client, notebook_service):
        """Test getting a specific notebook."""
        mock_data = {
            "id": "notebook:1",
            "name": "Test Notebook",
            "description": "Test",
            "archived": False,
            "created": "2024-01-01T00:00:00",
            "updated": "2024-01-01T00:00:00",
        }
        mock_client.get_notebook.return_value = mock_data

        notebook = notebook_service.get_notebook("notebook:1")
        assert notebook is not None
        assert notebook.name == "Test Notebook"
        assert notebook.id == "notebook:1"

    @patch("api.notebook_service.api_client")
    def test_get_notebook_list_response(self, mock_client, notebook_service):
        """Test getting notebook when API returns list."""
        mock_data = [
            {
                "id": "notebook:1",
                "name": "Test Notebook",
                "description": "Test",
                "archived": False,
                "created": "2024-01-01T00:00:00",
                "updated": "2024-01-01T00:00:00",
            }
        ]
        mock_client.get_notebook.return_value = mock_data

        notebook = notebook_service.get_notebook("notebook:1")
        assert notebook is not None
        assert notebook.name == "Test Notebook"

    @patch("api.notebook_service.api_client")
    def test_create_notebook(self, mock_client, notebook_service):
        """Test creating a notebook."""
        mock_data = {
            "id": "notebook:1",
            "name": "New Notebook",
            "description": "New",
            "archived": False,
            "created": "2024-01-01T00:00:00",
            "updated": "2024-01-01T00:00:00",
        }
        mock_client.create_notebook.return_value = mock_data

        notebook = notebook_service.create_notebook("New Notebook", "New")
        assert notebook.name == "New Notebook"
        assert notebook.id == "notebook:1"

    @patch("api.notebook_service.api_client")
    def test_update_notebook(self, mock_client, notebook_service):
        """Test updating a notebook."""
        from open_notebook.domain.notebook import Notebook

        notebook = Notebook(name="Old Name", description="Old")
        notebook.id = "notebook:1"

        mock_data = {
            "id": "notebook:1",
            "name": "Updated Name",
            "description": "Updated",
            "archived": False,
            "updated": "2024-01-02T00:00:00",
        }
        mock_client.update_notebook.return_value = mock_data

        updated = notebook_service.update_notebook(notebook)
        assert updated.name == "Updated Name"
        assert updated.description == "Updated"

    @patch("api.notebook_service.api_client")
    def test_delete_notebook(self, mock_client, notebook_service):
        """Test deleting a notebook."""
        from open_notebook.domain.notebook import Notebook

        notebook = Notebook(name="Test", description="")
        notebook.id = "notebook:1"

        result = notebook_service.delete_notebook(notebook)
        assert result is True
        mock_client.delete_notebook.assert_called_once_with("notebook:1")


class TestSourcesService:
    """Test suite for SourcesService."""

    @pytest.fixture
    def sources_service(self):
        """Create SourcesService instance."""
        return SourcesService()

    @patch("api.sources_service.api_client")
    def test_get_all_sources(self, mock_client, sources_service):
        """Test getting all sources."""
        mock_data = [
            {
                "id": "source:1",
                "title": "Test Source",
                "topics": ["topic1"],
                "asset": {"file_path": "/path/to/file.pdf", "url": None},
                "created": "2024-01-01T00:00:00",
                "updated": "2024-01-01T00:00:00",
                "embedded_chunks": 5,
            }
        ]
        mock_client.get_sources.return_value = mock_data

        sources = sources_service.get_all_sources()
        assert len(sources) == 1
        assert isinstance(sources[0], SourceWithMetadata)
        assert sources[0].title == "Test Source"
        assert sources[0].embedded_chunks == 5

    @patch("api.sources_service.api_client")
    def test_get_all_sources_with_notebook_filter(self, mock_client, sources_service):
        """Test getting sources filtered by notebook."""
        mock_data = []
        mock_client.get_sources.return_value = mock_data

        sources = sources_service.get_all_sources(notebook_id="notebook:1")
        assert len(sources) == 0
        mock_client.get_sources.assert_called_once_with(notebook_id="notebook:1")

    @patch("api.sources_service.api_client")
    def test_get_all_sources_without_asset(self, mock_client, sources_service):
        """Test getting sources without asset."""
        mock_data = [
            {
                "id": "source:1",
                "title": "Test Source",
                "topics": [],
                "asset": None,
                "created": "2024-01-01T00:00:00",
                "updated": "2024-01-01T00:00:00",
                "embedded_chunks": 0,
            }
        ]
        mock_client.get_sources.return_value = mock_data

        sources = sources_service.get_all_sources()
        assert len(sources) == 1
        assert sources[0].asset is None

    def test_source_with_metadata_properties(self):
        """Test SourceWithMetadata property accessors."""
        from open_notebook.domain.notebook import Source

        source = Source(title="Test", topics=["topic1"])
        source.id = "source:1"
        source.created = "2024-01-01T00:00:00"
        source.updated = "2024-01-01T00:00:00"

        source_meta = SourceWithMetadata(source=source, embedded_chunks=10)
        assert source_meta.id == "source:1"
        assert source_meta.title == "Test"
        assert source_meta.topics == ["topic1"]
        assert source_meta.embedded_chunks == 10

    def test_source_with_metadata_title_setter(self):
        """Test SourceWithMetadata title setter."""
        from open_notebook.domain.notebook import Source

        source = Source(title="Old Title")
        source_meta = SourceWithMetadata(source=source, embedded_chunks=0)
        source_meta.title = "New Title"
        assert source.title == "New Title"
        assert source_meta.title == "New Title"
