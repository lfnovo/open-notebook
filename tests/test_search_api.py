from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

MIGRATIONS_DIR = Path("open_notebook/database/migrations")


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

    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
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

    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
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

    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_no_scope_means_global_search(self, mock_text_search, mock_query, client):
        mock_text_search.return_value = []
        response = client.post("/api/search", json={"query": "x", "type": "text"})
        assert response.status_code == 200
        assert mock_text_search.await_args is not None
        assert mock_text_search.await_args.kwargs["notebook_ids"] == []
        mock_query.assert_not_awaited()

    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
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

    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_database_failure_during_scope_check_is_not_a_404(
        self, mock_text_search, mock_query, client
    ):
        mock_query.side_effect = RuntimeError("connection refused ws://db:8000")
        response = client.post(
            "/api/search",
            json={"query": "x", "type": "text", "notebook_ids": ["notebook:a"]},
        )
        assert response.status_code == 500
        # The raw driver error stays in the server log, not in the response.
        assert "ws://db:8000" not in response.text
        mock_text_search.assert_not_awaited()

    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
    @patch("api.routers.search.text_search", new_callable=AsyncMock)
    def test_non_notebook_id_returns_400(self, mock_text_search, mock_query, client):
        response = client.post(
            "/api/search",
            json={"query": "x", "type": "text", "notebook_ids": ["source:abc"]},
        )
        assert response.status_code == 400
        mock_query.assert_not_awaited()
        mock_text_search.assert_not_awaited()

    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
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


class TestAskScopeValidationOrder:
    """/search/ask validates the scope before touching models (#574, #87)."""

    @patch("api.routers.search.Model.get", new_callable=AsyncMock)
    @patch("open_notebook.domain.notebook.repo_query", new_callable=AsyncMock)
    def test_unknown_scope_fails_before_model_lookup(
        self, mock_query, mock_model_get, client
    ):
        mock_query.return_value = []
        response = client.post(
            "/api/search/ask",
            json={
                "question": "q",
                "strategy_model": "model:s",
                "answer_model": "model:a",
                "final_answer_model": "model:f",
                "notebook_ids": ["notebook:zzz"],
            },
        )
        assert response.status_code == 404
        mock_model_get.assert_not_awaited()


class TestMigration24:
    """Migration 24 adds the optional notebook scope to both search functions
    and is registered in AsyncMigrationManager (migrations are hard-coded,
    not auto-discovered)."""

    def test_migration_files_exist(self):
        assert (MIGRATIONS_DIR / "24.surrealql").is_file()
        assert (MIGRATIONS_DIR / "24_down.surrealql").is_file()

    def test_manager_registers_migration_24(self):
        from open_notebook.database.async_migrate import AsyncMigrationManager

        manager = AsyncMigrationManager()
        assert len(manager.up_migrations) >= 24
        assert len(manager.up_migrations) == len(manager.down_migrations)
        assert "$notebook_ids" in manager.up_migrations[23].sql
        assert "$notebook_ids" not in manager.down_migrations[23].sql

    def test_up_adds_optional_scope_to_both_functions(self):
        sql = (MIGRATIONS_DIR / "24.surrealql").read_text()
        scope_param = "$notebook_ids: option<array<record<notebook>>>"

        assert sql.count("REMOVE FUNCTION IF EXISTS fn::text_search") == 1
        assert sql.count("REMOVE FUNCTION IF EXISTS fn::vector_search") == 1
        assert sql.count(scope_param) == 2
        # Trailing + optional: the previous 4-/5-argument calls keep working.
        assert f"$show_notes: bool, {scope_param})" in sql
        assert f"$min_similarity: float, {scope_param})" in sql
        # Sources follow the `reference` edge, notes the `artifact` edge.
        assert "FROM reference WHERE out IN $notebook_ids" in sql
        assert "FROM artifact WHERE out IN $notebook_ids" in sql
        # Empty or absent scope must keep the unfiltered path.
        assert "$notebook_ids != NONE AND array::len($notebook_ids) > 0" in sql

    def test_down_restores_unscoped_signatures(self):
        sql = (MIGRATIONS_DIR / "24_down.surrealql").read_text()

        assert "$notebook_ids" not in sql
        assert "$match_count: int, $sources:bool, $show_notes:bool)" in sql
        assert "$show_notes: bool, $min_similarity: float)" in sql


class TestResolveNotebookScope:
    """resolve_notebook_scope() validates ids before any search runs (#574, #87)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad_id", ["", "notebook:", "source:abc", "abc"])
    async def test_malformed_ids_raise_invalid_input(self, bad_id):
        from open_notebook.domain import notebook as notebook_module
        from open_notebook.exceptions import InvalidInputError

        with patch.object(
            notebook_module, "repo_query", new_callable=AsyncMock
        ) as mock_query:
            with pytest.raises(InvalidInputError):
                await notebook_module.resolve_notebook_scope([bad_id])
        mock_query.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_scope_skips_the_database(self):
        from open_notebook.domain import notebook as notebook_module

        with patch.object(
            notebook_module, "repo_query", new_callable=AsyncMock
        ) as mock_query:
            assert await notebook_module.resolve_notebook_scope([]) == []
        mock_query.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_notebooks_raise_not_found_listing_them(self):
        from open_notebook.domain import notebook as notebook_module
        from open_notebook.exceptions import NotFoundError

        with patch.object(
            notebook_module,
            "repo_query",
            new_callable=AsyncMock,
            return_value=[{"id": "notebook:a"}],
        ):
            with pytest.raises(NotFoundError, match="notebook:zzz"):
                await notebook_module.resolve_notebook_scope(
                    ["notebook:a", "notebook:zzz"]
                )

    @pytest.mark.asyncio
    async def test_record_id_rows_from_driver_match_request_strings(self):
        """The real driver returns RecordID objects, not strings (regression)."""
        from surrealdb import RecordID

        from open_notebook.domain import notebook as notebook_module

        with patch.object(
            notebook_module,
            "repo_query",
            new_callable=AsyncMock,
            return_value=[{"id": RecordID("notebook", "a")}],
        ):
            assert await notebook_module.resolve_notebook_scope(["notebook:a"]) == [
                "notebook:a"
            ]


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
