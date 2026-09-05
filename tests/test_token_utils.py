"""Context-limit helpers in open_notebook.utils.token_utils.

`is_context_limit_error` is a thin wrapper over `error_classifier.classify_error`
so the codebase has a single list of provider wordings; these tests pin that
delegation and the chunk output-budget floor.
"""

import pytest

from open_notebook.utils.token_utils import (
    MIN_CHUNK_OUTPUT_TOKENS,
    OUTPUT_RATIO,
    calculate_output_buffer,
    chunk_text_by_tokens,
    get_context_limit_from_error,
    is_context_limit_error,
    token_count,
)


class TestIsContextLimitError:
    @pytest.mark.parametrize(
        "message",
        [
            "This model's maximum context length is 8192 tokens.",
            "prompt is too long: 142900 tokens > 200000 maximum",
            "The input token count (250012) exceeds the maximum number of tokens allowed (131072).",
            "Error code: 400 - context_length_exceeded",
        ],
    )
    def test_context_limit_wordings(self, message):
        assert is_context_limit_error(Exception(message)) is True

    @pytest.mark.parametrize(
        "message",
        [
            "Rate limit exceeded. Please wait a moment.",
            "Error code: 429 - too many requests",
            "Error code: 401 - invalid api key",
            "Error code: 503 - service unavailable",
            "Connection refused",
            "Something else entirely",
        ],
    )
    def test_non_context_errors(self, message):
        assert is_context_limit_error(Exception(message)) is False


class TestGetContextLimitFromError:
    @pytest.mark.parametrize(
        "message, expected",
        [
            ("prompt is too long: 142900 tokens > 200000 maximum", (142900, 200000)),
            (
                "This model's maximum context length is 8192 tokens. However, your messages resulted in 10500 tokens.",
                (10500, 8192),
            ),
            (
                "The input token count (250012) exceeds the maximum number of tokens allowed (131072).",
                (250012, 131072),
            ),
        ],
    )
    def test_parses_known_wordings(self, message, expected):
        assert get_context_limit_from_error(Exception(message), 8192) == expected

    def test_falls_back_to_default(self):
        assert get_context_limit_from_error(Exception("context window exceeded"), 4096) == (
            None,
            4096,
        )


class TestCalculateOutputBuffer:
    @pytest.mark.parametrize(
        "context_limit, expected",
        [
            (8192, 2048),  # 10% would be 819 — floored to MIN_CHUNK_OUTPUT_TOKENS
            (4096, 1024),  # floor capped at a quarter of a tiny window
            (128000, 12800),  # large windows keep the 10% ratio
        ],
    )
    def test_floor_and_ratio(self, context_limit, expected):
        assert calculate_output_buffer(context_limit) == expected

    def test_constants_agree_with_table(self):
        assert MIN_CHUNK_OUTPUT_TOKENS == 2048
        assert OUTPUT_RATIO == 0.10


class TestChunkTextByTokens:
    def test_chunks_respect_limit(self):
        text = "\n\n".join(f"Paragraph {i}. " + "word " * 40 for i in range(30))
        chunks = chunk_text_by_tokens(text, 200)

        assert len(chunks) > 1
        assert all(token_count(c) <= 200 for c in chunks)
        assert "".join(chunks).replace("\n", "").replace(" ", "") == text.replace(
            "\n", ""
        ).replace(" ", "")
