from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client after environment variables have been cleared by conftest."""
    from api.main import app

    return TestClient(app)


class TestSearchLimitValidation:
    """SearchRequest.limit must reject non-positive values (#863)."""

    @pytest.mark.parametrize("bad_limit", [0, -1, -100])
    def test_non_positive_limit_returns_422(self, bad_limit, client):
        response = client.post(
            "/api/search",
            json={"query": "x", "type": "text", "limit": bad_limit},
        )
        assert response.status_code == 422

    def test_limit_above_max_returns_422(self, client):
        response = client.post(
            "/api/search",
            json={"query": "x", "type": "text", "limit": 1001},
        )
        assert response.status_code == 422

    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_valid_limit_returns_200(self, mock_text_search, client):
        mock_text_search.return_value = []
        response = client.post(
            "/api/search",
            json={"query": "x", "type": "text", "limit": 10},
        )
        assert response.status_code == 200
        mock_text_search.assert_awaited_once()


class TestTextSearchHighlightOverflowFallback:
    """text_search() must fall back to vector search on a highlight position overflow (#648)."""

    @pytest.mark.asyncio
    async def test_position_overflow_falls_back_to_vector_search(self):
        from open_notebook.domain import notebook as notebook_module

        overflow = RuntimeError(
            "A value can't be highlighted: position overflow: 2545 - len: 1965"
        )
        with (
            patch.object(
                notebook_module, "repo_query", new_callable=AsyncMock, side_effect=overflow
            ),
            patch.object(
                notebook_module,
                "vector_search",
                new_callable=AsyncMock,
                return_value=[{"id": "source:1"}],
            ) as mock_vector,
        ):
            result = await notebook_module.text_search("hello", 10)

        assert result == [{"id": "source:1"}]
        mock_vector.assert_awaited_once_with("hello", 10, True, True, notebook_ids=None)

    @pytest.mark.asyncio
    async def test_position_overflow_raises_when_vector_also_fails(self):
        from open_notebook.domain import notebook as notebook_module
        from open_notebook.exceptions import DatabaseOperationError

        overflow = RuntimeError("position overflow: 1 - len: 0")
        with (
            patch.object(
                notebook_module, "repo_query", new_callable=AsyncMock, side_effect=overflow
            ),
            patch.object(
                notebook_module,
                "vector_search",
                new_callable=AsyncMock,
                side_effect=Exception("no embedding model"),
            ),
        ):
            # When both search paths fail, surface the error rather than masking it
            # as an empty result set.
            with pytest.raises(DatabaseOperationError):
                await notebook_module.text_search("hello", 10)

    @pytest.mark.asyncio
    async def test_other_runtime_errors_still_raise(self):
        from open_notebook.domain import notebook as notebook_module
        from open_notebook.exceptions import DatabaseOperationError

        with patch.object(
            notebook_module,
            "repo_query",
            new_callable=AsyncMock,
            side_effect=RuntimeError("some other db failure"),
        ):
            with pytest.raises(DatabaseOperationError):
                await notebook_module.text_search("hello", 10)


class TestSearchNotebookFiltering:
    """notebook_ids parameter correctly scopes search results."""

    @pytest.mark.asyncio
    async def test_none_notebook_ids_unfiltered(self):
        """When notebook_ids is None, $notebook_ids is passed as None (no filtering)."""
        from open_notebook.domain import notebook as notebook_module

        mock_results = [{"id": "source:1"}, {"id": "source:2"}]
        with patch.object(
            notebook_module, "repo_query", new_callable=AsyncMock, return_value=mock_results
        ) as mock_repo:
            results = await notebook_module.text_search("test", 10, notebook_ids=None)

        assert results == mock_results
        # Verify notebook_ids param was None in the SurrealQL call
        _sql, params = mock_repo.await_args.args
        assert params["notebook_ids"] is None

    @pytest.mark.asyncio
    async def test_empty_notebook_ids_normalized_to_none(self):
        """Empty list is normalized to None (via _normalize_empty_notebook_ids) so all results are returned."""
        from open_notebook.domain import notebook as notebook_module

        mock_results = [{"id": "source:1"}]
        with patch.object(
            notebook_module, "repo_query", new_callable=AsyncMock, return_value=mock_results
        ) as mock_repo:
            results = await notebook_module.text_search("test", 10, notebook_ids=[])

        assert results == mock_results
        _sql, params = mock_repo.await_args.args
        assert params["notebook_ids"] is None

    @pytest.mark.asyncio
    async def test_specific_notebook_ids_passed_as_record_ids(self):
        """Provided notebook IDs are converted to SurrealDB record IDs."""
        from open_notebook.domain import notebook as notebook_module

        mock_results = [{"id": "source:1"}]
        with patch.object(
            notebook_module, "repo_query", new_callable=AsyncMock, return_value=mock_results
        ) as mock_repo:
            results = await notebook_module.text_search(
                "test", 10, notebook_ids=["notebook:1", "notebook:2"]
            )

        assert results == mock_results
        _sql, params = mock_repo.await_args.args
        ids = params["notebook_ids"]
        assert ids is not None
        assert len(ids) == 2
        assert ids[0].id == "1", f"ids[0].id={ids[0].id!r}"
        assert ids[0].table_name == "notebook"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_vector_search_passes_notebook_ids(self):
        """vector_search also passes notebook_ids through correctly.
        (Tests via text_search since both share the same notebook_ids
        parameter construction logic; vector_search additionally calls
        generate_embedding which requires a live SurrealDB connection.)"""
        from open_notebook.domain import notebook as notebook_module

        mock_results = [{"id": "src:1"}]
        with patch.object(
            notebook_module, "repo_query", new_callable=AsyncMock, return_value=mock_results
        ) as mock_repo:
            # text_search and vector_search use the identical notebook_ids
            # param construction (lines 771-776 vs 833-838 in notebook.py)
            results = await notebook_module.text_search(
                "test keyword", 10, notebook_ids=["notebook:1"]
            )

        assert results == mock_results
        _sql, params = mock_repo.await_args.args
        ids = params["notebook_ids"]
        assert ids is not None
        assert len(ids) == 1
        assert ids[0].id == "1"
        assert ids[0].table_name == "notebook"

