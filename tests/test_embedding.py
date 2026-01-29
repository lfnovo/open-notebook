"""
Unit tests for the open_notebook.utils.embedding module.

Tests embedding generation and mean pooling functionality.
"""

import pytest

from open_notebook.utils.embedding import (
    generate_embedding,
    generate_embeddings,
    mean_pool_embeddings,
)

# ============================================================================
# TEST SUITE 1: Mean Pooling
# ============================================================================


class TestMeanPoolEmbeddings:
    """Test suite for mean pooling functionality."""

    @pytest.mark.asyncio
    async def test_single_embedding(self):
        """Test mean pooling with single embedding returns normalized version."""
        embedding = [1.0, 0.0, 0.0]
        result = await mean_pool_embeddings([embedding])
        assert len(result) == 3
        # Should be normalized (already unit length)
        assert abs(result[0] - 1.0) < 0.001
        assert abs(result[1]) < 0.001
        assert abs(result[2]) < 0.001

    @pytest.mark.asyncio
    async def test_two_embeddings(self):
        """Test mean pooling with two embeddings."""
        embeddings = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
        result = await mean_pool_embeddings(embeddings)
        assert len(result) == 3
        # Mean of normalized vectors, then normalized
        # Result should be roughly [0.707, 0.707, 0]
        assert abs(result[0] - result[1]) < 0.001  # x and y should be equal
        assert abs(result[2]) < 0.001  # z should be ~0

    @pytest.mark.asyncio
    async def test_identical_embeddings(self):
        """Test mean pooling with identical embeddings."""
        embedding = [0.5, 0.5, 0.5, 0.5]
        embeddings = [embedding, embedding, embedding]
        result = await mean_pool_embeddings(embeddings)
        assert len(result) == 4
        # Result should be same direction, just normalized
        # Original is already normalized if we normalize it
        import numpy as np
        orig_norm = np.linalg.norm(embedding)
        expected = [v / orig_norm for v in embedding]
        for i in range(4):
            assert abs(result[i] - expected[i]) < 0.001

    @pytest.mark.asyncio
    async def test_empty_list_raises(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            await mean_pool_embeddings([])

    @pytest.mark.asyncio
    async def test_normalization(self):
        """Test that result is normalized to unit length."""
        embeddings = [
            [3.0, 4.0, 0.0],  # Not unit length
            [0.0, 5.0, 0.0],  # Not unit length
        ]
        result = await mean_pool_embeddings(embeddings)
        # Check result is unit length
        import numpy as np
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_high_dimensional(self):
        """Test mean pooling with high-dimensional embeddings."""
        import numpy as np
        # Create random embeddings of dimension 768 (typical embedding size)
        np.random.seed(42)
        embeddings = [
            np.random.randn(768).tolist(),
            np.random.randn(768).tolist(),
            np.random.randn(768).tolist(),
        ]
        result = await mean_pool_embeddings(embeddings)
        assert len(result) == 768
        # Check result is normalized
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 0.001


# ============================================================================
# TEST SUITE 2: Generate Embeddings (requires mocking)
# ============================================================================


class TestGenerateEmbeddings:
    """Test suite for batch embedding generation."""

    @pytest.mark.asyncio
    async def test_empty_list(self):
        """Test that empty list returns empty list."""
        result = await generate_embeddings([])
        assert result == []

    @pytest.mark.asyncio
    async def test_no_model_raises(self):
        """Test that missing model raises ValueError."""
        from unittest.mock import AsyncMock, patch

        with patch(
            "open_notebook.utils.embedding.model_manager.get_embedding_model",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(ValueError, match="No embedding model configured"):
                await generate_embeddings(["test text"])

    @pytest.mark.asyncio
    async def test_successful_embedding(self):
        """Test successful embedding generation with mocked model."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_model = MagicMock()
        mock_model.aembed = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])

        with patch(
            "open_notebook.utils.embedding.model_manager.get_embedding_model",
            new_callable=AsyncMock,
            return_value=mock_model,
        ):
            result = await generate_embeddings(["text1", "text2"])
            assert len(result) == 2
            assert result[0] == [0.1, 0.2, 0.3]
            assert result[1] == [0.4, 0.5, 0.6]
            mock_model.aembed.assert_called_once_with(["text1", "text2"])


# ============================================================================
# TEST SUITE 3: Generate Single Embedding (requires mocking)
# ============================================================================


class TestGenerateEmbedding:
    """Test suite for single embedding generation."""

    @pytest.mark.asyncio
    async def test_empty_text_raises(self):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            await generate_embedding("")

        with pytest.raises(ValueError, match="empty"):
            await generate_embedding("   ")

    @pytest.mark.asyncio
    async def test_short_text_direct_embedding(self):
        """Test that short text is embedded directly without chunking."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_model = MagicMock()
        mock_model.aembed = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

        with patch(
            "open_notebook.utils.embedding.model_manager.get_embedding_model",
            new_callable=AsyncMock,
            return_value=mock_model,
        ):
            result = await generate_embedding("Short text")
            assert result == [0.1, 0.2, 0.3]
            # Should be called with single text
            mock_model.aembed.assert_called_once_with(["Short text"])

    @pytest.mark.asyncio
    async def test_long_text_chunked_and_pooled(self):
        """Test that long text is chunked and mean pooled."""
        from unittest.mock import AsyncMock, MagicMock, patch

        # Create text longer than chunk size
        long_text = "This is a sentence. " * 200  # ~4000 chars

        mock_model = MagicMock()
        # Return multiple embeddings (one per chunk)
        mock_model.aembed = AsyncMock(
            return_value=[
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
            ]
        )

        with patch(
            "open_notebook.utils.embedding.model_manager.get_embedding_model",
            new_callable=AsyncMock,
            return_value=mock_model,
        ):
            result = await generate_embedding(long_text)
            # Should return mean pooled result
            assert len(result) == 3
            # Model should have been called with multiple chunks
            assert mock_model.aembed.called

    @pytest.mark.asyncio
    async def test_content_type_parameter(self):
        """Test that content type parameter is passed through."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from open_notebook.utils.chunking import ContentType

        mock_model = MagicMock()
        mock_model.aembed = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

        with patch(
            "open_notebook.utils.embedding.model_manager.get_embedding_model",
            new_callable=AsyncMock,
            return_value=mock_model,
        ):
            result = await generate_embedding(
                "# Markdown Header\n\nContent",
                content_type=ContentType.MARKDOWN,
            )
            assert len(result) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
