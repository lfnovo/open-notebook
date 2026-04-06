"""
Tests for bug fixes #627 (asset persistence), #670 (title preservation),
and #651 (credential cascade delete).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.domain.notebook import Asset, Source


@pytest.fixture
def client():
    """Create test client after environment variables have been cleared by conftest."""
    from api.main import app

    return TestClient(app)


# ============================================================================
# TEST SUITE 1: #627 - Async source creation persists asset
# ============================================================================


class TestAsyncSourceAssetPersistence:
    """Tests for #627 - asset is persisted before async processing."""

    def test_source_created_with_url_asset(self):
        """Source created for link type has asset with url."""
        asset = Asset(url="https://example.com/article")
        source = Source(
            title="Processing...",
            topics=[],
            asset=asset,
        )
        assert source.asset is not None
        assert source.asset.url == "https://example.com/article"
        assert source.asset.file_path is None

    def test_source_created_with_file_asset(self):
        """Source created for upload type has asset with file_path."""
        asset = Asset(file_path="/tmp/uploads/video.mp4")
        source = Source(
            title="Processing...",
            topics=[],
            asset=asset,
        )
        assert source.asset is not None
        assert source.asset.file_path == "/tmp/uploads/video.mp4"
        assert source.asset.url is None

    def test_source_created_without_asset_for_text(self):
        """Source created for text type has no asset."""
        source = Source(
            title="Processing...",
            topics=[],
            asset=None,
        )
        assert source.asset is None

    def test_retry_with_url_asset(self):
        """Retry endpoint can reconstruct content_state from url asset."""
        source = Source(
            title="Processing...",
            topics=[],
            asset=Asset(url="https://example.com/video"),
        )
        # Simulate what the retry endpoint does
        content_state = {}
        if source.asset:
            if source.asset.file_path:
                content_state = {
                    "file_path": source.asset.file_path,
                    "delete_source": False,
                }
            elif source.asset.url:
                content_state = {"url": source.asset.url}

        assert content_state == {"url": "https://example.com/video"}

    def test_retry_with_file_asset(self):
        """Retry endpoint can reconstruct content_state from file asset."""
        source = Source(
            title="Processing...",
            topics=[],
            asset=Asset(file_path="/tmp/uploads/doc.pdf"),
        )
        content_state = {}
        if source.asset:
            if source.asset.file_path:
                content_state = {
                    "file_path": source.asset.file_path,
                    "delete_source": False,
                }
            elif source.asset.url:
                content_state = {"url": source.asset.url}

        assert content_state == {
            "file_path": "/tmp/uploads/doc.pdf",
            "delete_source": False,
        }


# ============================================================================
# TEST SUITE 2: #670 - Custom title preservation
# ============================================================================


class TestTitlePreservation:
    """Tests for #670 - user-set titles are preserved after processing."""

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.Source.get")
    @patch("open_notebook.graphs.source.Source.save", new_callable=AsyncMock)
    async def test_custom_title_preserved(self, mock_save, mock_get):
        """User-set title is NOT overwritten by content_state.title."""
        from open_notebook.graphs.source import save_source

        mock_source = MagicMock(spec=Source)
        mock_source.title = "My Custom Research Title"
        mock_source.save = AsyncMock()
        mock_get.return_value = mock_source

        content_state = MagicMock()
        content_state.title = "video.mp4"
        content_state.url = "https://example.com"
        content_state.file_path = None
        content_state.content = "Some content"

        state = {
            "source_id": "source:123",
            "content_state": content_state,
            "embed": False,
            "apply_transformations": [],
        }

        await save_source(state)

        # Title should remain as the custom user title
        assert mock_source.title == "My Custom Research Title"

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.Source.get")
    @patch("open_notebook.graphs.source.Source.save", new_callable=AsyncMock)
    async def test_placeholder_title_replaced(self, mock_save, mock_get):
        """Placeholder 'Processing...' title IS replaced by extracted title."""
        from open_notebook.graphs.source import save_source

        mock_source = MagicMock(spec=Source)
        mock_source.title = "Processing..."
        mock_source.save = AsyncMock()
        mock_get.return_value = mock_source

        content_state = MagicMock()
        content_state.title = "Extracted Article Title"
        content_state.url = "https://example.com"
        content_state.file_path = None
        content_state.content = "Some content"

        state = {
            "source_id": "source:123",
            "content_state": content_state,
            "embed": False,
            "apply_transformations": [],
        }

        await save_source(state)

        assert mock_source.title == "Extracted Article Title"

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.Source.get")
    @patch("open_notebook.graphs.source.Source.save", new_callable=AsyncMock)
    async def test_none_title_replaced(self, mock_save, mock_get):
        """None title IS replaced by extracted title."""
        from open_notebook.graphs.source import save_source

        mock_source = MagicMock(spec=Source)
        mock_source.title = None
        mock_source.save = AsyncMock()
        mock_get.return_value = mock_source

        content_state = MagicMock()
        content_state.title = "Extracted Title"
        content_state.url = None
        content_state.file_path = "/tmp/file.pdf"
        content_state.content = "Content"

        state = {
            "source_id": "source:123",
            "content_state": content_state,
            "embed": False,
            "apply_transformations": [],
        }

        await save_source(state)

        assert mock_source.title == "Extracted Title"

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.Source.get")
    @patch("open_notebook.graphs.source.Source.save", new_callable=AsyncMock)
    async def test_empty_title_replaced(self, mock_save, mock_get):
        """Empty string title IS replaced by extracted title."""
        from open_notebook.graphs.source import save_source

        mock_source = MagicMock(spec=Source)
        mock_source.title = ""
        mock_source.save = AsyncMock()
        mock_get.return_value = mock_source

        content_state = MagicMock()
        content_state.title = "Extracted Title"
        content_state.url = None
        content_state.file_path = None
        content_state.content = "Content"

        state = {
            "source_id": "source:123",
            "content_state": content_state,
            "embed": False,
            "apply_transformations": [],
        }

        await save_source(state)

        assert mock_source.title == "Extracted Title"


# ============================================================================
# TEST SUITE 3: #651 - Credential cascade delete
# ============================================================================


class TestCredentialCascadeDelete:
    """Tests for #651 - deleting credential cascade-deletes linked models."""

    @pytest.mark.asyncio
    @patch("api.routers.credentials.Credential.get")
    async def test_cascade_delete_linked_models(self, mock_get, client):
        """Deleting credential without options cascade-deletes linked models."""
        mock_model1 = AsyncMock()
        mock_model1.id = "model:1"
        mock_model1.provider = "openai"
        mock_model1.name = "gpt-4"

        mock_model2 = AsyncMock()
        mock_model2.id = "model:2"
        mock_model2.provider = "openai"
        mock_model2.name = "gpt-3.5-turbo"

        mock_cred = AsyncMock()
        mock_cred.get_linked_models = AsyncMock(
            return_value=[mock_model1, mock_model2]
        )
        mock_cred.delete = AsyncMock()
        mock_get.return_value = mock_cred

        response = client.delete("/api/credentials/cred:123")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_models"] == 2
        assert data["message"] == "Credential deleted successfully"

        # Verify models were deleted
        mock_model1.delete.assert_called_once()
        mock_model2.delete.assert_called_once()
        mock_cred.delete.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.routers.credentials.Credential.get")
    async def test_delete_credential_no_linked_models(self, mock_get, client):
        """Deleting credential with no linked models works cleanly."""
        mock_cred = AsyncMock()
        mock_cred.get_linked_models = AsyncMock(return_value=[])
        mock_cred.delete = AsyncMock()
        mock_get.return_value = mock_cred

        response = client.delete("/api/credentials/cred:123")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_models"] == 0
        mock_cred.delete.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.routers.credentials.Credential.get")
    async def test_migrate_models_instead_of_delete(self, mock_get, client):
        """Passing migrate_to reassigns models instead of deleting them."""
        mock_model = AsyncMock()
        mock_model.id = "model:1"
        mock_model.credential = "cred:123"
        mock_model.save = AsyncMock()

        mock_cred = AsyncMock()
        mock_cred.get_linked_models = AsyncMock(return_value=[mock_model])
        mock_cred.delete = AsyncMock()

        mock_target_cred = AsyncMock()
        mock_target_cred.id = "cred:456"

        # First call returns cred to delete, second returns target
        mock_get.side_effect = [mock_cred, mock_target_cred]

        response = client.delete(
            "/api/credentials/cred:123?migrate_to=cred:456"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_models"] == 0  # Models were migrated, not deleted
        mock_model.save.assert_called_once()
        assert mock_model.credential == "cred:456"
        mock_cred.delete.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
