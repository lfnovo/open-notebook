"""
Unit tests for the open_notebook.graphs module.

This test suite provides comprehensive coverage of graph-based workflows including:
- Language model provisioning and selection
- Transformation pipelines
- Prompt templates and chains
- Tool definitions
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from open_notebook.domain.notebook import Source
from open_notebook.domain.transformation import Transformation
from open_notebook.graphs.prompt import PatternChainState, call_model, graph
from open_notebook.graphs.tools import get_current_timestamp
from open_notebook.graphs.transformation import (
    TransformationState,
    run_transformation,
    graph as transformation_graph,
)
from open_notebook.graphs.utils import provision_langchain_model


# ============================================================================
# TEST SUITE 1: Graph Utils - Model Provisioning
# ============================================================================


class TestModelProvisioning:
    """Test suite for language model provisioning utilities."""

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.utils.token_count")
    async def test_provision_langchain_model_default(self, mock_token_count):
        """Test provisioning with default model for given type."""
        content = "Short content for testing"
        mock_token_count.return_value = 10

        from esperanto import LanguageModel
        mock_model = MagicMock(spec=LanguageModel)
        mock_model.to_langchain = MagicMock(return_value="langchain_model")

        with patch("open_notebook.graphs.utils.model_manager.get_default_model") as mock_get:
            mock_get.return_value = mock_model

            result = await provision_langchain_model(
                content=content,
                model_id=None,
                default_type="chat"
            )

            mock_get.assert_called_once_with("chat")
            assert result == "langchain_model"

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.utils.token_count")
    async def test_provision_langchain_model_large_context(self, mock_token_count):
        """Test large content triggers large context model."""
        # Create content with > 105k tokens
        large_content = "word " * 30000  # Should exceed 105k tokens
        mock_token_count.return_value = 110000  # > 105k

        from esperanto import LanguageModel
        mock_model = MagicMock(spec=LanguageModel)
        mock_model.to_langchain = MagicMock(return_value="large_context_model")

        with patch("open_notebook.graphs.utils.model_manager.get_default_model") as mock_get:
            mock_get.return_value = mock_model

            result = await provision_langchain_model(
                content=large_content,
                model_id=None,
                default_type="chat"
            )

            # Should call with large_context type
            mock_get.assert_called_once()
            call_args = mock_get.call_args[0]
            assert call_args[0] == "large_context"

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.utils.token_count")
    async def test_provision_langchain_model_specific_id(self, mock_token_count):
        """Test provisioning with specific model ID."""
        content = "Test content"
        model_id = "model:gpt4"
        mock_token_count.return_value = 5

        from esperanto import LanguageModel
        mock_model = MagicMock(spec=LanguageModel)
        mock_model.to_langchain = MagicMock(return_value="specific_model")

        with patch("open_notebook.graphs.utils.model_manager.get_model") as mock_get:
            mock_get.return_value = mock_model

            result = await provision_langchain_model(
                content=content,
                model_id=model_id,
                default_type="chat"
            )

            mock_get.assert_called_once_with(model_id)
            assert result == "specific_model"

    @pytest.mark.asyncio
    @patch("open_notebook.graphs.utils.token_count")
    async def test_provision_langchain_model_with_kwargs(self, mock_token_count):
        """Test provisioning passes through kwargs."""
        content = "Test"
        mock_token_count.return_value = 5

        from esperanto import LanguageModel
        mock_model = MagicMock(spec=LanguageModel)
        mock_model.to_langchain = MagicMock(return_value="model")

        with patch("open_notebook.graphs.utils.model_manager.get_default_model") as mock_get:
            mock_get.return_value = mock_model

            await provision_langchain_model(
                content=content,
                model_id=None,
                default_type="chat",
                temperature=0.7,
                max_tokens=1000
            )

            # Check kwargs were passed
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs["temperature"] == 0.7
            assert call_kwargs["max_tokens"] == 1000


# ============================================================================
# TEST SUITE 2: Graph Tools
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
# TEST SUITE 3: Prompt Graph
# ============================================================================


class TestPromptGraph:
    """Test suite for prompt pattern chain graph."""

    def test_pattern_chain_state_structure(self):
        """Test PatternChainState structure and fields."""
        state = PatternChainState(
            prompt="Test prompt",
            parser=None,
            input_text="Test input",
            output=""
        )

        assert state["prompt"] == "Test prompt"
        assert state["parser"] is None
        assert state["input_text"] == "Test input"
        assert state["output"] == ""

    @pytest.mark.asyncio
    async def test_call_model_basic(self):
        """Test basic model calling with prompt."""
        state = {
            "prompt": "Transform this text",
            "input_text": "Hello world",
            "parser": None
        }

        config = {
            "configurable": {
                "model_id": None
            }
        }

        mock_response = MagicMock()
        mock_response.content = "Transformed output"

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        with patch("open_notebook.graphs.prompt.provision_langchain_model") as mock_provision:
            mock_provision.return_value = mock_chain

            result = await call_model(state, config)

            assert "output" in result
            assert result["output"] == "Transformed output"
            mock_chain.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_model_with_parser(self):
        """Test model calling with custom parser."""
        mock_parser = MagicMock()

        state = {
            "prompt": "Process this",
            "input_text": "Input data",
            "parser": mock_parser
        }

        config = {"configurable": {"model_id": "model:test"}}

        mock_response = MagicMock()
        mock_response.content = "Output"

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        with patch("open_notebook.graphs.prompt.provision_langchain_model") as mock_provision:
            mock_provision.return_value = mock_chain

            result = await call_model(state, config)

            assert result["output"] == "Output"

    def test_prompt_graph_compilation(self):
        """Test that prompt graph compiles correctly."""
        assert graph is not None

        # Graph should have the expected structure
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")

    @pytest.mark.asyncio
    async def test_prompt_graph_execution(self):
        """Test executing the compiled prompt graph."""
        state = {
            "prompt": "Test prompt",
            "input_text": "Test input",
            "output": ""
        }

        config = {"configurable": {"model_id": None}}

        mock_response = MagicMock()
        mock_response.content = "Graph output"

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        with patch("open_notebook.graphs.prompt.provision_langchain_model") as mock_provision:
            mock_provision.return_value = mock_chain

            # Execute the graph
            result = await graph.ainvoke(state, config)

            assert "output" in result
            assert result["output"] == "Graph output"


# ============================================================================
# TEST SUITE 4: Transformation Graph
# ============================================================================


class TestTransformationGraph:
    """Test suite for transformation graph workflows."""

    def test_transformation_state_structure(self):
        """Test TransformationState structure and fields."""
        mock_source = MagicMock(spec=Source)
        mock_transformation = MagicMock(spec=Transformation)

        state = TransformationState(
            input_text="Test text",
            source=mock_source,
            transformation=mock_transformation,
            output=""
        )

        assert state["input_text"] == "Test text"
        assert state["source"] == mock_source
        assert state["transformation"] == mock_transformation
        assert state["output"] == ""

    @pytest.mark.asyncio
    async def test_run_transformation_with_source(self):
        """Test running transformation with a source object."""
        mock_source = MagicMock(spec=Source)
        mock_source.full_text = "Source content to transform"
        mock_source.add_insight = AsyncMock()

        mock_transformation = MagicMock(spec=Transformation)
        mock_transformation.prompt = "Summarize this text"
        mock_transformation.title = "Summary"

        state = {
            "source": mock_source,
            "transformation": mock_transformation,
            "input_text": None
        }

        config = {"configurable": {"model_id": None}}

        mock_response = MagicMock()
        mock_response.content = "This is a summary"

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        with patch("open_notebook.graphs.transformation.provision_langchain_model") as mock_provision, \
             patch("open_notebook.graphs.transformation.DefaultPrompts") as mock_prompts:

            mock_provision.return_value = mock_chain
            mock_prompts.return_value.transformation_instructions = None

            result = await run_transformation(state, config)

            assert "output" in result
            assert result["output"] == "This is a summary"
            # Should add insight to source
            mock_source.add_insight.assert_called_once_with("Summary", "This is a summary")

    @pytest.mark.asyncio
    async def test_run_transformation_with_input_text(self):
        """Test running transformation with direct input text."""
        mock_transformation = MagicMock(spec=Transformation)
        mock_transformation.prompt = "Analyze this"
        mock_transformation.title = "Analysis"

        state = {
            "input_text": "Direct input text",
            "transformation": mock_transformation,
            "source": None
        }

        config = {"configurable": {"model_id": "model:analyzer"}}

        mock_response = MagicMock()
        mock_response.content = "Analysis result"

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        with patch("open_notebook.graphs.transformation.provision_langchain_model") as mock_provision, \
             patch("open_notebook.graphs.transformation.DefaultPrompts") as mock_prompts:

            mock_provision.return_value = mock_chain
            mock_prompts.return_value.transformation_instructions = None

            result = await run_transformation(state, config)

            assert result["output"] == "Analysis result"

    @pytest.mark.asyncio
    async def test_run_transformation_cleans_thinking_content(self):
        """Test that transformation cleans thinking tags from output."""
        mock_transformation = MagicMock(spec=Transformation)
        mock_transformation.prompt = "Process this"
        mock_transformation.title = "Processed"

        state = {
            "input_text": "Test",
            "transformation": mock_transformation,
            "source": None
        }

        config = {"configurable": {"model_id": None}}

        # Response with thinking tags
        mock_response = MagicMock()
        mock_response.content = "<think>Internal reasoning</think>Clean output"

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        with patch("open_notebook.graphs.transformation.provision_langchain_model") as mock_provision, \
             patch("open_notebook.graphs.transformation.DefaultPrompts") as mock_prompts:

            mock_provision.return_value = mock_chain
            mock_prompts.return_value.transformation_instructions = None

            result = await run_transformation(state, config)

            # Should have thinking content removed
            assert "<think>" not in result["output"]
            assert "Clean output" in result["output"]
            assert "Internal reasoning" not in result["output"]

    @pytest.mark.asyncio
    async def test_run_transformation_assertion_no_content(self):
        """Test transformation raises assertion with no content."""
        mock_transformation = MagicMock(spec=Transformation)

        state = {
            "input_text": None,
            "transformation": mock_transformation,
            "source": None
        }

        config = {"configurable": {"model_id": None}}

        with pytest.raises(AssertionError, match="No content to transform"):
            await run_transformation(state, config)

    def test_transformation_graph_compilation(self):
        """Test that transformation graph compiles correctly."""
        assert transformation_graph is not None
        assert hasattr(transformation_graph, "invoke")
        assert hasattr(transformation_graph, "ainvoke")

    @pytest.mark.asyncio
    async def test_transformation_graph_execution(self):
        """Test executing the complete transformation graph."""
        mock_source = MagicMock(spec=Source)
        mock_source.full_text = "Content"
        mock_source.add_insight = AsyncMock()

        mock_transformation = MagicMock(spec=Transformation)
        mock_transformation.prompt = "Transform"
        mock_transformation.title = "Title"

        state = {
            "source": mock_source,
            "transformation": mock_transformation,
            "input_text": None,
            "output": ""
        }

        config = {"configurable": {"model_id": None}}

        mock_response = MagicMock()
        mock_response.content = "Transformed"

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        with patch("open_notebook.graphs.transformation.provision_langchain_model") as mock_provision, \
             patch("open_notebook.graphs.transformation.DefaultPrompts") as mock_prompts:

            mock_provision.return_value = mock_chain
            mock_prompts.return_value.transformation_instructions = None

            result = await transformation_graph.ainvoke(state, config)

            assert "output" in result
            assert result["output"] == "Transformed"

    @pytest.mark.asyncio
    async def test_transformation_with_default_prompts(self):
        """Test transformation uses default prompt instructions."""
        mock_transformation = MagicMock(spec=Transformation)
        mock_transformation.prompt = "Main prompt"
        mock_transformation.title = "Test"

        state = {
            "input_text": "Test",
            "transformation": mock_transformation,
            "source": None
        }

        config = {"configurable": {"model_id": None}}

        mock_response = MagicMock()
        mock_response.content = "Output"

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        mock_default_prompts = MagicMock()
        mock_default_prompts.transformation_instructions = "Default instructions"

        with patch("open_notebook.graphs.transformation.provision_langchain_model") as mock_provision, \
             patch("open_notebook.graphs.transformation.DefaultPrompts") as mock_prompts_class:

            mock_provision.return_value = mock_chain
            mock_prompts_class.return_value = mock_default_prompts

            result = await run_transformation(state, config)

            # Verify the chain was called (meaning prompt was constructed)
            mock_chain.ainvoke.assert_called_once()
            assert result["output"] == "Output"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
