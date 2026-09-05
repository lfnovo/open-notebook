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
                notebook_module,
                "repo_query",
                new_callable=AsyncMock,
                side_effect=overflow,
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
                notebook_module,
                "repo_query",
                new_callable=AsyncMock,
                side_effect=overflow,
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


class TestVectorSearchOrdering:
    """vector_search() must return results in descending similarity order (#1301)."""

    @pytest.mark.asyncio
    async def test_reorders_results_by_descending_similarity(self):
        from open_notebook.domain import notebook as notebook_module

        unordered = [
            {"id": "source:vehicle", "similarity": 0.353189},
            {"id": "source:medical", "similarity": 0.548259},
            {"id": "source:finance", "similarity": 0.389266},
        ]
        with (
            patch.object(
                notebook_module,
                "generate_embedding",
                create=True,
                new_callable=AsyncMock,
                return_value=[0.1, 0.2],
            ),
            patch(
                "open_notebook.utils.embedding.generate_embedding",
                new_callable=AsyncMock,
                return_value=[0.1, 0.2],
            ),
            patch.object(
                notebook_module,
                "repo_query",
                new_callable=AsyncMock,
                return_value=unordered,
            ),
        ):
            result = await notebook_module.vector_search(
                "Which document discusses examination of a person's eyesight?",
                10,
                True,
                False,
                0.1,
            )

        assert [item["id"] for item in result] == [
            "source:medical",
            "source:finance",
            "source:vehicle",
        ]
        assert [item["similarity"] for item in result] == [
            0.548259,
            0.389266,
            0.353189,
        ]

    @pytest.mark.asyncio
    async def test_tie_break_is_deterministic_by_id(self):
        from open_notebook.domain import notebook as notebook_module

        tied = [
            {"id": "source:b", "similarity": 0.5},
            {"id": "source:a", "similarity": 0.5},
            {"id": "source:c", "similarity": 0.4},
        ]
        with (
            patch(
                "open_notebook.utils.embedding.generate_embedding",
                new_callable=AsyncMock,
                return_value=[0.1],
            ),
            patch.object(
                notebook_module,
                "repo_query",
                new_callable=AsyncMock,
                return_value=tied,
            ),
        ):
            result = await notebook_module.vector_search("q", 3)

        assert [item["id"] for item in result] == [
            "source:a",
            "source:b",
            "source:c",
        ]


def _found(*ids):
    return [{"id": nb_id} for nb_id in ids]


class TestNotebookScopedSearchApi:
    """POST /api/search accepts a notebook scope and forwards it (#574, #87)."""

    @patch("api.routers.search.repo_query", new_callable=AsyncMock)
    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_notebook_ids_are_forwarded_to_text_search(
        self, mock_text_search, mock_query, client
    ):
        mock_query.return_value = _found("notebook:a", "notebook:b")
        mock_text_search.return_value = []
        response = client.post(
            "/api/search",
            json={
                "query": "x",
                "type": "text",
                "notebook_ids": ["notebook:a", "notebook:b"],
            },
        )
        assert response.status_code == 200
        assert mock_text_search.await_args is not None
        assert mock_text_search.await_args.kwargs["notebook_ids"] == [
            "notebook:a",
            "notebook:b",
        ]
        # Existence is checked with a single query for the whole scope.
        mock_query.assert_awaited_once()

    @patch("api.routers.search.repo_query", new_callable=AsyncMock)
    @patch(
        "api.routers.search.model_manager.get_embedding_model", new_callable=AsyncMock
    )
    @patch("api.routers.search.vector_search", new_callable=AsyncMock)
    def test_single_notebook_id_is_forwarded_to_vector_search(
        self, mock_vector_search, mock_embedding, mock_query, client
    ):
        """`notebook_id` (the #574 shape, already sent by clients) is honored too."""
        mock_query.return_value = _found("notebook:a")
        mock_embedding.return_value = object()
        mock_vector_search.return_value = []
        response = client.post(
            "/api/search",
            json={"query": "x", "type": "vector", "notebook_id": "notebook:a"},
        )
        assert response.status_code == 200
        assert mock_vector_search.await_args is not None
        assert mock_vector_search.await_args.kwargs["notebook_ids"] == ["notebook:a"]

    @patch("api.routers.search.repo_query", new_callable=AsyncMock)
    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_no_scope_means_global_search(self, mock_text_search, mock_query, client):
        mock_text_search.return_value = []
        response = client.post("/api/search", json={"query": "x", "type": "text"})
        assert response.status_code == 200
        assert mock_text_search.await_args is not None
        assert mock_text_search.await_args.kwargs["notebook_ids"] == []
        mock_query.assert_not_awaited()

    @patch("api.routers.search.repo_query", new_callable=AsyncMock)
    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_unknown_notebook_returns_404(self, mock_text_search, mock_query, client):
        mock_query.return_value = _found("notebook:a")
        response = client.post(
            "/api/search",
            json={
                "query": "x",
                "type": "text",
                "notebook_ids": ["notebook:a", "notebook:zzz"],
            },
        )
        assert response.status_code == 404
        assert "notebook:zzz" in response.json()["detail"]
        mock_text_search.assert_not_awaited()

    @patch("api.routers.search.repo_query", new_callable=AsyncMock)
    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_database_failure_during_scope_check_is_not_a_404(
        self, mock_text_search, mock_query, client
    ):
        mock_query.side_effect = RuntimeError("connection refused")
        response = client.post(
            "/api/search",
            json={"query": "x", "type": "text", "notebook_ids": ["notebook:a"]},
        )
        assert response.status_code == 500
        mock_text_search.assert_not_awaited()

    @patch("api.routers.search.repo_query", new_callable=AsyncMock)
    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_non_notebook_id_returns_400(self, mock_text_search, mock_query, client):
        response = client.post(
            "/api/search",
            json={"query": "x", "type": "text", "notebook_ids": ["source:abc"]},
        )
        assert response.status_code == 400
        mock_query.assert_not_awaited()
        mock_text_search.assert_not_awaited()

    @patch("api.routers.search.repo_query", new_callable=AsyncMock)
    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_empty_notebook_id_is_rejected_not_widened(
        self, mock_text_search, mock_query, client
    ):
        response = client.post(
            "/api/search", json={"query": "x", "type": "text", "notebook_id": ""}
        )
        assert response.status_code == 400
        mock_text_search.assert_not_awaited()

    def test_scope_is_bounded(self, client):
        response = client.post(
            "/api/search",
            json={"query": "x", "notebook_ids": [f"notebook:{i}" for i in range(51)]},
        )
        assert response.status_code == 422

    def test_scope_merges_and_dedupes_single_and_list(self):
        from api.models import SearchRequest

        request = SearchRequest(
            query="x",
            notebook_id="notebook:a",
            notebook_ids=["notebook:b", "notebook:a"],
        )
        assert request.scope_notebook_ids == ["notebook:a", "notebook:b"]
        assert SearchRequest(query="x").scope_notebook_ids == []


class TestNotebookScopedSearchDomain:
    """text_search / vector_search bind the scope as record ids (#574, #87)."""

    @pytest.mark.asyncio
    async def test_text_search_binds_notebook_record_ids(self):
        from surrealdb import RecordID

        from open_notebook.domain import notebook as notebook_module

        with patch.object(
            notebook_module, "repo_query", new_callable=AsyncMock, return_value=[]
        ) as mock_query:
            await notebook_module.text_search(
                "hello", 10, notebook_ids=["notebook:a", "notebook:b"]
            )

        assert mock_query.await_args is not None

        query, params = mock_query.await_args.args
        assert "$notebook_ids" in query
        assert params["notebook_ids"] == [
            RecordID("notebook", "a"),
            RecordID("notebook", "b"),
        ]

    @pytest.mark.asyncio
    async def test_empty_scope_binds_none_for_global_search(self):
        from open_notebook.domain import notebook as notebook_module

        with patch.object(
            notebook_module, "repo_query", new_callable=AsyncMock, return_value=[]
        ) as mock_query:
            await notebook_module.text_search("hello", 10, notebook_ids=[])
            await notebook_module.text_search("hello", 10)

        for call in mock_query.await_args_list:
            assert call.args[1]["notebook_ids"] is None

    @pytest.mark.asyncio
    async def test_vector_search_binds_notebook_record_ids(self):
        from surrealdb import RecordID

        from open_notebook.domain import notebook as notebook_module

        with (
            patch(
                "open_notebook.utils.embedding.generate_embedding",
                new_callable=AsyncMock,
                return_value=[0.1],
            ),
            patch.object(
                notebook_module, "repo_query", new_callable=AsyncMock, return_value=[]
            ) as mock_query,
        ):
            await notebook_module.vector_search("q", 3, notebook_ids=["notebook:a"])

        assert mock_query.await_args is not None

        query, params = mock_query.await_args.args
        assert "$notebook_ids" in query
        assert params["notebook_ids"] == [RecordID("notebook", "a")]
