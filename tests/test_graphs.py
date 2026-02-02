"""
Unit tests for the open_notebook.graphs module.

This test suite focuses on testing graph structures, tools, and validation
without heavy mocking of the actual processing logic.
"""

from datetime import datetime

import pytest

from open_notebook.graphs.prompt import PatternChainState, graph
from open_notebook.graphs.tools import get_current_timestamp
from open_notebook.graphs.transformation import (
    ChunkResult,
    ChunkState,
    TransformationState,
    _extract_response_content,
    _get_content,
    _get_source,
    fan_out_chunks,
    try_full_content,
)
from open_notebook.graphs.transformation import (
    graph as transformation_graph,
)

# ============================================================================
# TEST SUITE 1: Graph Tools
# ============================================================================


class TestGraphTools:
    """Test suite for graph tool definitions."""

    def test_get_current_timestamp_format(self):
        """Test timestamp tool returns correct format."""
        timestamp = get_current_timestamp.func()

        assert isinstance(timestamp, str)
        assert len(timestamp) == 14  # YYYYMMDDHHmmss format
        assert timestamp.isdigit()

    def test_get_current_timestamp_validity(self):
        """Test timestamp represents valid datetime."""
        timestamp = get_current_timestamp.func()

        # Parse it back to datetime to verify validity
        year = int(timestamp[0:4])
        month = int(timestamp[4:6])
        day = int(timestamp[6:8])
        hour = int(timestamp[8:10])
        minute = int(timestamp[10:12])
        second = int(timestamp[12:14])

        # Should be valid date components
        assert 2020 <= year <= 2100
        assert 1 <= month <= 12
        assert 1 <= day <= 31
        assert 0 <= hour <= 23
        assert 0 <= minute <= 59
        assert 0 <= second <= 59

        # Should parse as datetime
        dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
        assert isinstance(dt, datetime)

    def test_get_current_timestamp_is_tool(self):
        """Test that function is properly decorated as a tool."""
        # Check it has tool attributes
        assert hasattr(get_current_timestamp, "name")
        assert hasattr(get_current_timestamp, "description")


# ============================================================================
# TEST SUITE 2: Prompt Graph State
# ============================================================================


class TestPromptGraph:
    """Test suite for prompt pattern chain graph."""

    def test_pattern_chain_state_structure(self):
        """Test PatternChainState structure and fields."""
        state = PatternChainState(
            prompt="Test prompt", parser=None, input_text="Test input", output=""
        )

        assert state["prompt"] == "Test prompt"
        assert state["parser"] is None
        assert state["input_text"] == "Test input"
        assert state["output"] == ""

    def test_prompt_graph_compilation(self):
        """Test that prompt graph compiles correctly."""
        assert graph is not None

        # Graph should have the expected structure
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")


# ============================================================================
# TEST SUITE 3: Transformation Graph
# ============================================================================


class TestTransformationGraph:
    """Test suite for transformation graph workflows."""

    def test_transformation_state_structure(self):
        """Test TransformationState structure and fields."""
        from unittest.mock import MagicMock

        from open_notebook.domain.notebook import Source
        from open_notebook.domain.transformation import Transformation

        mock_source = MagicMock(spec=Source)
        mock_transformation = MagicMock(spec=Transformation)

        state = TransformationState(
            input_text="Test text",
            source=mock_source,
            transformation=mock_transformation,
            output="",
        )

        assert state["input_text"] == "Test text"
        assert state["source"] == mock_source
        assert state["transformation"] == mock_transformation
        assert state["output"] == ""

    @pytest.mark.asyncio
    async def test_try_full_content_assertion_no_content(self):
        """Test transformation raises assertion with no content."""
        from unittest.mock import MagicMock

        from open_notebook.domain.transformation import Transformation

        mock_transformation = MagicMock(spec=Transformation)

        state = {
            "input_text": None,
            "transformation": mock_transformation,
            "source": None,
        }

        config = {"configurable": {"model_id": None}}

        with pytest.raises(AssertionError, match="No content to transform"):
            await try_full_content(state, config)

    def test_transformation_graph_compilation(self):
        """Test that transformation graph compiles correctly."""
        assert transformation_graph is not None
        assert hasattr(transformation_graph, "invoke")
        assert hasattr(transformation_graph, "ainvoke")

    def test_transformation_graph_has_expected_nodes(self):
        """Test that transformation graph has all expected nodes."""
        node_names = list(transformation_graph.nodes.keys())
        assert "try_full" in node_names
        assert "process_chunk" in node_names
        assert "synthesize" in node_names


# ============================================================================
# TEST SUITE 4: Transformation Helper Functions
# ============================================================================


class TestTransformationHelpers:
    """Test suite for transformation helper functions."""

    def test_get_source_with_valid_source(self):
        """Test _get_source returns Source when present."""
        from unittest.mock import MagicMock

        from open_notebook.domain.notebook import Source

        mock_source = MagicMock(spec=Source)
        state = {"source": mock_source}

        result = _get_source(state)
        assert result == mock_source

    def test_get_source_with_none(self):
        """Test _get_source returns None when source is None."""
        state = {"source": None}
        result = _get_source(state)
        assert result is None

    def test_get_source_with_non_source_object(self):
        """Test _get_source returns None for non-Source objects."""
        state = {"source": "not a source"}
        result = _get_source(state)
        assert result is None

    def test_get_source_with_missing_key(self):
        """Test _get_source returns None when key is missing."""
        state = {}
        result = _get_source(state)
        assert result is None

    def test_extract_response_content_string(self):
        """Test _extract_response_content with string content."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.content = "Test response content"

        result = _extract_response_content(mock_response)
        assert result == "Test response content"

    def test_extract_response_content_with_thinking_tags(self):
        """Test _extract_response_content strips thinking tags."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.content = "<think>internal thought</think>Actual response"

        result = _extract_response_content(mock_response)
        assert "<think>" not in result
        assert "Actual response" in result

    def test_extract_response_content_non_string(self):
        """Test _extract_response_content converts non-string to string."""
        from unittest.mock import MagicMock

        mock_response = MagicMock()
        mock_response.content = ["list", "content"]

        result = _extract_response_content(mock_response)
        assert isinstance(result, str)

    def test_get_content_from_input_text(self):
        """Test _get_content extracts from input_text."""
        state = {"input_text": "Test input content", "source": None}
        result = _get_content(state)
        assert result == "Test input content"

    def test_get_content_from_source(self):
        """Test _get_content falls back to source.full_text."""
        from unittest.mock import MagicMock

        from open_notebook.domain.notebook import Source

        mock_source = MagicMock(spec=Source)
        mock_source.full_text = "Source full text content"

        state = {"input_text": None, "source": mock_source}
        result = _get_content(state)
        assert result == "Source full text content"

    def test_get_content_empty_state(self):
        """Test _get_content returns empty string for empty state."""
        state = {"input_text": None, "source": None}
        result = _get_content(state)
        assert result == ""


# ============================================================================
# TEST SUITE 5: Chunk Fan-Out Function
# ============================================================================


class TestFanOutChunks:
    """Test suite for fan_out_chunks conditional edge function."""

    def test_fan_out_returns_synthesize_when_no_chunking_needed(self):
        """Test fan_out_chunks routes to synthesize when needs_chunking is False."""
        state = {"needs_chunking": False}
        result = fan_out_chunks(state)
        assert result == "synthesize"

    def test_fan_out_returns_synthesize_when_needs_chunking_missing(self):
        """Test fan_out_chunks routes to synthesize when needs_chunking key missing."""
        state = {}
        result = fan_out_chunks(state)
        assert result == "synthesize"

    def test_fan_out_returns_synthesize_when_chunks_empty(self):
        """Test fan_out_chunks routes to synthesize when chunks list is empty."""
        state = {"needs_chunking": True, "chunks": []}
        result = fan_out_chunks(state)
        assert result == "synthesize"

    def test_fan_out_returns_synthesize_when_chunks_missing(self):
        """Test fan_out_chunks routes to synthesize when chunks key missing."""
        state = {"needs_chunking": True}
        result = fan_out_chunks(state)
        assert result == "synthesize"

    def test_fan_out_returns_send_objects_for_chunks(self):
        """Test fan_out_chunks returns Send objects for each chunk."""
        from langgraph.types import Send

        state = {
            "needs_chunking": True,
            "chunks": ["chunk1", "chunk2", "chunk3"],
            "system_prompt": "Test prompt",
            "model_id": "test-model",
            "output_buffer": 1000,
            "title": "Test Transformation",
        }

        result = fan_out_chunks(state)

        assert isinstance(result, list)
        assert len(result) == 3
        for item in result:
            assert isinstance(item, Send)

    def test_fan_out_send_objects_have_correct_node(self):
        """Test Send objects target the process_chunk node."""
        from langgraph.types import Send

        state = {
            "needs_chunking": True,
            "chunks": ["chunk1"],
            "system_prompt": "Test prompt",
            "model_id": None,
            "output_buffer": 1000,
            "title": "Test",
        }

        result = fan_out_chunks(state)

        assert len(result) == 1
        assert result[0].node == "process_chunk"

    def test_fan_out_send_objects_have_correct_state(self):
        """Test Send objects contain correct chunk state."""
        state = {
            "needs_chunking": True,
            "chunks": ["First chunk", "Second chunk"],
            "system_prompt": "System prompt text",
            "model_id": "model-123",
            "output_buffer": 2000,
            "title": "My Transform",
        }

        result = fan_out_chunks(state)

        # Check first chunk
        first_send = result[0]
        assert first_send.arg["chunk"] == "First chunk"
        assert first_send.arg["chunk_idx"] == 0
        assert first_send.arg["total_chunks"] == 2
        assert first_send.arg["system_prompt"] == "System prompt text"
        assert first_send.arg["model_id"] == "model-123"
        assert first_send.arg["output_buffer"] == 2000
        assert first_send.arg["title"] == "My Transform"

        # Check second chunk
        second_send = result[1]
        assert second_send.arg["chunk"] == "Second chunk"
        assert second_send.arg["chunk_idx"] == 1
        assert second_send.arg["total_chunks"] == 2


# ============================================================================
# TEST SUITE 6: Chunk State Structures
# ============================================================================


class TestChunkStateStructures:
    """Test suite for ChunkState and ChunkResult TypedDicts."""

    def test_chunk_result_structure(self):
        """Test ChunkResult has correct structure."""
        result: ChunkResult = {"idx": 0, "result": "Processed content"}

        assert result["idx"] == 0
        assert result["result"] == "Processed content"

    def test_chunk_state_structure(self):
        """Test ChunkState has correct structure."""
        state: ChunkState = {
            "system_prompt": "You are a helpful assistant",
            "model_id": "gpt-4",
            "output_buffer": 1000,
            "title": "Summary",
            "chunk": "Content to process",
            "chunk_idx": 2,
            "total_chunks": 5,
        }

        assert state["system_prompt"] == "You are a helpful assistant"
        assert state["model_id"] == "gpt-4"
        assert state["output_buffer"] == 1000
        assert state["title"] == "Summary"
        assert state["chunk"] == "Content to process"
        assert state["chunk_idx"] == 2
        assert state["total_chunks"] == 5

    def test_chunk_state_with_none_model_id(self):
        """Test ChunkState allows None for model_id."""
        state: ChunkState = {
            "system_prompt": "Prompt",
            "model_id": None,
            "output_buffer": 500,
            "title": "Test",
            "chunk": "Data",
            "chunk_idx": 0,
            "total_chunks": 1,
        }

        assert state["model_id"] is None


# ============================================================================
# TEST SUITE 7: Synthesize Results Function
# ============================================================================


class TestSynthesizeResults:
    """Test suite for synthesize_results function."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_empty_when_output_exists(self):
        """Test synthesize_results returns empty dict when output already set."""
        from open_notebook.graphs.transformation import synthesize_results

        state = {
            "output": "Already computed output",
            "needs_chunking": False,
            "transformation": MagicMock(title="Test"),
        }
        config = {"configurable": {}}

        result = await synthesize_results(state, config)
        assert result == {}

    @pytest.mark.asyncio
    async def test_synthesize_returns_empty_output_when_no_chunks(self):
        """Test synthesize_results returns empty output when no chunk_results."""
        from open_notebook.graphs.transformation import synthesize_results

        state = {
            "output": None,
            "needs_chunking": True,
            "chunk_results": [],
            "transformation": MagicMock(title="Test"),
            "title": "Test",
        }
        config = {"configurable": {}}

        result = await synthesize_results(state, config)
        assert result == {"output": ""}


# Import MagicMock at module level for the synthesize tests
from unittest.mock import MagicMock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
