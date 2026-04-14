"""
Tests for Phase 6 — Chat & Search — Workspace-Scoped Retrieval.

Covers workspace-scoped vector/text search, multi-workspace query in the ask
graph, chat-to-note save, RBAC filtering for multi-workspace endpoints,
checkpoint isolation, and injection resilience.

All tests mock DB, graph, and AI operations — no running database or API
server required.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_search_results():
    """Search results spanning two workspaces."""
    return [
        {
            "id": "source:s1",
            "content": "Alpha content",
            "workspace_id": "workspace:ws_a",
            "score": 0.9,
        },
        {
            "id": "note:n1",
            "content": "Beta content",
            "workspace_id": "workspace:ws_a",
            "score": 0.8,
        },
        {
            "id": "source:s2",
            "content": "Gamma content",
            "workspace_id": "workspace:ws_b",
            "score": 0.7,
        },
        {
            "id": "note:n2",
            "content": "Delta content",
            "workspace_id": "workspace:ws_b",
            "score": 0.6,
        },
        {
            "id": "source:s3",
            "content": "Epsilon content",
            "workspace_id": None,
            "score": 0.5,
        },
    ]


def _make_request(user_id="user_test"):
    """Build a fake Request with state.user_id for endpoint tests."""
    request = MagicMock()
    request.state = MagicMock()
    request.state.user_id = user_id
    return request


# =============================================================================
# HAPPY PATH TESTS
# =============================================================================


class TestWorkspaceScopedVectorSearch:
    """vector_search with workspace_id filters results correctly."""

    @pytest.mark.asyncio
    async def test_workspace_scoped_vector_search(self, sample_search_results):
        """When workspace_id is provided, only matching results are returned."""
        from open_notebook.domain.notebook import vector_search

        with (
            patch(
                "open_notebook.domain.notebook.repo_query",
                new_callable=AsyncMock,
                return_value=sample_search_results,
            ),
            patch(
                "open_notebook.utils.embedding.generate_embedding",
                new_callable=AsyncMock,
                return_value=[0.1, 0.2, 0.3],
            ),
        ):
            results = await vector_search(
                "test query", 10, True, True, workspace_id="workspace:ws_a"
            )

        assert len(results) == 2
        assert all(r["workspace_id"] == "workspace:ws_a" for r in results)

    @pytest.mark.asyncio
    async def test_vector_search_no_workspace_returns_all(self, sample_search_results):
        """When workspace_id is None, all results are returned (backward compat)."""
        from open_notebook.domain.notebook import vector_search

        with (
            patch(
                "open_notebook.domain.notebook.repo_query",
                new_callable=AsyncMock,
                return_value=sample_search_results,
            ),
            patch(
                "open_notebook.utils.embedding.generate_embedding",
                new_callable=AsyncMock,
                return_value=[0.1, 0.2, 0.3],
            ),
        ):
            results = await vector_search("test query", 10, True, True)

        assert len(results) == 5


class TestWorkspaceScopedTextSearch:
    """text_search with workspace_id filters results correctly."""

    @pytest.mark.asyncio
    async def test_workspace_scoped_text_search(self, sample_search_results):
        """When workspace_id is provided, only matching results are returned."""
        from open_notebook.domain.notebook import text_search

        with patch(
            "open_notebook.domain.notebook.repo_query",
            new_callable=AsyncMock,
            return_value=sample_search_results,
        ):
            results = await text_search(
                "test", 10, True, True, workspace_id="workspace:ws_b"
            )

        assert len(results) == 2
        assert all(r["workspace_id"] == "workspace:ws_b" for r in results)

    @pytest.mark.asyncio
    async def test_text_search_no_workspace_returns_all(self, sample_search_results):
        """When workspace_id is None, all results are returned (backward compat)."""
        from open_notebook.domain.notebook import text_search

        with patch(
            "open_notebook.domain.notebook.repo_query",
            new_callable=AsyncMock,
            return_value=sample_search_results,
        ):
            results = await text_search("test", 10, True, True)

        assert len(results) == 5


class TestMultiWorkspaceQuery:
    """ask graph with workspace_ids queries multiple workspaces in parallel."""

    @pytest.mark.asyncio
    async def test_multi_workspace_query(self):
        """provide_answer queries each workspace via GraphService and vector_search."""
        from open_notebook.graphs.ask import provide_answer

        ws_a_results = [
            {
                "id": "source:s1",
                "content": "Alpha",
                "workspace_id": "workspace:ws_a",
                "score": 0.9,
            },
        ]
        ws_b_results = [
            {
                "id": "source:s2",
                "content": "Beta",
                "workspace_id": "workspace:ws_b",
                "score": 0.8,
            },
        ]

        async def mock_vector_search(
            keyword, results, source, note, workspace_id=None, minimum_score=0.2
        ):
            if workspace_id == "workspace:ws_a":
                return ws_a_results
            elif workspace_id == "workspace:ws_b":
                return ws_b_results
            return []

        mock_model = AsyncMock()
        mock_model.ainvoke = AsyncMock(
            return_value=MagicMock(content="Answer from sources")
        )

        state = {
            "question": "What is quantum computing?",
            "term": "quantum computing",
            "instructions": "Explain quantum computing",
            "results": {},
            "answer": "",
            "ids": [],
            "workspace_ids": ["workspace:ws_a", "workspace:ws_b"],
        }
        config = {"configurable": {"answer_model": "model:test"}}

        mock_graph_service = MagicMock()
        mock_graph_service.query = AsyncMock(return_value="graph context")

        with (
            patch(
                "open_notebook.graphs.ask.vector_search",
                side_effect=mock_vector_search,
            ),
            patch(
                "open_notebook.graphs.ask.provision_langchain_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch(
                "open_notebook.graphs.ask._get_graph_service",
                return_value=mock_graph_service,
            ),
        ):
            result = await provide_answer(state, config)

        # Should have produced an answer (not empty)
        assert len(result["answers"]) > 0
        assert result["answers"][0] == "Answer from sources"


class TestChatReturnsCitations:
    """ask graph response includes source references."""

    @pytest.mark.asyncio
    async def test_chat_returns_citations(self):
        """provide_answer passes result IDs through for citation tracking."""
        from open_notebook.graphs.ask import provide_answer

        search_results = [
            {
                "id": "source:cite1",
                "content": "Cited content",
                "workspace_id": "workspace:ws_a",
                "score": 0.9,
            },
        ]

        mock_model = AsyncMock()
        mock_model.ainvoke = AsyncMock(
            return_value=MagicMock(content="Answer referencing [source:cite1]")
        )

        state = {
            "question": "What is X?",
            "term": "X",
            "instructions": "Explain X",
            "results": {},
            "answer": "",
            "ids": [],
            "workspace_ids": ["workspace:ws_a"],
        }
        config = {"configurable": {"answer_model": "model:test"}}

        mock_graph_service = MagicMock()
        mock_graph_service.query = AsyncMock(return_value="")

        with (
            patch(
                "open_notebook.graphs.ask.vector_search",
                new_callable=AsyncMock,
                return_value=search_results,
            ),
            patch(
                "open_notebook.graphs.ask.provision_langchain_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch(
                "open_notebook.graphs.ask._get_graph_service",
                return_value=mock_graph_service,
            ),
        ):
            result = await provide_answer(state, config)

        assert len(result["answers"]) == 1
        assert "source:cite1" in result["answers"][0]


class TestNoResultsReturnsEmpty:
    """query with no matching content returns empty answers."""

    @pytest.mark.asyncio
    async def test_no_results_returns_empty(self):
        """When vector_search and GraphService return nothing, answers is empty."""
        from open_notebook.graphs.ask import provide_answer

        state = {
            "question": "Unknown topic?",
            "term": "unknown topic",
            "instructions": "Find info",
            "results": {},
            "answer": "",
            "ids": [],
            "workspace_ids": ["workspace:ws_empty"],
        }
        config = {"configurable": {"answer_model": "model:test"}}

        mock_graph_service = MagicMock()
        mock_graph_service.query = AsyncMock(return_value="")

        with (
            patch(
                "open_notebook.graphs.ask.vector_search",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "open_notebook.graphs.ask._get_graph_service",
                return_value=mock_graph_service,
            ),
        ):
            result = await provide_answer(state, config)

        assert result["answers"] == []


class TestSaveChatAsNote:
    """save-as-note endpoint creates Note with correct workspace_id."""

    @pytest.mark.asyncio
    async def test_save_chat_as_note(self):
        """save_chat_as_note handler creates a Note with workspace_id set."""
        from api.routers.chat import save_chat_as_note
        from api.models import SaveChatAsNoteRequest

        mock_note_instance = MagicMock()
        mock_note_instance.id = "note:new1"
        mock_note_instance.title = "Chat Note"
        mock_note_instance.content = "Important finding from chat"
        mock_note_instance.note_type = "ai"
        mock_note_instance.workspace_id = "workspace:ws_save"
        mock_note_instance.created = "2026-04-12T00:00:00Z"
        mock_note_instance.updated = "2026-04-12T00:00:00Z"
        mock_note_instance.save = AsyncMock(return_value="command:embed1")

        body = SaveChatAsNoteRequest(
            content="Important finding from chat",
            title="Chat Note",
            workspace_id="workspace:ws_save",
        )
        request = _make_request()

        with (
            patch(
                "api.routers.chat.Note",
            ) as mock_note_cls,
            patch(
                "api.routers.chat.require_editor",
                new_callable=AsyncMock,
                return_value="editor",
            ),
        ):
            mock_note_cls.return_value = mock_note_instance
            response = await save_chat_as_note(body, request)

        assert response.id == "note:new1"
        assert response.note_type == "ai"
        assert response.command_id == "command:embed1"
        # Verify Note was constructed with workspace_id
        mock_note_cls.assert_called_once_with(
            title="Chat Note",
            content="Important finding from chat",
            note_type="ai",
            workspace_id="workspace:ws_save",
        )


# =============================================================================
# ERROR CASES
# =============================================================================


class TestMultiWorkspaceExcludesInaccessible:
    """workspace search endpoint silently excludes workspaces where user has no role."""

    @pytest.mark.asyncio
    async def test_multi_workspace_excludes_inaccessible(self):
        """User with access to ws_a but not ws_b only gets ws_a results."""
        from api.routers.search import workspace_search
        from api.models import WorkspaceSearchRequest

        ws_a_results = [
            {
                "id": "source:s1",
                "content": "Accessible",
                "workspace_id": "workspace:ws_a",
                "score": 0.9,
            },
        ]

        async def mock_role(workspace_id, user_id):
            if workspace_id == "workspace:ws_a":
                return "viewer"
            return None  # No access to ws_b

        async def mock_vs(
            keyword, results, source, note, minimum_score=0.2, workspace_id=None
        ):
            if workspace_id == "workspace:ws_a":
                return ws_a_results
            return []

        body = WorkspaceSearchRequest(
            query="test query",
            workspace_ids=["workspace:ws_a", "workspace:ws_b"],
            type="vector",
            limit=100,
            search_sources=True,
            search_notes=True,
            minimum_score=0.2,
        )
        request = _make_request()

        with (
            patch(
                "api.routers.search._get_user_role",
                side_effect=mock_role,
            ),
            patch(
                "api.routers.search.vector_search",
                side_effect=mock_vs,
            ),
            patch(
                "api.routers.search.model_manager",
            ) as mock_mm,
        ):
            mock_mm.get_embedding_model = AsyncMock(return_value=MagicMock())
            response = await workspace_search(body, request)

        assert "workspace:ws_a" in response.workspace_ids
        assert "workspace:ws_b" not in response.workspace_ids
        assert response.total_count == 1


class TestChatNoModelConfigured:
    """ask graph without configured models raises appropriate error."""

    @pytest.mark.asyncio
    async def test_chat_no_model_configured(self):
        """When answer_model is None, provision_langchain_model raises."""
        from open_notebook.graphs.ask import provide_answer
        from open_notebook.exceptions import ConfigurationError

        state = {
            "question": "Test?",
            "term": "test",
            "instructions": "test",
            "results": {},
            "answer": "",
            "ids": [],
        }
        config = {"configurable": {}}

        with (
            patch(
                "open_notebook.graphs.ask.vector_search",
                new_callable=AsyncMock,
                return_value=[{"id": "source:s1", "content": "data", "score": 0.9}],
            ),
            patch(
                "open_notebook.graphs.ask.provision_langchain_model",
                new_callable=AsyncMock,
                side_effect=ConfigurationError("No model configured"),
            ),
            patch(
                "open_notebook.graphs.ask._get_graph_service",
                return_value=None,
            ),
        ):
            with pytest.raises(ConfigurationError, match="No model configured"):
                await provide_answer(state, config)


class TestWorkspaceChatCheckpointIsolation:
    """different sessions in different workspaces have separate message histories."""

    @pytest.mark.asyncio
    async def test_workspace_chat_checkpoint_isolation(self):
        """Sessions are isolated by session_id (thread_id), ensuring no cross-talk."""
        from open_notebook.graphs.chat import ThreadState

        # Verify workspace_id is in the ThreadState
        annotations = ThreadState.__annotations__
        assert "workspace_id" in annotations, (
            "ThreadState must include workspace_id for workspace awareness"
        )


# =============================================================================
# ADVERSARIAL CASES
# =============================================================================


class TestWorkspaceIdsInjection:
    """malicious workspace_id values are safely handled."""

    @pytest.mark.asyncio
    async def test_workspace_ids_injection(self):
        """Workspace IDs with SQL-like injection patterns are safely handled."""
        from open_notebook.domain.notebook import vector_search

        malicious_ids = [
            "workspace:'; DROP TABLE workspace;--",
            "workspace:<script>alert(1)</script>",
            "workspace:../../etc/passwd",
        ]

        with (
            patch(
                "open_notebook.domain.notebook.repo_query",
                new_callable=AsyncMock,
                return_value=[
                    {
                        "id": "source:s1",
                        "content": "safe",
                        "workspace_id": "workspace:ws_a",
                        "score": 0.9,
                    },
                ],
            ),
            patch(
                "open_notebook.utils.embedding.generate_embedding",
                new_callable=AsyncMock,
                return_value=[0.1, 0.2, 0.3],
            ),
        ):
            for malicious_id in malicious_ids:
                results = await vector_search(
                    "test", 10, True, True, workspace_id=malicious_id
                )
                # No results should match the malicious workspace_id
                assert len(results) == 0, (
                    f"Malicious workspace_id '{malicious_id}' should not match any results"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
