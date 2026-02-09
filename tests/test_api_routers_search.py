"""
Tests for /api/search router endpoints.

Focuses on increasing coverage from 19%.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSearchRouter:
    """Test suite for /api/search endpoints."""

    @pytest.mark.asyncio
    @patch("api.routers.search.text_search")
    async def test_search_text_success(self, mock_text_search, client):
        """Test POST /api/search with text search."""
        mock_results = [
            {
                "id": "source:1",
                "title": "Test Source",
                "relevance_score": 0.8,
                "excerpt": "Test excerpt",
            }
        ]
        mock_text_search.return_value = mock_results

        response = client.post(
            "/api/search",
            json={
                "query": "test query",
                "type": "text",
                "limit": 10,
                "search_sources": True,
                "search_notes": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["search_type"] == "text"
        assert len(data["results"]) == 1

    @pytest.mark.asyncio
    @patch("api.routers.search.vector_search")
    @patch("api.routers.search.model_manager")
    async def test_search_vector_success(self, mock_model_manager, mock_vector_search, client):
        """Test POST /api/search with vector search."""
        mock_embedding_model = MagicMock()
        mock_model_manager.get_embedding_model = AsyncMock(return_value=mock_embedding_model)

        mock_results = [
            {
                "id": "source:1",
                "title": "Test Source",
                "relevance_score": 0.9,
                "excerpt": "Test excerpt",
            }
        ]
        mock_vector_search.return_value = mock_results

        response = client.post(
            "/api/search",
            json={
                "query": "test query",
                "type": "vector",
                "limit": 10,
                "minimum_score": 0.5,
                "search_sources": True,
                "search_notes": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["search_type"] == "vector"
        assert len(data["results"]) == 1

    @pytest.mark.asyncio
    @patch("api.routers.search.model_manager")
    async def test_search_vector_no_embedding_model(self, mock_model_manager, client):
        """Test POST /api/search with vector search fails without embedding model."""
        mock_model_manager.get_embedding_model = AsyncMock(return_value=None)

        response = client.post(
            "/api/search",
            json={
                "query": "test query",
                "type": "vector",
                "limit": 10,
            },
        )
        assert response.status_code == 400
        assert "embedding model" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch("api.routers.search.text_search")
    async def test_search_invalid_input(self, mock_text_search, client):
        """Test POST /api/search handles invalid input."""
        from open_notebook.exceptions import InvalidInputError

        mock_text_search.side_effect = InvalidInputError("Invalid query")

        response = client.post(
            "/api/search",
            json={
                "query": "",
                "type": "text",
                "limit": 10,
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    @patch("api.routers.search.text_search")
    async def test_search_database_error(self, mock_text_search, client):
        """Test POST /api/search handles database errors."""
        from open_notebook.exceptions import DatabaseOperationError

        mock_text_search.side_effect = DatabaseOperationError("DB error")

        response = client.post(
            "/api/search",
            json={
                "query": "test",
                "type": "text",
                "limit": 10,
            },
        )
        assert response.status_code == 500

    @pytest.mark.asyncio
    @patch("api.routers.search.text_search")
    async def test_search_empty_results(self, mock_text_search, client):
        """Test POST /api/search handles empty results."""
        mock_text_search.return_value = []

        response = client.post(
            "/api/search",
            json={
                "query": "nonexistent",
                "type": "text",
                "limit": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["results"] == []

    @pytest.mark.asyncio
    @patch("api.routers.search.ask_graph")
    @patch("api.routers.search.Model")
    @patch("api.routers.search.model_manager")
    async def test_ask_endpoint_success(self, mock_model_manager, mock_model_class, mock_ask_graph, client):
        """Test POST /api/search/ask returns streaming response."""
        mock_strategy_model = MagicMock()
        mock_strategy_model.id = "model:strategy"
        mock_answer_model = MagicMock()
        mock_answer_model.id = "model:answer"
        mock_final_model = MagicMock()
        mock_final_model.id = "model:final"

        mock_model_class.get = AsyncMock(side_effect=[mock_strategy_model, mock_answer_model, mock_final_model])
        mock_model_manager.get_embedding_model = AsyncMock(return_value=MagicMock())

        # Mock streaming response
        async def mock_stream():
            yield {"agent": {"strategy": MagicMock(reasoning="test", searches=[])}}
            yield {"provide_answer": {"answers": ["answer1"]}}
            yield {"write_final_answer": {"final_answer": "final"}}

        mock_ask_graph.astream = AsyncMock(return_value=mock_stream())

        response = client.post(
            "/api/search/ask",
            json={
                "question": "What is AI?",
                "strategy_model": "model:strategy",
                "answer_model": "model:answer",
                "final_answer_model": "model:final",
            },
        )
        # Streaming response should be 200
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("api.routers.search.Model")
    async def test_ask_endpoint_missing_models(self, mock_model_class, client):
        """Test POST /api/search/ask fails when models are missing."""
        mock_model_class.get = AsyncMock(return_value=None)

        response = client.post(
            "/api/search/ask",
            json={
                "question": "What is AI?",
                "strategy_model": "model:strategy",
                "answer_model": "model:answer",
                "final_answer_model": "model:final",
            },
        )
        assert response.status_code == 400
