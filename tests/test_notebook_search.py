"""
Unit tests for notebook-scoped search.

Tests the notebook_id parameter through API models, domain search functions,
and the ask graph state threading.
"""

from unittest.mock import AsyncMock, patch

import pytest
from surrealdb import RecordID

from api.models import AskRequest, SearchRequest
from open_notebook.domain.notebook import text_search, vector_search
from open_notebook.exceptions import InvalidInputError
from open_notebook.graphs.ask import (
    Search,
    Strategy,
    SubGraphState,
    trigger_queries,
)

# ============================================================================
# TEST SUITE 1: API Model notebook_id Field
# ============================================================================


class TestSearchRequestNotebookId:
    """Test that SearchRequest accepts optional notebook_id."""

    def test_search_request_without_notebook_id(self):
        """notebook_id defaults to None when omitted."""
        req = SearchRequest(query="test")
        assert req.notebook_id is None

    def test_search_request_with_notebook_id(self):
        """notebook_id is preserved when provided."""
        req = SearchRequest(query="test", notebook_id="notebook:abc123")
        assert req.notebook_id == "notebook:abc123"

    def test_search_request_with_notebook_id_none_explicit(self):
        """Explicitly passing None works."""
        req = SearchRequest(query="test", notebook_id=None)
        assert req.notebook_id is None


class TestAskRequestNotebookId:
    """Test that AskRequest accepts optional notebook_id."""

    def test_ask_request_without_notebook_id(self):
        """notebook_id defaults to None when omitted."""
        req = AskRequest(
            question="What is AI?",
            strategy_model="model:1",
            answer_model="model:2",
            final_answer_model="model:3",
        )
        assert req.notebook_id is None

    def test_ask_request_with_notebook_id(self):
        """notebook_id is preserved when provided."""
        req = AskRequest(
            question="What is AI?",
            strategy_model="model:1",
            answer_model="model:2",
            final_answer_model="model:3",
            notebook_id="notebook:xyz",
        )
        assert req.notebook_id == "notebook:xyz"


# ============================================================================
# TEST SUITE 2: Domain Search Functions with notebook_id
# ============================================================================


class TestTextSearchNotebookId:
    """Test text_search passes notebook_id to repo_query."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
    async def test_text_search_without_notebook_id(self, mock_repo_query):
        """When notebook_id is None, passes None to the query."""
        mock_repo_query.return_value = [{"id": "source:1", "title": "Test"}]

        results = await text_search("test query", 10)

        mock_repo_query.assert_called_once()
        call_vars = mock_repo_query.call_args[0][1]
        assert call_vars["notebook_id"] is None

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
    async def test_text_search_with_notebook_id(self, mock_repo_query):
        """When notebook_id is provided, passes a RecordID to the query."""
        mock_repo_query.return_value = [{"id": "source:1", "title": "Test"}]

        results = await text_search("test query", 10, notebook_id="notebook:abc123")

        mock_repo_query.assert_called_once()
        call_vars = mock_repo_query.call_args[0][1]
        assert isinstance(call_vars["notebook_id"], RecordID)
        assert str(call_vars["notebook_id"]) == "notebook:abc123"

    @pytest.mark.asyncio
    async def test_text_search_empty_keyword_raises(self):
        """Empty keyword still raises InvalidInputError."""
        with pytest.raises(InvalidInputError, match="Search keyword cannot be empty"):
            await text_search("", 10, notebook_id="notebook:abc123")

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
    async def test_text_search_query_includes_notebook_id_param(self, mock_repo_query):
        """The SurrealQL query string references $notebook_id."""
        mock_repo_query.return_value = []

        await text_search("test", 5, notebook_id="notebook:123")

        query_str = mock_repo_query.call_args[0][0]
        assert "$notebook_id" in query_str


class TestVectorSearchNotebookId:
    """Test vector_search passes notebook_id to repo_query."""

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
    @patch(
        "open_notebook.utils.embedding.generate_embedding",
        new_callable=AsyncMock,
        return_value=[0.1, 0.2, 0.3],
    )
    async def test_vector_search_without_notebook_id(self, mock_embed, mock_repo_query):
        """When notebook_id is None, passes None to the query."""
        mock_repo_query.return_value = [{"id": "source:1", "title": "Test"}]

        results = await vector_search("test query", 10)

        mock_repo_query.assert_called_once()
        call_vars = mock_repo_query.call_args[0][1]
        assert call_vars["notebook_id"] is None

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
    @patch(
        "open_notebook.utils.embedding.generate_embedding",
        new_callable=AsyncMock,
        return_value=[0.1, 0.2, 0.3],
    )
    async def test_vector_search_with_notebook_id(self, mock_embed, mock_repo_query):
        """When notebook_id is provided, passes a RecordID to the query."""
        mock_repo_query.return_value = [{"id": "source:1", "title": "Test"}]

        results = await vector_search("test query", 10, notebook_id="notebook:abc123")

        mock_repo_query.assert_called_once()
        call_vars = mock_repo_query.call_args[0][1]
        assert isinstance(call_vars["notebook_id"], RecordID)
        assert str(call_vars["notebook_id"]) == "notebook:abc123"

    @pytest.mark.asyncio
    async def test_vector_search_empty_keyword_raises(self):
        """Empty keyword still raises InvalidInputError."""
        with pytest.raises(InvalidInputError, match="Search keyword cannot be empty"):
            await vector_search("", 10, notebook_id="notebook:abc123")

    @pytest.mark.asyncio
    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
    @patch(
        "open_notebook.utils.embedding.generate_embedding",
        new_callable=AsyncMock,
        return_value=[0.1, 0.2, 0.3],
    )
    async def test_vector_search_query_includes_notebook_id_param(
        self, mock_embed, mock_repo_query
    ):
        """The SurrealQL query string references $notebook_id."""
        mock_repo_query.return_value = []

        await vector_search("test", 5, notebook_id="notebook:123")

        query_str = mock_repo_query.call_args[0][0]
        assert "$notebook_id" in query_str


# ============================================================================
# TEST SUITE 3: Ask Graph notebook_id Threading
# ============================================================================


class TestAskGraphNotebookId:
    """Test that the ask graph threads notebook_id through state and config."""

    def test_subgraph_state_accepts_notebook_id(self):
        """SubGraphState includes notebook_id field."""
        state = SubGraphState(
            question="test",
            term="term",
            instructions="instructions",
            results={},
            answer="",
            ids=[],
            notebook_id="notebook:abc",
        )
        assert state["notebook_id"] == "notebook:abc"

    @pytest.mark.asyncio
    async def test_trigger_queries_passes_notebook_id_from_config(self):
        """trigger_queries reads notebook_id from config and includes it in Send."""
        strategy = Strategy(
            reasoning="test",
            searches=[Search(term="AI safety", instructions="find info")],
        )
        state = {"question": "What is AI?", "strategy": strategy}
        config = {"configurable": {"notebook_id": "notebook:xyz"}}

        sends = await trigger_queries(state, config)

        assert len(sends) == 1
        assert sends[0].node == "provide_answer"
        send_state = sends[0].arg
        assert send_state["notebook_id"] == "notebook:xyz"

    @pytest.mark.asyncio
    async def test_trigger_queries_passes_none_when_no_notebook_id(self):
        """trigger_queries passes None when notebook_id not in config."""
        strategy = Strategy(
            reasoning="test",
            searches=[Search(term="AI safety", instructions="find info")],
        )
        state = {"question": "What is AI?", "strategy": strategy}
        config = {"configurable": {}}

        sends = await trigger_queries(state, config)

        assert len(sends) == 1
        send_state = sends[0].arg
        assert send_state["notebook_id"] is None

    @pytest.mark.asyncio
    async def test_trigger_queries_multiple_searches(self):
        """notebook_id is passed to all Send instances."""
        strategy = Strategy(
            reasoning="test",
            searches=[
                Search(term="AI safety", instructions="find safety info"),
                Search(term="alignment", instructions="find alignment info"),
            ],
        )
        state = {"question": "Compare approaches", "strategy": strategy}
        config = {"configurable": {"notebook_id": "notebook:multi"}}

        sends = await trigger_queries(state, config)

        assert len(sends) == 2
        for send in sends:
            assert send.arg["notebook_id"] == "notebook:multi"
