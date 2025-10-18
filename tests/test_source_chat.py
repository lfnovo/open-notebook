"""
Integration tests for Source Chat Langgraph.

These tests verify that the Source Chat Langgraph integrates correctly
with the existing Open Notebook infrastructure.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from open_notebook.domain.notebook import Source, SourceInsight
from open_notebook.graphs.source_chat import (
    SourceChatState,
    _format_source_context,
    call_model_with_source_context,
    source_chat_graph,
)


@pytest.fixture
def mock_source():
    """Create a mock Source object for testing."""
    source = MagicMock(spec=Source)
    source.id = "source:test123"
    source.title = "Test Source"
    source.topics = ["AI", "Machine Learning"]
    source.full_text = "This is test content for the source."
    source.model_dump.return_value = {
        "id": "source:test123",
        "title": "Test Source",
        "topics": ["AI", "Machine Learning"],
        "full_text": "This is test content for the source."
    }
    return source


@pytest.fixture
def mock_insight():
    """Create a mock SourceInsight object for testing."""
    insight = MagicMock(spec=SourceInsight)
    insight.id = "insight:test456"
    insight.insight_type = "summary"
    insight.content = "This is a test insight about the source."
    insight.model_dump.return_value = {
        "id": "insight:test456",
        "insight_type": "summary",
        "content": "This is a test insight about the source."
    }
    return insight


@pytest.fixture
def sample_state():
    """Create a sample SourceChatState for testing."""
    return SourceChatState(
        messages=[HumanMessage(content="What are the main topics in this source?")],
        source_id="source:test123",
        source=None,
        insights=None,
        context=None,
        model_override=None,
        context_indicators=None
    )


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return {
        "configurable": {
            "thread_id": "test_thread",
            "model_id": "test_model"
        }
    }


class TestSourceChatState:
    """Test the SourceChatState TypedDict structure."""
    
    def test_source_chat_state_creation(self, sample_state):
        """Test that SourceChatState can be created with required fields."""
        assert sample_state["source_id"] == "source:test123"
        assert len(sample_state["messages"]) == 1
        assert sample_state["source"] is None
        assert sample_state["insights"] is None


class TestContextFormatting:
    """Test the context formatting functionality."""
    
    def test_format_source_context_with_sources(self):
        """Test formatting context data containing sources."""
        context_data = {
            "sources": [{
                "id": "source:test123",
                "title": "Test Source",
                "full_text": "This is test content."
            }],
            "insights": [],
            "metadata": {
                "source_count": 1,
                "insight_count": 0
            },
            "total_tokens": 100
        }
        
        result = _format_source_context(context_data)
        
        assert "## SOURCE CONTENT" in result
        assert "source:test123" in result
        assert "Test Source" in result
        assert "This is test content." in result
        assert "## CONTEXT METADATA" in result
    
    def test_format_source_context_with_insights(self):
        """Test formatting context data containing insights."""
        context_data = {
            "sources": [],
            "insights": [{
                "id": "insight:test456",
                "insight_type": "summary",
                "content": "Test insight content."
            }],
            "metadata": {
                "source_count": 0,
                "insight_count": 1
            },
            "total_tokens": 50
        }
        
        result = _format_source_context(context_data)
        
        assert "## SOURCE INSIGHTS" in result
        assert "insight:test456" in result
        assert "summary" in result
        assert "Test insight content." in result
    
    def test_format_source_context_empty(self):
        """Test formatting empty context data."""
        context_data = {
            "sources": [],
            "insights": [],
            "metadata": {
                "source_count": 0,
                "insight_count": 0
            },
            "total_tokens": 0
        }
        
        result = _format_source_context(context_data)
        
        assert "## CONTEXT METADATA" in result
        assert "Source count: 0" in result
        assert "Insight count: 0" in result


class TestSourceChatIntegration:
    """Test the integration of source chat components."""
    
    @patch('open_notebook.graphs.source_chat.ContextBuilder')
    @patch('open_notebook.graphs.source_chat.provision_langchain_model')
    @patch('open_notebook.graphs.source_chat.Prompter')
    async def test_call_model_with_source_context(
        self, 
        mock_prompter, 
        mock_provision_model, 
        mock_context_builder,
        sample_state,
        sample_config,
        mock_source,
        mock_insight
    ):
        """Test the main model calling function with mocked dependencies."""
        
        # Mock the ContextBuilder
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build.return_value = {
            "sources": [mock_source.model_dump()],
            "insights": [mock_insight.model_dump()],
            "metadata": {"source_count": 1, "insight_count": 1},
            "total_tokens": 150
        }
        mock_context_builder.return_value = mock_builder_instance
        
        # Mock the Prompter
        mock_prompter_instance = MagicMock()
        mock_prompter_instance.render.return_value = "Rendered prompt"
        mock_prompter.return_value = mock_prompter_instance
        
        # Mock the model
        mock_model = AsyncMock()
        mock_ai_message = AIMessage(content="Test response from AI")
        mock_model.invoke.return_value = mock_ai_message
        mock_provision_model.return_value = mock_model
        
        # Call the function
        result = await call_model_with_source_context(sample_state, sample_config)  # type: ignore[misc]
        
        # Verify the result
        assert "messages" in result
        assert result["messages"] == mock_ai_message
        assert "source" in result
        assert "insights" in result
        assert "context" in result
        assert "context_indicators" in result
        
        # Verify mocks were called correctly
        mock_context_builder.assert_called_once()
        mock_builder_instance.build.assert_called_once()
        mock_prompter.assert_called_once_with(prompt_template="source_chat")
        mock_provision_model.assert_called_once()
    
    def test_source_chat_graph_structure(self):
        """Test that the source chat graph is properly structured."""
        # Verify the graph has the expected structure
        assert source_chat_graph is not None
        
        # Check that the graph has nodes
        nodes = source_chat_graph.get_graph().nodes
        assert "source_chat_agent" in [node for node in nodes]
        
        # Check that the graph has the checkpointer
        assert source_chat_graph.checkpointer is not None
    
    @pytest.mark.asyncio
    async def test_source_chat_state_validation(self):
        """Test that the source chat validates required state fields."""
        # Test with missing source_id
        invalid_state = SourceChatState(
            messages=[HumanMessage(content="Test")],
            source_id="",  # Empty source_id should cause error
            source=None,
            insights=None,
            context=None,
            model_override=None,
            context_indicators=None
        )
        
        config = {"configurable": {"thread_id": "test"}}
        
        # This should raise an error due to missing source_id
        with pytest.raises(ValueError, match="source_id is required"):
            await call_model_with_source_context(invalid_state, config)  # type: ignore[misc, arg-type]


class TestSourceChatGraphExecution:
    """Test the execution of the source chat graph."""
    
    @patch('open_notebook.graphs.source_chat.Source')
    @patch('open_notebook.graphs.source_chat.ContextBuilder')
    @patch('open_notebook.graphs.source_chat.provision_langchain_model')
    @patch('open_notebook.graphs.source_chat.Prompter')
    @pytest.mark.asyncio
    async def test_graph_execution_flow(
        self, 
        mock_prompter,
        mock_provision_model,
        mock_context_builder,
        mock_source_class,
        sample_state,
        sample_config
    ):
        """Test the complete graph execution flow with mocked dependencies."""
        
        # Setup mocks (similar to previous test but for full graph execution)
        mock_builder_instance = AsyncMock()
        mock_builder_instance.build.return_value = {
            "sources": [{"id": "source:test123", "title": "Test"}],
            "insights": [{"id": "insight:test456", "content": "Test insight"}],
            "metadata": {"source_count": 1, "insight_count": 1},
            "total_tokens": 100
        }
        mock_context_builder.return_value = mock_builder_instance
        
        mock_prompter_instance = MagicMock()
        mock_prompter_instance.render.return_value = "Test prompt"
        mock_prompter.return_value = mock_prompter_instance
        
        mock_model = AsyncMock()
        mock_model.invoke.return_value = AIMessage(content="AI response")
        mock_provision_model.return_value = mock_model
        
        # Execute the graph
        result = await source_chat_graph.ainvoke(sample_state, sample_config)
        
        # Verify the result structure
        assert "messages" in result
        assert "source_id" in result
        assert result["source_id"] == "source:test123"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])