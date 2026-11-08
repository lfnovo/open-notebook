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
    run_transformation,
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
    async def test_run_transformation_assertion_no_content(self):
        """Test transformation raises assertion with no content."""
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
            await run_transformation(state, config)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("full_text", ["", "   \n\t ", None])
    async def test_run_transformation_rejects_source_without_text(self, full_text):
        """A source with no extracted text must not reach the model, and no
        insight is saved (#1394)."""
        from open_notebook.domain.transformation import Transformation
        from open_notebook.exceptions import InvalidInputError

        mock_source = MagicMock(spec=Source)
        mock_source.full_text = full_text
        mock_source.add_insight = AsyncMock()

        state = {
            "input_text": None,
            "transformation": MagicMock(spec=Transformation),
            "source": mock_source,
        }
        config: RunnableConfig = {"configurable": {"model_id": None}}

        with patch(
            "open_notebook.graphs.transformation.provision_langchain_model",
            new_callable=AsyncMock,
        ) as mock_provision:
            with pytest.raises(InvalidInputError, match="no text content"):
                await run_transformation(state, config)

        mock_provision.assert_not_called()
        mock_source.add_insight.assert_not_called()

    def test_transformation_graph_compilation(self):
        """Test that transformation graph compiles correctly."""
        assert transformation_graph is not None
        assert hasattr(transformation_graph, "invoke")
        assert hasattr(transformation_graph, "ainvoke")


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

    @pytest.fixture(autouse=True)
    def _uploads_in_tmp_path(self, tmp_path, monkeypatch):
        # content_process only reads (and deletes) files inside the uploads folder.
        monkeypatch.setattr("open_notebook.graphs.source.UPLOADS_FOLDER", str(tmp_path))

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
    # Runtime present: nothing to fall back from.
    @patch("open_notebook.graphs.source.engine_runtime_missing", return_value=None)
    @patch("open_notebook.graphs.source.extract_content")
    @patch("open_notebook.graphs.source.ModelManager")
    async def test_persisted_engines_wired_into_config(
        self, mock_model_manager, mock_extract, _mock_runtime, mock_settings
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
                youtube_preferred_languages=None,
                default_content_processing_engine_url="crawl4ai",
                default_content_processing_engine_doc="docling",
                docling_ocr=False,
                docling_formulas=True,
                docling_vision=True,
                docling_vision_url=None,
                docling_vision_model=None,
                docling_vision_prompt=None,
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
        assert config.docling_formulas is True
        assert config.docling_vision is True

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.ContentSettings")
    @patch("open_notebook.graphs.source.engine_runtime_missing", return_value=None)
    @patch("open_notebook.graphs.source.extract_content")
    @patch("open_notebook.graphs.source.ModelManager")
    async def test_docling_vision_endpoint_env_reaches_config(
        self,
        mock_model_manager,
        mock_extract,
        _mock_runtime,
        mock_settings,
        monkeypatch,
    ):
        """The CCORE_DOCLING_VISION_* worker variables (#1478) still apply when
        content_process builds ContentCoreConfig with its own overrides."""
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, content_process

        monkeypatch.setenv(
            "CCORE_DOCLING_VISION_URL", "http://vlm.local:8000/v1/chat/completions"
        )
        monkeypatch.setenv("CCORE_DOCLING_VISION_MODEL", "qwen2.5-vl-7b")
        monkeypatch.setenv("CCORE_DOCLING_VISION_API_KEY", "test-key")

        mm_instance = MagicMock()
        mm_instance.get_defaults = AsyncMock(
            return_value=MagicMock(default_speech_to_text_model=None)
        )
        mock_model_manager.return_value = mm_instance
        mock_settings.get_instance = AsyncMock(
            return_value=MagicMock(
                youtube_preferred_languages=None,
                default_content_processing_engine_url=None,
                default_content_processing_engine_doc="docling",
                docling_ocr=None,
                docling_formulas=None,
                docling_vision=True,
                docling_vision_url=None,
                docling_vision_model=None,
                docling_vision_prompt=None,
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
        assert config.docling_vision is True
        assert config.docling_vision_url == "http://vlm.local:8000/v1/chat/completions"
        assert config.docling_vision_model == "qwen2.5-vl-7b"
        assert config.docling_vision_api_key == "test-key"

    @staticmethod
    async def _config_with_vision_settings(**vision_settings):
        """Run content_process with Docling vision on and the given vision
        endpoint settings, and return the ContentCoreConfig it builds."""
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, content_process

        settings = MagicMock(
            youtube_preferred_languages=None,
            default_content_processing_engine_url=None,
            default_content_processing_engine_doc="docling",
            docling_ocr=None,
            docling_formulas=None,
            docling_vision=True,
            docling_vision_url=None,
            docling_vision_model=None,
            docling_vision_prompt=None,
        )
        for name, value in vision_settings.items():
            setattr(settings, name, value)

        mm_instance = MagicMock()
        mm_instance.get_defaults = AsyncMock(
            return_value=MagicMock(default_speech_to_text_model=None)
        )
        state = {
            "source_id": "source:123",
            "content_state": {"url": "https://example.com"},
            "embed": False,
            "apply_transformations": [],
        }
        with (
            patch("open_notebook.graphs.source.ContentSettings") as mock_settings,
            patch(
                "open_notebook.graphs.source.engine_runtime_missing",
                return_value=None,
            ),
            patch("open_notebook.graphs.source.extract_content") as mock_extract,
            patch("open_notebook.graphs.source.ModelManager", return_value=mm_instance),
        ):
            mock_settings.get_instance = AsyncMock(return_value=settings)
            mock_extract.return_value = ExtractionOutput(title="T", content="body")
            await content_process(cast(SourceState, state))

        assert mock_extract.await_args is not None
        return mock_extract.await_args.kwargs["config"]

    @pytest.mark.asyncio
    async def test_docling_vision_settings_override_env(self, monkeypatch):
        """Vision endpoint fields saved in Settings (#1561) reach
        ContentCoreConfig and win over the CCORE_DOCLING_VISION_* variables,
        while the API key still comes from its env var."""
        monkeypatch.setenv("CCORE_DOCLING_VISION_URL", "http://env.local/v1")
        monkeypatch.setenv("CCORE_DOCLING_VISION_MODEL", "env-model")
        monkeypatch.setenv("CCORE_DOCLING_VISION_API_KEY", "test-key")

        config = await self._config_with_vision_settings(
            docling_vision_url=" http://192.168.1.20:1234/v1/chat/completions ",
            docling_vision_model="qwen2.5-vl-7b",
            docling_vision_prompt="Describe the chart.",
        )

        assert (
            config.docling_vision_url == "http://192.168.1.20:1234/v1/chat/completions"
        )
        assert config.docling_vision_model == "qwen2.5-vl-7b"
        assert config.docling_vision_prompt == "Describe the chart."
        assert config.docling_vision_api_key == "test-key"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("blank", [None, "", "   "])
    async def test_blank_docling_vision_settings_keep_env(self, blank, monkeypatch):
        """Empty vision endpoint fields are not passed to content-core, so the
        CCORE_DOCLING_VISION_* worker variables keep applying (#1561)."""
        monkeypatch.setenv("CCORE_DOCLING_VISION_URL", "http://env.local/v1")
        monkeypatch.setenv("CCORE_DOCLING_VISION_MODEL", "env-model")
        monkeypatch.setenv("CCORE_DOCLING_VISION_PROMPT", "env prompt")

        config = await self._config_with_vision_settings(
            docling_vision_url=blank,
            docling_vision_model=blank,
            docling_vision_prompt=blank,
        )

        assert config.docling_vision_url == "http://env.local/v1"
        assert config.docling_vision_model == "env-model"
        assert config.docling_vision_prompt == "env prompt"

    @pytest.mark.asyncio
    async def test_unsafe_docling_vision_url_is_not_used(self, monkeypatch):
        """A stored vision URL that fails validate_url() at extraction time
        (e.g. it now points at a cloud metadata address) is dropped instead of
        receiving document images."""
        monkeypatch.delenv("CCORE_DOCLING_VISION_URL", raising=False)

        config = await self._config_with_vision_settings(
            docling_vision_url="http://169.254.169.254/latest/meta-data/",
        )

        assert config.docling_vision_url is None
        assert config.docling_vision is True

    @pytest.mark.asyncio
    async def test_unsafe_docling_vision_url_falls_back_to_env_as_a_whole(
        self, monkeypatch
    ):
        """When the stored URL is dropped, the stored model and prompt go with
        it, so the worker's endpoint gets its own model name, not ours."""
        monkeypatch.setenv("CCORE_DOCLING_VISION_URL", "http://env.local/v1")
        monkeypatch.setenv("CCORE_DOCLING_VISION_MODEL", "env-model")
        monkeypatch.delenv("CCORE_DOCLING_VISION_PROMPT", raising=False)

        config = await self._config_with_vision_settings(
            docling_vision_url="http://169.254.169.254/latest/meta-data/",
            docling_vision_model="qwen2.5-vl-7b",
            docling_vision_prompt="Describe the chart.",
        )

        assert config.docling_vision_url == "http://env.local/v1"
        assert config.docling_vision_model == "env-model"
        assert config.docling_vision_prompt is None

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.ContentSettings")
    @patch("open_notebook.graphs.source.extract_content")
    @patch("open_notebook.graphs.source.ModelManager")
    async def test_persisted_youtube_languages_wired_into_config(
        self, mock_model_manager, mock_extract, mock_settings
    ):
        """ContentSettings.youtube_preferred_languages overrides the built-in
        default list, so users can add transcript languages without a code
        change (regression: the setting was dropped in the content-core 2.x
        migration and silently ignored)."""
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, content_process

        mm_instance = MagicMock()
        mm_instance.get_defaults = AsyncMock(
            return_value=MagicMock(default_speech_to_text_model=None)
        )
        mock_model_manager.return_value = mm_instance
        mock_settings.get_instance = AsyncMock(
            return_value=MagicMock(
                youtube_preferred_languages=["ko", "en"],
                default_content_processing_engine_url=None,
                default_content_processing_engine_doc=None,
                docling_ocr=None,
                docling_formulas=None,
                docling_vision=None,
                docling_vision_url=None,
                docling_vision_model=None,
                docling_vision_prompt=None,
            )
        )
        mock_extract.return_value = ExtractionOutput(title="T", content="body")

        state = {
            "source_id": "source:123",
            "content_state": {"url": "https://youtu.be/abc"},
            "embed": False,
            "apply_transformations": [],
        }

        await content_process(cast(SourceState, state))

        config = mock_extract.await_args.kwargs["config"]
        assert config.youtube_languages == ["ko", "en"]

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.ContentSettings")
    @patch("open_notebook.graphs.source.extract_content")
    @patch("open_notebook.graphs.source.ModelManager")
    async def test_unavailable_engine_falls_back_to_auto(
        self, mock_model_manager, mock_extract, mock_settings
    ):
        """A stored engine whose runtime is absent must not reach content-core.

        The selection is persisted in the database while runtime availability
        comes from environment flags, so a redeploy that drops
        OPEN_NOTEBOOK_ENABLE_CRAWL4AI leaves the setting pointing at a runtime
        that is not installed. Passing it through failed every URL ingestion
        with "Could not extract any text content from this source" and no clue
        as to why; the extraction must degrade to content-core's "auto" chain
        instead.
        """
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, content_process

        mm_instance = MagicMock()
        mm_instance.get_defaults = AsyncMock(
            return_value=MagicMock(default_speech_to_text_model=None)
        )
        mock_model_manager.return_value = mm_instance
        mock_settings.get_instance = AsyncMock(
            return_value=MagicMock(
                youtube_preferred_languages=None,
                default_content_processing_engine_url="crawl4ai",
                default_content_processing_engine_doc="docling",
                docling_ocr=True,
                docling_formulas=False,
                docling_vision=False,
                docling_vision_url=None,
                docling_vision_model=None,
                docling_vision_prompt=None,
            )
        )
        mock_extract.return_value = ExtractionOutput(title="T", content="body")

        state = {
            "source_id": "source:123",
            "content_state": {"url": "https://example.com"},
            "embed": False,
            "apply_transformations": [],
        }

        with patch(
            "open_notebook.graphs.source.engine_runtime_missing",
            side_effect=lambda engine: {
                "crawl4ai": "OPEN_NOTEBOOK_ENABLE_CRAWL4AI",
                "docling": "OPEN_NOTEBOOK_ENABLE_DOCLING",
            }.get(engine),
        ):
            await content_process(cast(SourceState, state))

        config = mock_extract.await_args.kwargs["config"]
        assert config.url_engine == "auto"
        assert config.document_engine == "auto"

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.source.ContentSettings")
    @patch("open_notebook.graphs.source.extract_content")
    @patch("open_notebook.graphs.source.ModelManager")
    async def test_runtime_free_engines_never_fall_back(
        self, mock_model_manager, mock_extract, mock_settings
    ):
        """Engines needing no opt-in runtime are passed through untouched."""
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, content_process

        mm_instance = MagicMock()
        mm_instance.get_defaults = AsyncMock(
            return_value=MagicMock(default_speech_to_text_model=None)
        )
        mock_model_manager.return_value = mm_instance
        mock_settings.get_instance = AsyncMock(
            return_value=MagicMock(
                youtube_preferred_languages=None,
                default_content_processing_engine_url="firecrawl",
                default_content_processing_engine_doc="simple",
                docling_ocr=True,
                docling_formulas=False,
                docling_vision=False,
                docling_vision_url=None,
                docling_vision_model=None,
                docling_vision_prompt=None,
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
        assert config.url_engine == "firecrawl"
        assert config.document_engine == "simple"

    @staticmethod
    def _stt_setup(mock_model_manager, mock_model, linked_credential):
        mm_instance = MagicMock()
        mm_instance.get_defaults = AsyncMock(
            return_value=MagicMock(default_speech_to_text_model="model:stt1")
        )
        mock_model_manager.return_value = mm_instance
        # `name=` can't be passed via the MagicMock constructor: it sets the
        # mock's own repr name, not a `.name` attribute.
        mock_stt_model = MagicMock()
        mock_stt_model.provider = "openai"
        mock_stt_model.name = "gpt-4o-mini-transcribe"
        mock_stt_model.get_credential_obj = AsyncMock(return_value=linked_credential)
        mock_model.get = AsyncMock(return_value=mock_stt_model)

    @pytest.mark.asyncio
    @patch("open_notebook.ai.key_provider.provision_provider_keys")
    @patch("open_notebook.graphs.source.Model")
    @patch("open_notebook.graphs.source.extract_content")
    @patch("open_notebook.graphs.source.ModelManager")
    async def test_stt_key_provisioned_before_extraction(
        self, mock_model_manager, mock_extract, mock_model, mock_provision, tmp_path
    ):
        """The default STT model's provider env vars must be provisioned before
        content-core runs, the same fallback resolve_* / get_model use for
        language and embedding models (see #567, which fixed the same class
        of bug for embeddings).

        content-core builds its speech-to-text client from process env vars
        only, so without this it raises ConfigurationError when
        OPENAI_API_KEY is unset, even though a credential is configured in
        the UI.
        """
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, content_process

        self._stt_setup(mock_model_manager, mock_model, linked_credential=None)
        calls: list[str] = []

        async def provision(*args, **kwargs):
            calls.append("provision")
            return True

        async def extract(*args, **kwargs):
            calls.append("extract")
            return ExtractionOutput(title="T", content="body")

        mock_provision.side_effect = provision
        mock_extract.side_effect = extract
        audio = tmp_path / "audio.mp3"
        audio.write_bytes(b"fake")

        state = {
            "source_id": "source:123",
            "content_state": {"file_path": str(audio)},
            "embed": False,
            "apply_transformations": [],
        }

        await content_process(cast(SourceState, state))

        assert calls == ["provision", "extract"]
        mock_provision.assert_awaited_once_with("openai", credential=None)

    @pytest.mark.asyncio
    @patch("open_notebook.ai.key_provider.provision_provider_keys")
    @patch("open_notebook.graphs.source.Model")
    @patch("open_notebook.graphs.source.extract_content")
    @patch("open_notebook.graphs.source.ModelManager")
    async def test_stt_model_linked_credential_is_provisioned(
        self, mock_model_manager, mock_extract, mock_model, mock_provision, tmp_path
    ):
        """With several credentials for one provider, the STT model's own linked
        credential is provisioned, not the provider's first one."""
        from content_core.common import ExtractionOutput

        from open_notebook.graphs.source import SourceState, content_process

        linked = MagicMock()
        self._stt_setup(mock_model_manager, mock_model, linked_credential=linked)
        mock_provision.return_value = True
        mock_extract.return_value = ExtractionOutput(title="T", content="body")
        audio = tmp_path / "audio.mp3"
        audio.write_bytes(b"fake")

        state = {
            "source_id": "source:123",
            "content_state": {"file_path": str(audio)},
            "embed": False,
            "apply_transformations": [],
        }

        await content_process(cast(SourceState, state))

        mock_provision.assert_awaited_once_with("openai", credential=linked)


# ============================================================================
# TEST SUITE 6: Per-transformation model_id forwarding (#1137)
# ============================================================================


class TestTransformationModelIdForwarding:
    """Both call sites must forward transformation.model_id into the graph via
    config.configurable so per-transformation model selection is honored (#1137).
    """

    @pytest.mark.asyncio
    @patch(
        "open_notebook.graphs.source.transform_graph.ainvoke", new_callable=AsyncMock
    )
    async def test_source_graph_forwards_model_id(self, mock_ainvoke):
        """open_notebook.graphs.source.transform_content forwards model_id."""
        from open_notebook.domain.transformation import Transformation
        from open_notebook.graphs.source import transform_content

        mock_ainvoke.return_value = {"output": "result"}

        mock_source = MagicMock(spec=Source)
        mock_source.full_text = "some content"
        mock_source.add_insight = AsyncMock()

        transformation = MagicMock(spec=Transformation)
        transformation.name = "summary"
        transformation.title = "Summary"
        transformation.model_id = "model:custom"

        state = {"source": mock_source, "transformation": transformation}

        await transform_content(state)  # type: ignore[arg-type]

        mock_ainvoke.assert_awaited_once()
        config = mock_ainvoke.await_args.kwargs["config"]
        assert config["configurable"]["model_id"] == "model:custom"

    @pytest.mark.asyncio
    @patch(
        "open_notebook.graphs.source.transform_graph.ainvoke", new_callable=AsyncMock
    )
    async def test_source_graph_forwards_none_model_id(self, mock_ainvoke):
        """When model_id is unset (None), None is forwarded (falls back to default)."""
        from open_notebook.domain.transformation import Transformation
        from open_notebook.graphs.source import transform_content

        mock_ainvoke.return_value = {"output": "result"}

        mock_source = MagicMock(spec=Source)
        mock_source.full_text = "some content"
        mock_source.add_insight = AsyncMock()

        transformation = MagicMock(spec=Transformation)
        transformation.name = "summary"
        transformation.title = "Summary"
        transformation.model_id = None

        state = {"source": mock_source, "transformation": transformation}

        await transform_content(state)  # type: ignore[arg-type]

        config = mock_ainvoke.await_args.kwargs["config"]
        assert config["configurable"]["model_id"] is None

    @pytest.mark.asyncio
    @patch("commands.source_commands.transform_graph.ainvoke", new_callable=AsyncMock)
    @patch("commands.source_commands.Transformation.get", new_callable=AsyncMock)
    @patch("commands.source_commands.Source.get", new_callable=AsyncMock)
    async def test_command_forwards_model_id(
        self, mock_source_get, mock_transformation_get, mock_ainvoke
    ):
        """commands.source_commands.run_transformation_command forwards model_id."""
        from commands.source_commands import (
            RunTransformationInput,
            run_transformation_command,
        )
        from open_notebook.domain.transformation import Transformation

        mock_source_get.return_value = MagicMock(spec=Source)

        transformation = MagicMock(spec=Transformation)
        transformation.model_id = "model:custom"
        mock_transformation_get.return_value = transformation

        mock_ainvoke.return_value = {"output": "result"}

        input_data = RunTransformationInput(
            source_id="source:123", transformation_id="transformation:456"
        )

        await run_transformation_command(input_data)

        mock_ainvoke.assert_awaited_once()
        config = mock_ainvoke.await_args.kwargs["config"]
        assert config["configurable"]["model_id"] == "model:custom"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
