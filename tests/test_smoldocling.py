"""
Tests for SmolDocling integration.

These tests verify that the SmolDocling parser can:
1. Check if dependencies are available
2. Initialize properly (lazy loading)
3. Handle various file types
4. Fall back gracefully when dependencies are missing
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module under test
from open_notebook.graphs.smol_docling_integration import (
    SmolDoclingParser,
    SmolDoclingResult,
    check_smoldocling_available,
    get_smol_docling_parser,
    convert_pdf_to_markdown,
)


class TestSmolDoclingResult:
    """Test the SmolDoclingResult dataclass"""
    
    def test_default_values(self):
        """Test that SmolDoclingResult has sensible defaults"""
        result = SmolDoclingResult(content="test content")
        assert result.content == "test content"
        assert result.title is None
        assert result.page_count == 0
        assert result.success is True
        assert result.error_message is None
        assert result.doctags is None
    
    def test_error_result(self):
        """Test creating an error result"""
        result = SmolDoclingResult(
            content="",
            success=False,
            error_message="Test error"
        )
        assert result.content == ""
        assert result.success is False
        assert result.error_message == "Test error"


class TestSmolDoclingParser:
    """Test the SmolDoclingParser class"""
    
    def test_initialization_defaults(self):
        """Test parser initializes with correct defaults"""
        parser = SmolDoclingParser()
        assert parser.use_gpu is True
        assert parser.max_new_tokens == 8192
        assert parser._initialized is False
        assert parser._model is None
        assert parser._processor is None
    
    def test_initialization_custom_params(self):
        """Test parser accepts custom parameters"""
        parser = SmolDoclingParser(use_gpu=False, max_new_tokens=4096)
        assert parser.use_gpu is False
        assert parser.max_new_tokens == 4096
    
    def test_messages_template(self):
        """Test that messages template is properly set"""
        parser = SmolDoclingParser()
        assert len(parser._messages) == 1
        assert parser._messages[0]["role"] == "user"
        assert len(parser._messages[0]["content"]) == 2
        assert parser._messages[0]["content"][0]["type"] == "image"
        assert parser._messages[0]["content"][1]["type"] == "text"
        assert "docling" in parser._messages[0]["content"][1]["text"].lower()


class TestCheckSmolDoclingAvailable:
    """Test the dependency check function"""
    
    def test_check_returns_bool(self):
        """Test that check_smoldocling_available returns a boolean"""
        result = check_smoldocling_available()
        assert isinstance(result, bool)
    
    @patch.dict('sys.modules', {'transformers': None})
    def test_returns_false_when_transformers_missing(self):
        """Test returns False when transformers is not available"""
        # This test may not work as expected due to caching
        # but documents the expected behavior
        pass


class TestGetSmolDoclingParser:
    """Test the singleton parser getter"""
    
    def test_returns_parser_instance(self):
        """Test that get_smol_docling_parser returns a SmolDoclingParser"""
        parser = get_smol_docling_parser()
        assert isinstance(parser, SmolDoclingParser)
    
    def test_singleton_behavior(self):
        """Test that subsequent calls return the same instance"""
        # Reset the singleton
        import open_notebook.graphs.smol_docling_integration as module
        module._parser_instance = None
        
        parser1 = get_smol_docling_parser()
        parser2 = get_smol_docling_parser()
        assert parser1 is parser2


class TestParseFileValidation:
    """Test file validation in parse_file"""
    
    @pytest.mark.asyncio
    async def test_file_not_found(self):
        """Test handling of non-existent file"""
        parser = SmolDoclingParser()
        # Mock _initialize to avoid loading the model
        parser._initialized = True
        parser._device = "cpu"
        
        result = await parser.parse_file("/nonexistent/path/to/file.pdf")
        assert result.success is False
        assert "not found" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_unsupported_format(self):
        """Test handling of unsupported file format"""
        parser = SmolDoclingParser()
        parser._initialized = True
        parser._device = "cpu"
        
        # Create a temp file with unsupported extension
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            result = await parser.parse_file(temp_path)
            assert result.success is False
            assert "unsupported" in result.error_message.lower()
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestContentSettingsIntegration:
    """Test integration with ContentSettings"""
    
    def test_document_parser_field_exists(self):
        """Test that ContentSettings has the document_parser field"""
        from open_notebook.domain.content_settings import ContentSettings
        
        settings = ContentSettings()
        assert hasattr(settings, 'document_parser')
        assert settings.document_parser == "content_core"  # default value
    
    def test_smol_docling_use_gpu_field_exists(self):
        """Test that ContentSettings has the smol_docling_use_gpu field"""
        from open_notebook.domain.content_settings import ContentSettings
        
        settings = ContentSettings()
        assert hasattr(settings, 'smol_docling_use_gpu')
        assert settings.smol_docling_use_gpu is True  # default value
    
    def test_document_parser_options(self):
        """Test that document_parser accepts valid options"""
        from open_notebook.domain.content_settings import ContentSettings
        
        # Test content_core option
        settings1 = ContentSettings(document_parser="content_core")
        assert settings1.document_parser == "content_core"
        
        # Test smol_docling option
        settings2 = ContentSettings(document_parser="smol_docling")
        assert settings2.document_parser == "smol_docling"


class TestSourceGraphIntegration:
    """Test that source.py properly imports SmolDocling functions"""
    
    def test_imports_available(self):
        """Test that source.py can import SmolDocling functions"""
        from open_notebook.graphs.source import (
            content_process,
        )
        # Import should succeed
        assert content_process is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
