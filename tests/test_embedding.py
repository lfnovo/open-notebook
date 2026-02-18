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
            "open_notebook.ai.models.model_manager.get_embedding_model",
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
            "open_notebook.ai.models.model_manager.get_embedding_model",
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
            "open_notebook.ai.models.model_manager.get_embedding_model",
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
            "open_notebook.ai.models.model_manager.get_embedding_model",
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
            "open_notebook.ai.models.model_manager.get_embedding_model",
            new_callable=AsyncMock,
            return_value=mock_model,
        ):
            result = await generate_embedding(
                "# Markdown Header\n\nContent",
                content_type=ContentType.MARKDOWN,
            )
            assert len(result) == 3


    @pytest.mark.asyncio
    async def test_batching(self):
        """Test that large input is split into batches of EMBEDDING_BATCH_SIZE."""
        from unittest.mock import AsyncMock, MagicMock, call, patch

        from open_notebook.utils.embedding import EMBEDDING_BATCH_SIZE

        num_texts = 120
        texts = [f"text_{i}" for i in range(num_texts)]

        mock_model = MagicMock()
        mock_model.model_name = "test-model"

        def make_embeddings(batch):
            return [[float(i)] * 3 for i in range(len(batch))]

        mock_model.aembed = AsyncMock(side_effect=lambda batch: make_embeddings(batch))

        with patch(
            "open_notebook.ai.models.model_manager.get_embedding_model",
            new_callable=AsyncMock,
            return_value=mock_model,
        ):
            result = await generate_embeddings(texts)

            assert len(result) == num_texts
            # 120 texts / 50 batch size = 3 batches (50, 50, 20)
            assert mock_model.aembed.call_count == 3
            assert len(mock_model.aembed.call_args_list[0][0][0]) == EMBEDDING_BATCH_SIZE
            assert len(mock_model.aembed.call_args_list[1][0][0]) == EMBEDDING_BATCH_SIZE
            assert len(mock_model.aembed.call_args_list[2][0][0]) == 20

    @pytest.mark.asyncio
    async def test_batch_retry_on_transient_failure(self):
        """Test that a transient failure is retried and succeeds."""
        from unittest.mock import AsyncMock, MagicMock, patch

        texts = ["text_a", "text_b"]
        mock_model = MagicMock()
        mock_model.model_name = "test-model"

        # Fail once, then succeed
        mock_model.aembed = AsyncMock(
            side_effect=[
                RuntimeError("transient error"),
                [[0.1, 0.2], [0.3, 0.4]],
            ]
        )

        with (
            patch(
                "open_notebook.ai.models.model_manager.get_embedding_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("open_notebook.utils.embedding.EMBEDDING_RETRY_DELAY", 0),
        ):
            result = await generate_embeddings(texts)
            assert result == [[0.1, 0.2], [0.3, 0.4]]
            assert mock_model.aembed.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_retry_exhaustion(self):
        """Test that RuntimeError is raised after all retries are exhausted."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from open_notebook.utils.embedding import EMBEDDING_MAX_RETRIES

        texts = ["text_a"]
        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        mock_model.aembed = AsyncMock(side_effect=RuntimeError("persistent error"))

        with (
            patch(
                "open_notebook.ai.models.model_manager.get_embedding_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("open_notebook.utils.embedding.EMBEDDING_RETRY_DELAY", 0),
        ):
            with pytest.raises(RuntimeError, match="Failed to generate embeddings"):
                await generate_embeddings(texts)
            assert mock_model.aembed.call_count == EMBEDDING_MAX_RETRIES


# ============================================================================
# TEST SUITE 4: Error Classification for 413
# ============================================================================


class TestErrorClassifier413:
    """Test that 413 payload-too-large errors are classified correctly."""

    def test_413_status_code(self):
        from open_notebook.exceptions import ExternalServiceError
        from open_notebook.utils.error_classifier import classify_error

        exc = Exception("HTTP 413: Payload Too Large")
        exc_class, message = classify_error(exc)
        assert exc_class is ExternalServiceError
        assert "payload is too large" in message

    def test_request_entity_too_large(self):
        from open_notebook.exceptions import ExternalServiceError
        from open_notebook.utils.error_classifier import classify_error

        exc = Exception("Request Entity Too Large")
        exc_class, message = classify_error(exc)
        assert exc_class is ExternalServiceError
        assert "payload is too large" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
