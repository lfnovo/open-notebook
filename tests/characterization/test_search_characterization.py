"""Characterization: search — both text search and vector search.

Captures the CURRENT behavior of POST /api/search as of `upstream-base`.
See ./README.md before changing anything here.

The two search modes differ in more than a flag: vector search additionally
requires a configured embedding model and applies a `minimum_score` floor,
while text search does neither.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from open_notebook.exceptions import DatabaseOperationError, InvalidInputError


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


class TestTextSearch:
    """type=text — the default."""

    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_text_search_is_the_default_type(self, mock_text, client):
        """Omitting `type` runs a text search, not a vector search."""
        mock_text.return_value = []

        response = client.post("/api/search", json={"query": "anything"})

        assert response.status_code == 200
        assert response.json()["search_type"] == "text"
        mock_text.assert_awaited_once()

    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_text_search_passes_defaults_through(self, mock_text, client):
        mock_text.return_value = []

        client.post("/api/search", json={"query": "surrealdb", "type": "text"})

        kwargs = mock_text.await_args.kwargs
        assert kwargs["keyword"] == "surrealdb"
        # `limit` maps to `results`, and defaults to 100.
        assert kwargs["results"] == 100
        # Sources and notes are both searched by default.
        assert kwargs["source"] is True
        assert kwargs["note"] is True
        # minimum_score is NOT passed to text search — it is vector-only.
        assert "minimum_score" not in kwargs

    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_text_search_returns_results_and_total_count(self, mock_text, client):
        mock_text.return_value = [
            {"id": "source:1", "title": "First"},
            {"id": "note:2", "title": "Second"},
        ]

        response = client.post("/api/search", json={"query": "x", "type": "text"})

        assert response.status_code == 200
        body = response.json()
        assert body["total_count"] == 2
        assert body["search_type"] == "text"
        assert [r["title"] for r in body["results"]] == ["First", "Second"]

    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_none_results_become_an_empty_list(self, mock_text, client):
        """A None from the search layer is normalized to [] with count 0."""
        mock_text.return_value = None

        response = client.post("/api/search", json={"query": "x", "type": "text"})

        assert response.status_code == 200
        assert response.json()["results"] == []
        assert response.json()["total_count"] == 0

    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_scope_flags_are_forwarded(self, mock_text, client):
        mock_text.return_value = []

        client.post(
            "/api/search",
            json={
                "query": "x",
                "type": "text",
                "search_sources": False,
                "search_notes": True,
            },
        )

        kwargs = mock_text.await_args.kwargs
        assert kwargs["source"] is False
        assert kwargs["note"] is True

    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_no_embedding_model_needed_for_text_search(self, mock_text, client):
        """Text search must keep working on an instance with no embedding model
        configured — this is the fallback when vector search is unavailable."""
        mock_text.return_value = []

        with patch(
            "api.routers.search.model_manager.get_embedding_model",
            new_callable=AsyncMock,
        ) as mock_embed:
            mock_embed.return_value = None
            response = client.post("/api/search", json={"query": "x", "type": "text"})

        assert response.status_code == 200
        # The embedding model was never even consulted.
        mock_embed.assert_not_awaited()


class TestVectorSearch:
    """type=vector — requires an embedding model."""

    @patch("api.routers.search.vector_search", new_callable=AsyncMock)
    @patch("api.routers.search.model_manager.get_embedding_model", new_callable=AsyncMock)
    def test_vector_search_passes_minimum_score(self, mock_embed, mock_vector, client):
        mock_embed.return_value = object()
        mock_vector.return_value = []

        client.post(
            "/api/search",
            json={"query": "semantic", "type": "vector", "minimum_score": 0.75},
        )

        kwargs = mock_vector.await_args.kwargs
        assert kwargs["keyword"] == "semantic"
        assert kwargs["minimum_score"] == 0.75

    @patch("api.routers.search.vector_search", new_callable=AsyncMock)
    @patch("api.routers.search.model_manager.get_embedding_model", new_callable=AsyncMock)
    def test_vector_minimum_score_defaults_to_point_two(
        self, mock_embed, mock_vector, client
    ):
        mock_embed.return_value = object()
        mock_vector.return_value = []

        client.post("/api/search", json={"query": "semantic", "type": "vector"})

        assert mock_vector.await_args.kwargs["minimum_score"] == 0.2

    @patch("api.routers.search.vector_search", new_callable=AsyncMock)
    @patch("api.routers.search.model_manager.get_embedding_model", new_callable=AsyncMock)
    def test_vector_search_reports_its_search_type(
        self, mock_embed, mock_vector, client
    ):
        mock_embed.return_value = object()
        mock_vector.return_value = [{"id": "source:1", "relevance": 0.9}]

        response = client.post("/api/search", json={"query": "x", "type": "vector"})

        assert response.status_code == 200
        assert response.json()["search_type"] == "vector"
        assert response.json()["total_count"] == 1

    @patch("api.routers.search.model_manager.get_embedding_model", new_callable=AsyncMock)
    def test_vector_search_without_embedding_model_returns_400(
        self, mock_embed, client
    ):
        """No embedding model configured -> 400 with a message pointing the user
        at the Models section. It does NOT silently fall back to text search."""
        mock_embed.return_value = None

        response = client.post("/api/search", json={"query": "x", "type": "vector"})

        assert response.status_code == 400
        assert "requires an embedding model" in response.json()["detail"]


class TestRequestValidation:
    @pytest.mark.parametrize("bad_type", ["semantic", "fulltext", "TEXT", ""])
    def test_unknown_search_type_returns_422(self, bad_type, client):
        """`type` is a Literal["text", "vector"] — anything else is a 422."""
        response = client.post("/api/search", json={"query": "x", "type": bad_type})
        assert response.status_code == 422

    def test_missing_query_returns_422(self, client):
        response = client.post("/api/search", json={"type": "text"})
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_score", [-0.1, 1.1])
    def test_minimum_score_outside_zero_to_one_returns_422(self, bad_score, client):
        response = client.post(
            "/api/search",
            json={"query": "x", "type": "vector", "minimum_score": bad_score},
        )
        assert response.status_code == 422

    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_empty_query_string_is_accepted(self, mock_text, client):
        """An empty query is NOT rejected — it reaches the search layer.
        Captured as current behavior, not endorsed."""
        mock_text.return_value = []
        response = client.post("/api/search", json={"query": "", "type": "text"})
        assert response.status_code == 200


class TestErrorMapping:
    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_invalid_input_error_becomes_400(self, mock_text, client):
        mock_text.side_effect = InvalidInputError("bad keyword")
        response = client.post("/api/search", json={"query": "x", "type": "text"})
        assert response.status_code == 400

    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_database_error_becomes_500(self, mock_text, client):
        mock_text.side_effect = DatabaseOperationError("index missing")
        response = client.post("/api/search", json={"query": "x", "type": "text"})
        assert response.status_code == 500
        # NOTE: the underlying error text is surfaced to the client here.
        assert "Search failed" in response.json()["detail"]
