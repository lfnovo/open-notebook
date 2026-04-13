"""
Tests for Phase 5 — Graph Service (LightRAG per Workspace).

Covers per-workspace LightRAG instance management, graph insertion/query,
LRU eviction, graceful degradation, and source pipeline integration.

All tests mock LightRAG and DB operations — no running database or
LightRAG installation required.
"""

import asyncio
import os
import shutil
import tempfile
from collections import OrderedDict
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_data_dir(tmp_path):
    """Provide a temporary directory for graph data storage."""
    graphs_dir = tmp_path / "data" / "graphs"
    graphs_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def mock_lightrag_class():
    """Return a mock LightRAG class that produces mock instances."""
    mock_cls = MagicMock()
    mock_instance = AsyncMock()
    mock_instance.ainsert = AsyncMock()
    mock_instance.aquery = AsyncMock(return_value="graph query result")
    mock_instance.adelete_by_entity = AsyncMock()
    mock_cls.return_value = mock_instance
    return mock_cls


@pytest.fixture
def mock_llm_func():
    """Return an async callable that mimics an LLM function for LightRAG."""

    async def fake_llm(*args, **kwargs):
        return "mock llm response"

    return fake_llm


@pytest.fixture
def mock_embedding_func():
    """Return an async callable that mimics an embedding function for LightRAG."""

    async def fake_embed(*args, **kwargs):
        return [[0.1, 0.2, 0.3]]

    return fake_embed


# =============================================================================
# HAPPY PATH TESTS
# =============================================================================


class TestGraphServiceInitCreatesWorkingDir:
    """get_instance for a workspace -> creates data/graphs/{id}/ directory."""

    @pytest.mark.asyncio
    async def test_graph_service_init_creates_working_dir(
        self, temp_data_dir, mock_lightrag_class
    ):
        """Creating a graph instance for a workspace creates the working directory."""
        from open_notebook.services.graph_service import GraphService

        workspace_id = "workspace:ws_test_123"
        expected_dir = temp_data_dir / "data" / "graphs" / "workspace_ws_test_123"

        with (
            patch.object(GraphService, "DATA_ROOT", str(temp_data_dir / "data")),
            patch(
                "open_notebook.services.graph_service._try_import_lightrag",
                return_value=MagicMock(LightRAG=mock_lightrag_class),
            ),
            patch(
                "open_notebook.services.graph_service.build_llm_func",
                return_value=AsyncMock(),
            ),
            patch(
                "open_notebook.services.graph_service.build_embedding_func",
                return_value=AsyncMock(),
            ),
        ):
            GraphService._instances = OrderedDict()
            instance = await GraphService.get_instance(workspace_id)

        assert expected_dir.exists(), f"Expected directory {expected_dir} to be created"
        assert instance is not None


class TestGraphInsertDelegatesToLightrag:
    """insert text -> calls LightRAG.ainsert."""

    @pytest.mark.asyncio
    async def test_graph_insert_delegates_to_lightrag(
        self, temp_data_dir, mock_lightrag_class
    ):
        """Inserting text delegates to the LightRAG instance's ainsert method."""
        from open_notebook.services.graph_service import GraphService

        workspace_id = "workspace:ws_insert"
        text_content = "Knowledge about quantum computing and its applications."

        with (
            patch.object(GraphService, "DATA_ROOT", str(temp_data_dir / "data")),
            patch(
                "open_notebook.services.graph_service._try_import_lightrag",
                return_value=MagicMock(LightRAG=mock_lightrag_class),
            ),
            patch(
                "open_notebook.services.graph_service.build_llm_func",
                return_value=AsyncMock(),
            ),
            patch(
                "open_notebook.services.graph_service.build_embedding_func",
                return_value=AsyncMock(),
            ),
        ):
            GraphService._instances = OrderedDict()
            await GraphService.insert(workspace_id, text_content)

        mock_lightrag_class.return_value.ainsert.assert_awaited_once_with(text_content)


class TestGraphQueryDelegatesToLightrag:
    """query -> calls LightRAG.aquery with hybrid mode."""

    @pytest.mark.asyncio
    async def test_graph_query_delegates_to_lightrag(
        self, temp_data_dir, mock_lightrag_class
    ):
        """Querying delegates to LightRAG's aquery with hybrid search mode."""
        from open_notebook.services.graph_service import GraphService

        workspace_id = "workspace:ws_query"
        query_text = "What is quantum entanglement?"

        with (
            patch.object(GraphService, "DATA_ROOT", str(temp_data_dir / "data")),
            patch(
                "open_notebook.services.graph_service._try_import_lightrag",
                return_value=MagicMock(LightRAG=mock_lightrag_class),
            ),
            patch(
                "open_notebook.services.graph_service.build_llm_func",
                return_value=AsyncMock(),
            ),
            patch(
                "open_notebook.services.graph_service.build_embedding_func",
                return_value=AsyncMock(),
            ),
        ):
            GraphService._instances = OrderedDict()
            result = await GraphService.query(workspace_id, query_text)

        mock_lightrag_class.return_value.aquery.assert_awaited_once()
        call_args = mock_lightrag_class.return_value.aquery.call_args
        assert call_args[0][0] == query_text
        assert call_args[1].get("param") is not None
        assert result == "graph query result"


class TestGraphIsolationDifferentWorkingDirs:
    """Two workspaces -> different working_dir paths."""

    @pytest.mark.asyncio
    async def test_graph_isolation_different_working_dirs(
        self, temp_data_dir, mock_lightrag_class
    ):
        """Each workspace uses an isolated directory under data/graphs/{workspace_id}/."""
        from open_notebook.services.graph_service import GraphService

        workspace_a = "workspace:ws_a"
        workspace_b = "workspace:ws_b"

        with (
            patch.object(GraphService, "DATA_ROOT", str(temp_data_dir / "data")),
            patch(
                "open_notebook.services.graph_service._try_import_lightrag",
                return_value=MagicMock(LightRAG=mock_lightrag_class),
            ),
            patch(
                "open_notebook.services.graph_service.build_llm_func",
                return_value=AsyncMock(),
            ),
            patch(
                "open_notebook.services.graph_service.build_embedding_func",
                return_value=AsyncMock(),
            ),
        ):
            GraphService._instances = OrderedDict()
            await GraphService.get_instance(workspace_a)
            await GraphService.get_instance(workspace_b)

        # _graph_dir sanitizes ':' to '_' for filesystem safety
        dir_a = temp_data_dir / "data" / "graphs" / workspace_a.replace(":", "_")
        dir_b = temp_data_dir / "data" / "graphs" / workspace_b.replace(":", "_")
        assert dir_a.exists(), f"Expected directory for workspace A: {dir_a}"
        assert dir_b.exists(), f"Expected directory for workspace B: {dir_b}"
        assert dir_a != dir_b, "Workspace directories must be different"


class TestBuildGraphCommandSubmittedAfterSave:
    """Source saved via pipeline -> build_graph command submitted."""

    @pytest.mark.asyncio
    async def test_build_graph_command_submitted_after_save(self):
        """After save_source completes, a build_graph command is submitted."""
        from open_notebook.graphs.source import save_source

        mock_source = AsyncMock()
        mock_source.id = "source:src_graph"
        mock_source.full_text = "Some content for graph extraction"
        mock_source.workspace_id = "workspace:ws_graph"
        mock_source.vectorize = AsyncMock()

        state = {
            "content_state": MagicMock(
                url=None,
                file_path=None,
                content="text",
                title="Test Source",
            ),
            "source_id": "source:src_graph",
            "workspace_id": "workspace:ws_graph",
            "embed": False,
        }

        with (
            patch(
                "open_notebook.graphs.source.Source.get",
                new_callable=AsyncMock,
                return_value=mock_source,
            ),
            patch(
                "open_notebook.graphs.source.submit_command",
                return_value="command:graph_cmd1",
            ) as mock_submit,
        ):
            await save_source(state)

        mock_submit.assert_called_once_with(
            "open_notebook",
            "build_graph",
            {
                "workspace_id": "workspace:ws_graph",
                "source_id": "source:src_graph",
            },
        )


class TestLruEviction:
    """21 instances created -> oldest evicted."""

    @pytest.mark.asyncio
    async def test_lru_eviction(self, temp_data_dir, mock_lightrag_class):
        """After creating 21 instances, only 20 remain (oldest evicted)."""
        from open_notebook.services.graph_service import GraphService

        with (
            patch.object(GraphService, "DATA_ROOT", str(temp_data_dir / "data")),
            patch(
                "open_notebook.services.graph_service._try_import_lightrag",
                return_value=MagicMock(LightRAG=mock_lightrag_class),
            ),
            patch(
                "open_notebook.services.graph_service.build_llm_func",
                return_value=AsyncMock(),
            ),
            patch(
                "open_notebook.services.graph_service.build_embedding_func",
                return_value=AsyncMock(),
            ),
        ):
            GraphService._instances = OrderedDict()
            for idx in range(21):
                await GraphService.get_instance(f"workspace:ws_{idx}")

            assert len(GraphService._instances) == GraphService.MAX_CACHED
            assert "workspace:ws_0" not in GraphService._instances, (
                "Oldest workspace should have been evicted"
            )
            assert "workspace:ws_20" in GraphService._instances, (
                "Newest workspace should still be cached"
            )


# =============================================================================
# ERROR CASES
# =============================================================================


class TestGraphExtractionFailureSetsWarning:
    """insert raises exception -> source graph_status set to 'warning'."""

    @pytest.mark.asyncio
    async def test_graph_extraction_failure_sets_warning(self):
        """When build_graph fails, the source graph_status is set to 'warning'."""
        from commands.graph_commands import build_graph_command, BuildGraphInput

        mock_source = AsyncMock()
        mock_source.id = "source:src_fail"
        mock_source.full_text = "Some content"
        mock_source.workspace_id = "workspace:ws_fail"
        mock_source.graph_status = None
        mock_source.save = AsyncMock()

        mock_input = BuildGraphInput(
            workspace_id="workspace:ws_fail",
            source_id="source:src_fail",
        )

        with (
            patch(
                "commands.graph_commands.Source.get",
                new_callable=AsyncMock,
                return_value=mock_source,
            ),
            patch(
                "commands.graph_commands.GraphService.insert",
                new_callable=AsyncMock,
                side_effect=RuntimeError("LightRAG extraction failed"),
            ),
        ):
            result = await build_graph_command(mock_input)

        assert mock_source.graph_status == "warning"
        mock_source.save.assert_awaited_once()
        assert result.success is False
        assert (
            "warning" in result.error_message.lower()
            or "failed" in result.error_message.lower()
        )


class TestDeleteWorkspaceRemovesGraphDir:
    """delete_workspace -> removes directory."""

    @pytest.mark.asyncio
    async def test_delete_workspace_removes_graph_dir(self, temp_data_dir):
        """Deleting workspace graph data removes its directory."""
        from open_notebook.services.graph_service import GraphService

        workspace_id = "workspace:ws_delete"
        safe_id = workspace_id.replace(":", "_")
        graph_dir = temp_data_dir / "data" / "graphs" / safe_id
        graph_dir.mkdir(parents=True)
        (graph_dir / "some_file.txt").write_text("graph data")

        with patch.object(GraphService, "DATA_ROOT", str(temp_data_dir / "data")):
            GraphService._instances = OrderedDict()
            await GraphService.delete_workspace(workspace_id)

        assert not graph_dir.exists(), (
            f"Expected directory {graph_dir} to be removed after delete"
        )


class TestLightragNotAvailableGraceful:
    """LightRAG import fails -> methods return gracefully."""

    @pytest.mark.asyncio
    async def test_lightrag_not_available_query_returns_empty(self, temp_data_dir):
        """When LightRAG is not installed, query returns an empty string."""
        from open_notebook.services.graph_service import GraphService

        with (
            patch.object(GraphService, "DATA_ROOT", str(temp_data_dir / "data")),
            patch(
                "open_notebook.services.graph_service._try_import_lightrag",
                return_value=None,
            ),
        ):
            GraphService._instances = OrderedDict()
            result = await GraphService.query("workspace:ws_missing", "test query")

        assert result == ""

    @pytest.mark.asyncio
    async def test_lightrag_not_available_insert_is_noop(self, temp_data_dir):
        """When LightRAG is not installed, insert is a no-op (no error)."""
        from open_notebook.services.graph_service import GraphService

        with (
            patch.object(GraphService, "DATA_ROOT", str(temp_data_dir / "data")),
            patch(
                "open_notebook.services.graph_service._try_import_lightrag",
                return_value=None,
            ),
        ):
            GraphService._instances = OrderedDict()
            await GraphService.insert("workspace:ws_missing", "some text")


# =============================================================================
# ADVERSARIAL CASES
# =============================================================================


class TestConcurrentGraphAccess:
    """Multiple concurrent inserts -> no deadlock or corruption."""

    @pytest.mark.asyncio
    async def test_concurrent_graph_access(self, temp_data_dir, mock_lightrag_class):
        """Concurrent inserts to the same workspace complete without error."""
        from open_notebook.services.graph_service import GraphService

        workspace_id = "workspace:ws_concurrent"

        with (
            patch.object(GraphService, "DATA_ROOT", str(temp_data_dir / "data")),
            patch(
                "open_notebook.services.graph_service._try_import_lightrag",
                return_value=MagicMock(LightRAG=mock_lightrag_class),
            ),
            patch(
                "open_notebook.services.graph_service.build_llm_func",
                return_value=AsyncMock(),
            ),
            patch(
                "open_notebook.services.graph_service.build_embedding_func",
                return_value=AsyncMock(),
            ),
        ):
            GraphService._instances = OrderedDict()
            GraphService._lock = asyncio.Lock()

            tasks = [
                GraphService.insert(workspace_id, f"Content batch {idx}")
                for idx in range(10)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, (
            f"Expected no errors from concurrent inserts, got: {errors}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
