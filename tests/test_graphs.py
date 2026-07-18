"""
Unit tests for the open_notebook.graphs module.

This test suite focuses on testing graph structures, tools, and validation
without heavy mocking of the actual processing logic.
"""

from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from open_notebook.domain.notebook import Source
from open_notebook.graphs.prompt import PatternChainState, graph
from open_notebook.graphs.tools import get_current_timestamp
from open_notebook.graphs.transformation import (
    TransformationState,
    _batch_results_by_tokens,
    fan_out_chunks,
    synthesize_results,
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
        timestamp = get_current_timestamp.invoke({})

        assert isinstance(timestamp, str)
        assert len(timestamp) == 14  # YYYYMMDDHHmmss format
        assert timestamp.isdigit()

    def test_get_current_timestamp_validity(self):
        """Test timestamp represents valid datetime."""
        timestamp = get_current_timestamp.invoke({})

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
        """try_full_content raises an assertion when there's no content."""
        from unittest.mock import MagicMock

        from open_notebook.domain.transformation import Transformation

        mock_transformation = MagicMock(spec=Transformation)

        state = {
            "input_text": None,
            "transformation": mock_transformation,
            "source": None,
        }

        config: RunnableConfig = {"configurable": {"model_id": None}}

        with pytest.raises(AssertionError, match="No content to transform"):
            await try_full_content(state, config)

    def test_transformation_graph_compilation(self):
        """Test that transformation graph compiles correctly."""
        assert transformation_graph is not None
        assert hasattr(transformation_graph, "invoke")
        assert hasattr(transformation_graph, "ainvoke")

    def test_fan_out_chunks_routes_to_synthesize_without_chunking(self):
        """fan_out_chunks goes straight to synthesize when no chunking needed."""
        assert fan_out_chunks({"needs_chunking": False}) == "synthesize"
        assert fan_out_chunks({"needs_chunking": True, "chunks": []}) == "synthesize"


class TestTransformationFullContentPath:
    """Tests for the optimistic full-content attempt."""

    @pytest.mark.asyncio
    async def test_full_content_uses_8192_output_cap(self):
        """The full-content attempt must keep the pre-chunking 8192 output cap;
        a lower cap would silently truncate outputs on the common path."""
        from open_notebook.domain.transformation import Transformation

        mock_transformation = MagicMock(spec=Transformation)
        mock_transformation.prompt = "Summarize the document."
        mock_transformation.title = "Summary"

        state = {
            "input_text": "Some short content.",
            "transformation": mock_transformation,
            "source": None,
        }

        resp = MagicMock()
        resp.content = "summary"
        fake_chain = MagicMock()
        fake_chain.ainvoke = AsyncMock(return_value=resp)
        provision = AsyncMock(return_value=fake_chain)

        with patch(
            "open_notebook.graphs.transformation.provision_langchain_model",
            new=provision,
        ):
            result = await try_full_content(state, {"configurable": {}})

        assert result == {"output": "summary", "needs_chunking": False}
        assert provision.await_args.kwargs["max_tokens"] == 8192


class TestProcessChunk:
    """Tests for the parallel chunk processor."""

    @pytest.mark.asyncio
    async def test_chunk_sent_verbatim_with_hint_in_system_prompt(self):
        """The section hint must live in the system prompt, not the user
        content, so it can't bleed into extraction-style outputs."""
        from open_notebook.graphs.transformation import process_chunk

        state = {
            "system_prompt": "Extract all names.",
            "model_id": None,
            "output_buffer": 800,
            "title": "Names",
            "chunk": "Alice met Bob.",
            "chunk_idx": 1,
            "total_chunks": 3,
        }

        resp = MagicMock()
        resp.content = "Alice, Bob"
        fake_chain = MagicMock()
        fake_chain.ainvoke = AsyncMock(return_value=resp)

        with patch(
            "open_notebook.graphs.transformation.provision_langchain_model",
            new=AsyncMock(return_value=fake_chain),
        ):
            result = await process_chunk(state, {"configurable": {}})

        payload = fake_chain.ainvoke.await_args.args[0]
        system_message, human_message = payload
        assert human_message.content == "Alice met Bob."
        assert system_message.content.startswith("Extract all names.")
        assert "section 2 of 3" in system_message.content
        assert result == {"chunk_results": [{"idx": 1, "result": "Alice, Bob"}]}

    def test_chunk_semaphore_is_per_event_loop(self):
        """Each event loop gets its own semaphore (a shared one would raise
        'bound to a different event loop' across worker/API loops)."""
        import asyncio

        from open_notebook.graphs.transformation import _get_chunk_semaphore

        async def grab_twice():
            return _get_chunk_semaphore(), _get_chunk_semaphore()

        loop1 = asyncio.new_event_loop()
        try:
            sem_a, sem_b = loop1.run_until_complete(grab_twice())
        finally:
            loop1.close()

        loop2 = asyncio.new_event_loop()
        try:
            sem_c, _ = loop2.run_until_complete(grab_twice())
        finally:
            loop2.close()

        assert sem_a is sem_b  # same loop reuses its semaphore
        assert sem_a is not sem_c  # different loop gets a fresh one


class TestTransformationChunkingReduce:
    """Tests for the large-document chunking + hierarchical synthesis reduce."""

    def test_batch_results_by_tokens_respects_budget(self):
        from open_notebook.graphs.transformation import token_count

        results = ["word " * 100 for _ in range(10)]  # ~100 tokens each
        budget = 250
        batches = _batch_results_by_tokens(results, budget)

        assert sum(len(b) for b in batches) == 10  # nothing dropped
        for b in batches:
            assert len(b) == 1 or sum(token_count(r) for r in b) <= budget

    @pytest.mark.asyncio
    async def test_synthesize_batches_instead_of_overflowing(self):
        """Many/large chunk results must be reduced in context-sized batches,
        not concatenated into one oversized synthesis call."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from open_notebook.graphs.transformation import token_count

        chunk_results = [{"idx": i, "result": "word " * 1000} for i in range(12)]
        state = {
            "output": None,
            "needs_chunking": True,
            "chunk_results": chunk_results,
            "title": "Dense Summary",
            "system_prompt": "Summarize the document.",
            "output_buffer": 1000,
            "context_limit": 8000,
            "model_id": None,
            "source": None,
            "transformation": MagicMock(title="Dense Summary"),
        }

        seen_call_tokens: list[int] = []

        async def fake_ainvoke(payload):
            seen_call_tokens.append(token_count(payload[-1].content))
            resp = MagicMock()
            resp.content = "merged"  # small result so the reduction converges
            return resp

        fake_chain = MagicMock()
        fake_chain.ainvoke = fake_ainvoke

        budget = int(8000 * 0.90)  # generous upper bound for any single call
        with patch(
            "open_notebook.graphs.transformation.provision_langchain_model",
            new=AsyncMock(return_value=fake_chain),
        ):
            result = await synthesize_results(state, {"configurable": {}})

        assert result["output"] == "merged"
        assert len(seen_call_tokens) > 1, "should batch into multiple calls"
        assert all(
            n <= budget for n in seen_call_tokens
        ), f"a synthesis call exceeded budget: {seen_call_tokens}"


# ============================================================================
# TEST SUITE 4: Source Graph - Title Preservation
# ============================================================================


class TestSaveSourceTitlePreservation:
    """Test save_source node preserves user-set titles (#670)."""

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.Source.get")
    async def test_custom_title_preserved(self, mock_get):
        """User-set title is NOT overwritten by the extracted title."""
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, save_source

        mock_source = MagicMock(spec=Source)
        mock_source.title = "My Custom Research Title"
        mock_source.save = AsyncMock()
        mock_get.return_value = mock_source

        state = {
            "source_id": "source:123",
            "content_state": {"url": "https://example.com", "file_path": None},
            "extraction": ExtractionOutput(title="video.mp4", content="Some content"),
            "embed": False,
            "apply_transformations": [],
        }

        # cast: the node only reads these keys; SourceState is a total TypedDict
        await save_source(cast(SourceState, state))

        assert mock_source.title == "My Custom Research Title"
        mock_source.save.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.Source.get")
    async def test_placeholder_title_replaced(self, mock_get):
        """Placeholder 'Processing...' title IS replaced by extracted title."""
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, save_source

        mock_source = MagicMock(spec=Source)
        mock_source.title = "Processing..."
        mock_source.save = AsyncMock()
        mock_get.return_value = mock_source

        state = {
            "source_id": "source:123",
            "content_state": {"url": "https://example.com", "file_path": None},
            "extraction": ExtractionOutput(
                title="Extracted Article Title", content="Some content"
            ),
            "embed": False,
            "apply_transformations": [],
        }

        # cast: the node only reads these keys; SourceState is a total TypedDict
        await save_source(cast(SourceState, state))

        assert mock_source.title == "Extracted Article Title"
        mock_source.save.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.Source.get")
    async def test_none_title_replaced(self, mock_get):
        """None title IS replaced by extracted title."""
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, save_source

        mock_source = MagicMock(spec=Source)
        mock_source.title = None
        mock_source.save = AsyncMock()
        mock_get.return_value = mock_source

        state = {
            "source_id": "source:123",
            "content_state": {"url": None, "file_path": "/tmp/file.pdf"},
            "extraction": ExtractionOutput(title="Extracted Title", content="Content"),
            "embed": False,
            "apply_transformations": [],
        }

        # cast: the node only reads these keys; SourceState is a total TypedDict
        await save_source(cast(SourceState, state))

        assert mock_source.title == "Extracted Title"
        mock_source.save.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.Source.get")
    async def test_empty_title_replaced(self, mock_get):
        """Empty string title IS replaced by extracted title."""
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, save_source

        mock_source = MagicMock(spec=Source)
        mock_source.title = ""
        mock_source.save = AsyncMock()
        mock_get.return_value = mock_source

        state = {
            "source_id": "source:123",
            "content_state": {"url": None, "file_path": None},
            "extraction": ExtractionOutput(title="Extracted Title", content="Content"),
            "embed": False,
            "apply_transformations": [],
        }

        # cast: the node only reads these keys; SourceState is a total TypedDict
        await save_source(cast(SourceState, state))

        assert mock_source.title == "Extracted Title"
        mock_source.save.assert_awaited_once()


# ============================================================================
# TEST SUITE 5: Source Graph - content_process (content-core 2.x)
# ============================================================================


class TestContentProcessDeleteSource:
    """content-core 2.x no longer deletes the uploaded file; the graph must."""

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.extract_content")
    @patch("open_notebook.graphs.source.ModelManager")
    async def test_uploaded_file_deleted_when_flag_set(
        self, mock_model_manager, mock_extract, tmp_path
    ):
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, content_process

        # No STT default configured -> no audio override, no DB access.
        mm_instance = MagicMock()
        mm_instance.get_defaults = AsyncMock(
            return_value=MagicMock(default_speech_to_text_model=None)
        )
        mock_model_manager.return_value = mm_instance
        mock_extract.return_value = ExtractionOutput(
            title="Doc", content="extracted text"
        )

        uploaded = tmp_path / "upload.pdf"
        uploaded.write_text("data")

        state = {
            "source_id": "source:123",
            "content_state": {"file_path": str(uploaded), "delete_source": True},
            "embed": False,
            "apply_transformations": [],
        }

        result = await content_process(cast(SourceState, state))

        assert result["extraction"].content == "extracted text"
        assert not uploaded.exists()  # file removed by the graph
        mock_extract.assert_awaited_once()
        # The broader YouTube transcript language list is wired into the config
        # (content-core's own default is only en/es/pt).
        config = mock_extract.await_args.kwargs["config"]
        assert "de" in config.youtube_languages
        assert "ja" in config.youtube_languages

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.extract_content")
    @patch("open_notebook.graphs.source.ModelManager")
    async def test_uploaded_file_kept_when_flag_not_set(
        self, mock_model_manager, mock_extract, tmp_path
    ):
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, content_process

        mm_instance = MagicMock()
        mm_instance.get_defaults = AsyncMock(
            return_value=MagicMock(default_speech_to_text_model=None)
        )
        mock_model_manager.return_value = mm_instance
        mock_extract.return_value = ExtractionOutput(title="Doc", content="text")

        uploaded = tmp_path / "upload.pdf"
        uploaded.write_text("data")

        state = {
            "source_id": "source:123",
            "content_state": {"file_path": str(uploaded), "delete_source": False},
            "embed": False,
            "apply_transformations": [],
        }

        await content_process(cast(SourceState, state))

        assert uploaded.exists()  # file preserved

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.extract_content")
    @patch("open_notebook.graphs.source.ModelManager")
    async def test_empty_extraction_raises_valueerror(
        self, mock_model_manager, mock_extract, tmp_path
    ):
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, content_process

        mm_instance = MagicMock()
        mm_instance.get_defaults = AsyncMock(
            return_value=MagicMock(default_speech_to_text_model=None)
        )
        mock_model_manager.return_value = mm_instance
        mock_extract.return_value = ExtractionOutput(title="", content="   ")

        state = {
            "source_id": "source:123",
            "content_state": {"url": "https://example.com"},
            "embed": False,
            "apply_transformations": [],
        }

        with pytest.raises(ValueError):
            await content_process(cast(SourceState, state))

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.ContentSettings")
    @patch("open_notebook.graphs.source.extract_content")
    @patch("open_notebook.graphs.source.ModelManager")
    async def test_persisted_engines_wired_into_config(
        self, mock_model_manager, mock_extract, mock_settings
    ):
        """The persisted content-processing engines reach ContentCoreConfig, so
        a user-selected engine (e.g. crawl4ai) actually takes effect."""
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, content_process

        mm_instance = MagicMock()
        mm_instance.get_defaults = AsyncMock(
            return_value=MagicMock(default_speech_to_text_model=None)
        )
        mock_model_manager.return_value = mm_instance
        mock_settings.get_instance = AsyncMock(
            return_value=MagicMock(
                default_content_processing_engine_url="crawl4ai",
                default_content_processing_engine_doc="docling",
                docling_ocr=False,
            )
        )
        mock_extract.return_value = ExtractionOutput(title="T", content="body")

        state = {
            "source_id": "source:123",
            "content_state": {"url": "https://example.com"},
            "embed": False,
            "apply_transformations": [],
        }

        await content_process(cast(SourceState, state))

        config = mock_extract.await_args.kwargs["config"]
        assert config.url_engine == "crawl4ai"
        assert config.document_engine == "docling"
        assert config.docling_ocr is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
