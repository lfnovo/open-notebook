"""
Tests for remaining API service layer modules.

Covers context_service and embedding_service which are at 0% coverage.
"""

from unittest.mock import patch

import pytest

from api.context_service import ContextService, context_service
from api.embedding_service import EmbeddingService, embedding_service


class TestContextService:
    """Test suite for ContextService."""

    @pytest.fixture
    def service(self):
        """Create ContextService instance."""
        return ContextService()

    @patch("api.context_service.api_client")
    def test_get_notebook_context(self, mock_client, service):
        """Test get_notebook_context calls API client."""
        mock_context = {"sources": [], "notes": []}
        mock_client.get_notebook_context.return_value = mock_context

        result = service.get_notebook_context("notebook:123")
        assert result == mock_context
        mock_client.get_notebook_context.assert_called_once_with(
            notebook_id="notebook:123", context_config=None
        )

    @patch("api.context_service.api_client")
    def test_get_notebook_context_with_config(self, mock_client, service):
        """Test get_notebook_context with custom config."""
        mock_context = {"sources": [{"id": "source:1"}]}
        config = {"max_sources": 5}
        mock_client.get_notebook_context.return_value = mock_context

        result = service.get_notebook_context("notebook:123", context_config=config)
        assert result == mock_context
        mock_client.get_notebook_context.assert_called_once_with(
            notebook_id="notebook:123", context_config=config
        )

    def test_global_instance_exists(self):
        """Test that global context_service instance exists."""
        assert context_service is not None
        assert isinstance(context_service, ContextService)


class TestEmbeddingService:
    """Test suite for EmbeddingService."""

    @pytest.fixture
    def service(self):
        """Create EmbeddingService instance."""
        return EmbeddingService()

    @patch("api.embedding_service.api_client")
    def test_embed_content(self, mock_client, service):
        """Test embed_content calls API client."""
        mock_result = {"status": "success", "command_id": "cmd:123"}
        mock_client.embed_content.return_value = mock_result

        result = service.embed_content(item_id="source:123", item_type="source")
        assert result == mock_result
        mock_client.embed_content.assert_called_once_with(
            item_id="source:123", item_type="source"
        )

    @patch("api.embedding_service.api_client")
    def test_embed_content_note(self, mock_client, service):
        """Test embed_content for note type."""
        mock_result = {"status": "success"}
        mock_client.embed_content.return_value = mock_result

        result = service.embed_content(item_id="note:456", item_type="note")
        assert result == mock_result
        mock_client.embed_content.assert_called_once_with(
            item_id="note:456", item_type="note"
        )

    def test_global_instance_exists(self):
        """Test that global embedding_service instance exists."""
        assert embedding_service is not None
        assert isinstance(embedding_service, EmbeddingService)
