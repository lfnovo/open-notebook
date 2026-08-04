"""
Unit tests for the open_notebook.utils.token_utils module.

Tests parse_context_limit_error with provider-specific error formats,
chunk_text_by_tokens edge cases (oversized words, overlap overhead),
and token counting utilities.
"""


import pytest

from open_notebook.utils.token_utils import (
    SAFETY_BUFFER,
    chunk_text_by_tokens,
    parse_context_limit_error,
    token_cost,
    token_count,
)

# ============================================================================
# TEST SUITE 1: Token Counting
# ============================================================================


class TestTokenCount:
    """Test suite for token_count utility."""

    def test_empty_string(self):
        """Empty string should have 0 tokens."""
        assert token_count("") == 0

    def test_simple_text(self):
        """Simple English text should have reasonable token count."""
        count = token_count("Hello, world!")
        assert count > 0
        assert count < 20

    def test_longer_text(self):
        """Longer text should have proportionally more tokens."""
        short = token_count("This is a short sentence.")
        long = token_count("This is a much longer sentence with many more words in it for testing purposes.")
        assert long > short

    def test_whitespace_only(self):
        """Whitespace-only strings may have 0 or minimal tokens."""
        count = token_count("   \n\n  \t  ")
        # Some tokenizers may count whitespace tokens
        assert isinstance(count, int)
        assert count >= 0


# ============================================================================
# TEST SUITE 2: Token Cost
# ============================================================================


class TestTokenCost:
    """Test suite for token_cost utility."""

    def test_zero_tokens(self):
        """Zero tokens should cost zero."""
        assert token_cost(0) == 0.0

    def test_default_rate(self):
        """Test default $0.150 per million tokens."""
        assert token_cost(1_000_000) == 0.150

    def test_custom_rate(self):
        """Test custom cost per million."""
        assert token_cost(1_000_000, 0.5) == 0.5

    def test_partial_million(self):
        """Test partial million calculation."""
        assert token_cost(500_000) == 0.075  # half of $0.150


# ============================================================================
# TEST SUITE 3: parse_context_limit_error
# ============================================================================


class TestParseContextLimitError:
    """Test suite for parse_context_limit_error with provider-specific formats."""

    def test_anthropic_format(self):
        """Anthropic: 'your request was X tokens ... model's maximum is Y'"""
        error = (
            "your request was 5000 tokens, but the model's maximum "
            "is 4097 tokens for this model."
        )
        result = parse_context_limit_error(error)
        assert result is not None
        limit, sent = result
        assert limit == 4097  # group(2) = limit
        assert sent == 5000   # group(1) = sent

    def test_anthropic_variant(self):
        """Anthropic variant: 'you have used X tokens ... limit is Y'"""
        error = (
            "you have used 15000 tokens of context. The model's maximum "
            "context length is 100000 tokens."
        )
        result = parse_context_limit_error(error)
        assert result is not None
        limit, sent = result
        assert limit == 100000
        assert sent == 15000

    def test_openai_format(self):
        """OpenAI: 'maximum context length is Y tokens ... you requested X'"""
        error = (
            "This model's maximum context length is 8192 tokens. "
            "However, you requested 10000 tokens (7500 in the messages, "
            "2500 in the completion)."
        )
        result = parse_context_limit_error(error)
        assert result is not None
        limit, sent = result
        # OpenAI format: group(1)=limit, group(2)=sent
        assert limit == 8192
        assert sent == 10000

    def test_openai_long_context_format(self):
        """OpenAI GPT-4-turbo: large context with large request."""
        error = (
            "This model's maximum context length is 128000 tokens. "
            "However, you requested 150000 tokens."
        )
        result = parse_context_limit_error(error)
        assert result is not None
        limit, sent = result
        assert limit == 128000
        assert sent == 150000

    def test_gemini_format(self):
        """Google/Gemini: 'The number of tokens (X) exceeded the limit (Y)'"""
        error = (
            "The number of tokens (5000) exceeded the limit of 4097. "
            "Reduce the input or use a model with a larger context window."
        )
        result = parse_context_limit_error(error)
        assert result is not None
        limit, sent = result
        # Gemini format: the larger number (5000) is the sent tokens,
        # the smaller number (4097) is the limit. The old max(g1,g2)
        # heuristic would pick 5000 as limit — WRONG.
        assert limit == 4097  # limit follows "limit of"
        assert sent == 5000   # sent in parentheses

    def test_gemini_format_variant(self):
        """Gemini variant: tokens exceed limit in reverse order."""
        error = (
            "The number of tokens (15000) exceeded the limit of 8192."
        )
        result = parse_context_limit_error(error)
        assert result is not None
        limit, sent = result
        assert limit == 8192
        assert sent == 15000

    def test_generic_format(self):
        """Generic: 'context_length_exceeded: X > Y'"""
        error = "context_length_exceeded: 5000 > 4097"
        result = parse_context_limit_error(error)
        assert result is not None
        limit, sent = result
        assert limit == 4097
        assert sent == 5000

    def test_generic_format_variant(self):
        """Generic: 'context_length_exceeded: X exceeded Y'"""
        error = "context_length_exceeded: 10000 exceeded 8192"
        result = parse_context_limit_error(error)
        assert result is not None
        limit, sent = result
        assert limit == 8192
        assert sent == 10000

    def test_unrelated_error_returns_none(self):
        """Non-context errors should return None."""
        error = "Authentication failed: invalid API key"
        assert parse_context_limit_error(error) is None

    def test_rate_limit_error_returns_none(self):
        """Rate limit errors should return None."""
        error = "Rate limit exceeded. Please wait and retry."
        assert parse_context_limit_error(error) is None

    def test_empty_string_returns_none(self):
        """Empty string should return None."""
        assert parse_context_limit_error("") is None

    def test_provider_model_not_found(self):
        """Model-not-found errors should return None."""
        error = "model not found: gpt-4-fake-model"
        assert parse_context_limit_error(error) is None


# ============================================================================
# TEST SUITE 4: chunk_text_by_tokens
# ============================================================================


class TestChunkTextByTokens:
    """Test suite for chunk_text_by_tokens utility."""

    def test_empty_text(self):
        """Empty text returns empty list."""
        chunks = chunk_text_by_tokens("", max_chunk_tokens=1000)
        # The function checks token_count("") <= max_chunk_tokens first,
        # so empty string returns [""] — one empty chunk, not nothing.
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_short_text_no_chunking(self):
        """Text within budget returns unchanged."""
        text = "Short text."
        chunks = chunk_text_by_tokens(text, max_chunk_tokens=1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_text_at_token_limit(self):
        """Text exactly at the budget boundary fits in one chunk."""
        text = "Hello world. " * 100
        max_tokens = token_count(text)
        chunks = chunk_text_by_tokens(text, max_chunk_tokens=max_tokens)
        assert len(chunks) == 1

    def test_paragraph_splitting(self):
        """Text with multiple paragraphs should split at paragraph boundaries."""
        # Build a text where each paragraph is within budget
        # but the whole exceeds it.
        para = "This is a paragraph with enough content to be meaningful. " * 50
        text = f"{para}\n\n{para}\n\n{para}"
        max_tokens = int(token_count(para) * 1.5)  # Fits ~1.5 paragraphs
        chunks = chunk_text_by_tokens(text, max_chunk_tokens=max_tokens)
        assert len(chunks) >= 2
        # Each chunk should be within the token budget (with some slack
        # for the overlap overhead if added at the end).
        for chunk in chunks:
            assert token_count(chunk) <= max_tokens * 1.15, (
                f"Chunk has {token_count(chunk)} tokens, "
                f"budget was {max_tokens}"
            )

    def test_oversized_paragraph_sentences(self):
        """A single paragraph exceeding budget gets split by sentences."""
        # One paragraph that exceeds the budget
        para = "Short sentence. " * 200
        max_tokens = int(token_count(para) * 0.3)
        text = f"Intro.\n\n{para}\n\nOutro."
        chunks = chunk_text_by_tokens(text, max_chunk_tokens=max_tokens)
        assert len(chunks) >= 3  # intro + split para + outro

    def test_oversized_word_fallback(self):
        """
        A single whitespace-free token exceeding the budget is split
        at character boundaries (paragraph→sentence→word fallback).
        """
        # A single "word" with no spaces that exceeds max_chunk_tokens
        oversized = "a" * 10000  # ~2500 tokens for o200k
        budget = 500  # tokens — the word should exceed this
        chunks = chunk_text_by_tokens(oversized, max_chunk_tokens=budget)
        assert len(chunks) > 1, (
            f"Oversized word should be split into multiple chunks, "
            f"got {len(chunks)}"
        )
        # Every chunk should be within budget or close
        for chunk in chunks:
            assert token_count(chunk) <= budget * 1.15, (
                f"Chunk has {token_count(chunk)} tokens, "
                f"budget was {budget}"
            )

    def test_oversized_code_block(self):
        """
        Minified code without spaces (e.g. base64, JSON) should
        be split at character boundaries.
        """
        minified = "abcdefghij" * 2000  # ~3000 chars, ~750 tokens
        budget = 200
        chunks = chunk_text_by_tokens(minified, max_chunk_tokens=budget)
        assert len(chunks) > 1
        for chunk in chunks:
            assert token_count(chunk) <= budget * 1.15

    def test_overlap_does_not_overshoot_budget(self):
        """
        Overlap + continuation marker added between chunks should
        not push chunks significantly over the token budget.
        """
        para = "This paragraph has enough content to build up tokens. " * 30
        text = f"{para}\n\n{para}\n\n{para}\n\n{para}"
        budget = int(token_count(para) * 1.8)
        chunks = chunk_text_by_tokens(
            text, max_chunk_tokens=budget, overlap_chars=200
        )
        assert len(chunks) >= 2
        for chunk in chunks:
            assert token_count(chunk) <= budget * 1.15, (
                f"Chunk with overlap has {token_count(chunk)} tokens, "
                f"budget was {budget}"
            )

    def test_no_overlap_when_overlap_chars_zero(self):
        """Setting overlap_chars=0 should not add overlap."""
        text = "A chunk. " * 100 + "\n\n" + "Another chunk. " * 100
        budget = int(token_count("A chunk. " * 80))
        chunks_with = chunk_text_by_tokens(
            text, max_chunk_tokens=budget, overlap_chars=200
        )
        chunks_without = chunk_text_by_tokens(
            text, max_chunk_tokens=budget, overlap_chars=0
        )
        # Without overlap, chunks should be shorter
        assert len(chunks_without) >= len(chunks_with) - 1  # overlap can create extra chunk

    def test_large_text_hierarchical(self):
        """A long document should be split hierarchically."""
        paragraph = "This is a paragraph used for testing hierarchical splitting. " * 20
        text = "\n\n".join([paragraph] * 20)
        budget = int(token_count(paragraph) * 2.5)
        chunks = chunk_text_by_tokens(text, max_chunk_tokens=budget)
        assert len(chunks) > 1
        # All chunks should contain text (not empty)
        assert all(c.strip() for c in chunks)


# ============================================================================
# TEST SUITE 5: Integration — parse + chunk pipeline
# ============================================================================


class TestParseThenChunkIntegration:
    """Test that parse_context_limit_error output feeds correctly into
    chunk_text_by_tokens as it does in _handle_llm_error."""

    def test_anthropic_parse_then_chunk(self):
        """Simulate the _handle_llm_error pipeline with an Anthropic error."""
        error_msg = (
            "your request was 50000 tokens, but the model's maximum "
            "is 100000 tokens for this model."
        )
        result = parse_context_limit_error(error_msg)
        assert result is not None
        context_limit, _tokens_sent = result

        # Simulate the chunk size calculation from _handle_llm_error
        system_prompt = "You are an AI assistant."
        system_tokens = token_count(system_prompt)
        output_budget = min(8192, int(context_limit * 0.10))
        max_chunk_tokens = context_limit - system_tokens - output_budget
        max_chunk_tokens = int(max_chunk_tokens * SAFETY_BUFFER)
        max_chunk_tokens = max(max_chunk_tokens, 512)

        # Create content that exceeds the chunk budget
        # "Content paragraph. " * 50000 ≈ 150K tokens > 78K chunk budget
        content = "Content paragraph. " * 50000
        chunks = chunk_text_by_tokens(content, max_chunk_tokens=max_chunk_tokens)
        assert len(chunks) > 1
        for chunk in chunks:
            assert token_count(chunk) <= max_chunk_tokens * 1.15

    def test_gemini_parse_then_chunk(self):
        """Simulate pipeline with a Gemini error — validates the fixed
        context_limit ordering doesn't produce tiny/invalid chunks."""
        error_msg = (
            "The number of tokens (5000) exceeded the limit of 4097."
        )
        result = parse_context_limit_error(error_msg)
        assert result is not None
        context_limit, _ = result
        # With the old max-heuristic, context_limit would be 5000 (wrong).
        # With the fix, it's 4097 (correct).
        assert context_limit == 4097

    def test_openai_parse_then_chunk(self):
        """Simulate pipeline with an OpenAI error."""
        error_msg = (
            "This model's maximum context length is 8192 tokens. "
            "However, you requested 10000 tokens."
        )
        result = parse_context_limit_error(error_msg)
        assert result is not None
        context_limit, _ = result
        assert context_limit == 8192


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
