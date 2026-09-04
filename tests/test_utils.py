"""
Unit tests for the open_notebook.utils module.

This test suite focuses on testing utility functions that perform actual logic
without heavy mocking - string processing, validation, and algorithms.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.domain.notebook import Source
from open_notebook.graphs.source_chat import (
    _format_source_context,
    _source_content_is_available,
)
from open_notebook.utils import (
    clean_thinking_content,
    compare_versions,
    get_installed_version,
    parse_thinking_content,
    remove_non_ascii,
    remove_non_printable,
    token_count,
)
from open_notebook.utils.context_builder import (
    SOURCE_TRUNCATION_NOTICE,
    _truncate_source_to_token_budget,
    build_source_context,
)

# ============================================================================
# TEST SUITE 1: Text Utilities
# ============================================================================


class TestTextUtilities:
    """Test suite for text utility functions."""

    def test_remove_non_ascii(self):
        """Test removal of non-ASCII characters."""
        # Text with various non-ASCII characters
        text_with_unicode = "Hello 世界 café naïve émoji 🎉"
        result = remove_non_ascii(text_with_unicode)

        # Should only contain ASCII characters
        assert result == "Hello  caf nave moji "
        # All characters should be in ASCII range
        assert all(ord(char) < 128 for char in result)

    def test_remove_non_ascii_pure_ascii(self):
        """Test that pure ASCII text is unchanged."""
        text = "Hello World 123 !@#"
        result = remove_non_ascii(text)
        assert result == text

    def test_remove_non_printable(self):
        """Test removal of non-printable characters."""
        # Text with various Unicode whitespace and control chars
        text = "Hello\u2000World\u200b\u202fTest"
        result = remove_non_printable(text)

        # Should have regular spaces and printable chars only
        assert "Hello" in result
        assert "World" in result
        assert "Test" in result

    def test_remove_non_printable_preserves_newlines(self):
        """Test that newlines and tabs are preserved."""
        text = "Line1\nLine2\tTabbed"
        result = remove_non_printable(text)
        assert "\n" in result
        assert "\t" in result

    def test_parse_thinking_content_basic(self):
        """Test parsing single thinking block."""
        content = "<think>This is my thinking</think>Here is my answer"
        thinking, cleaned = parse_thinking_content(content)

        assert thinking == "This is my thinking"
        assert cleaned == "Here is my answer"

    def test_parse_thinking_content_multiple_tags(self):
        """Test parsing multiple thinking blocks."""
        content = "<think>First thought</think>Answer<think>Second thought</think>More"
        thinking, cleaned = parse_thinking_content(content)

        assert "First thought" in thinking
        assert "Second thought" in thinking
        assert "<think>" not in cleaned
        assert "Answer" in cleaned
        assert "More" in cleaned

    def test_parse_thinking_content_no_tags(self):
        """Test parsing content without thinking tags."""
        content = "Just regular content"
        thinking, cleaned = parse_thinking_content(content)

        assert thinking == ""
        assert cleaned == "Just regular content"

    def test_parse_thinking_content_malformed_no_open_tag(self):
        """Test parsing malformed output where opening <think> tag is missing."""
        content = "Some thinking content</think>Here is my answer"
        thinking, cleaned = parse_thinking_content(content)

        assert thinking == "Some thinking content"
        assert cleaned == "Here is my answer"

    def test_parse_thinking_content_invalid_input(self):
        """Test parsing with invalid input types."""
        # Non-string input (intentionally violates the signature to test the
        # runtime guard)
        thinking, cleaned = parse_thinking_content(None)  # type: ignore[arg-type]
        assert thinking == ""
        assert cleaned == ""

        # Integer input (same intentional violation)
        thinking, cleaned = parse_thinking_content(123)  # type: ignore[arg-type]
        assert thinking == ""
        assert cleaned == "123"

    def test_parse_thinking_content_large_content(self):
        """Test that very large content is not processed."""
        large_content = "x" * 200000  # > 100KB limit
        thinking, cleaned = parse_thinking_content(large_content)

        # Should return unchanged due to size limit
        assert thinking == ""
        assert cleaned == large_content

    def test_clean_thinking_content(self):
        """Test convenience function for cleaning thinking content."""
        content = "<think>Internal thoughts</think>Public response"
        result = clean_thinking_content(content)

        assert "<think>" not in result
        assert "Public response" in result
        assert "Internal thoughts" not in result


# ============================================================================
# TEST SUITE 2: Token Utilities
# ============================================================================


class TestTokenUtilities:
    """Test suite for token counting fallback behavior."""

    def test_token_count_fallback(self):
        """Test fallback when tiktoken raises an error."""
        from unittest.mock import patch

        # Make tiktoken raise an ImportError to trigger fallback
        with patch(
            "tiktoken.get_encoding", side_effect=ImportError("tiktoken not available")
        ):
            text = "one two three four five"
            count = token_count(text)

            # Fallback uses word count * 1.3
            # 5 words * 1.3 = 6.5 -> 6
            assert isinstance(count, int)
            assert count > 0

    def test_token_count_network_error_fallback(self):
        """Test fallback when tiktoken raises a network error (issue #264).

        In offline environments tiktoken.get_encoding() tries to download the
        encoding file and raises a URLError/OSError, not an ImportError.
        The except clause must catch Exception (not only ImportError) so that
        these network failures also fall through to the word-count estimate.
        """
        import urllib.error
        from unittest.mock import patch

        with patch(
            "tiktoken.get_encoding",
            side_effect=urllib.error.URLError("No network (simulated offline)"),
        ):
            text = "one two three four five"
            count = token_count(text)

            # Must not raise; must return a positive int via the fallback
            assert isinstance(count, int)
            assert count > 0


# ============================================================================
# TEST SUITE 3: Version Utilities
# ============================================================================


class TestVersionUtilities:
    """Test suite for version management functions."""

    def test_compare_versions_equal(self):
        """Test comparing equal versions."""
        result = compare_versions("1.0.0", "1.0.0")
        assert result == 0

    def test_compare_versions_less_than(self):
        """Test comparing when first version is less."""
        result = compare_versions("1.0.0", "2.0.0")
        assert result == -1

        result = compare_versions("1.0.0", "1.1.0")
        assert result == -1

        result = compare_versions("1.0.0", "1.0.1")
        assert result == -1

    def test_compare_versions_greater_than(self):
        """Test comparing when first version is greater."""
        result = compare_versions("2.0.0", "1.0.0")
        assert result == 1

        result = compare_versions("1.1.0", "1.0.0")
        assert result == 1

        result = compare_versions("1.0.1", "1.0.0")
        assert result == 1

    def test_compare_versions_prerelease(self):
        """Test comparing versions with pre-release tags."""
        result = compare_versions("1.0.0", "1.0.0-alpha")
        assert result == 1  # Release > pre-release

        result = compare_versions("1.0.0-beta", "1.0.0-alpha")
        assert result == 1  # beta > alpha

    def test_get_installed_version_success(self):
        """Test getting installed package version."""
        # Test with a known installed package
        version = get_installed_version("pytest")
        assert isinstance(version, str)
        assert len(version) > 0
        # Should look like a version (has dots)
        assert "." in version

    def test_get_installed_version_not_found(self):
        """Test getting version of non-existent package."""
        from importlib.metadata import PackageNotFoundError

        with pytest.raises(PackageNotFoundError):
            get_installed_version("this-package-does-not-exist-12345")

    def test_get_version_from_github_invalid_url(self):
        """Test GitHub version fetch with invalid URL."""
        from open_notebook.utils.version_utils import get_version_from_github

        with pytest.raises(ValueError, match="Not a GitHub URL"):
            get_version_from_github("https://example.com/repo")

        with pytest.raises(ValueError, match="Invalid GitHub repository URL"):
            get_version_from_github("https://github.com/")


# ============================================================================
# TEST SUITE 4: Source Context Building
# ============================================================================


def _mock_source(insights):
    source = SimpleNamespace(id="source:123")
    source.get_context = AsyncMock(
        return_value={"id": "source:123", "title": "T", "full_text": "body"}
    )
    source.get_insights = AsyncMock(return_value=insights)
    return source


def _insight(insight_id, content="insight content"):
    return SimpleNamespace(id=insight_id, insight_type="summary", content=content)


class TestBuildSourceContext:
    """Test suite for build_source_context (used by the source-chat graph)."""

    @pytest.mark.asyncio
    async def test_source_and_insights_shape(self):
        """The response carries the source's full context and its insights."""
        source = _mock_source([_insight("source_insight:1")])

        with patch(
            "open_notebook.utils.context_builder.Source.get",
            new=AsyncMock(return_value=source),
        ) as mock_get:
            result = await build_source_context("123")

        mock_get.assert_awaited_once_with("source:123")  # bare id gets prefixed
        source.get_context.assert_awaited_once_with(
            context_size="long",
            insights=source.get_insights.return_value,
        )
        assert result["sources"] == [
            {
                "id": "source:123",
                "title": "T",
                "full_text": "body",
                "insights": [],
            }
        ]
        assert result["insights"] == [
            {
                "id": "source_insight:1",
                "source_id": "source:123",
                "insight_type": "summary",
                "content": "insight content",
            }
        ]
        assert result["notes"] == []
        assert result["total_items"] == 2
        assert result["total_tokens"] > 0
        assert result["metadata"] == {
            "source_count": 1,
            "note_count": 0,
            "insight_count": 1,
            "source_text_status": "available",
            "source_truncated": False,
        }
        assert result["total_tokens"] == token_count(_format_source_context(result))

    @pytest.mark.asyncio
    async def test_preserves_insights_that_fit_token_budget(self):
        """Insights are retained in order while they fit the token budget."""
        big = "word " * 300
        source = _mock_source(
            [_insight("source_insight:1", big), _insight("source_insight:2", big)]
        )

        with patch(
            "open_notebook.utils.context_builder.Source.get",
            new=AsyncMock(return_value=source),
        ):
            result = await build_source_context("source:123", max_tokens=600)

        # Budget fits the source and the first insight, not the second
        assert len(result["sources"]) == 1
        assert [i["id"] for i in result["insights"]] == ["source_insight:1"]
        assert result["total_tokens"] <= 600

    @pytest.mark.asyncio
    async def test_real_source_full_text_reaches_formatted_prompt(self):
        """Source.get_context(long) carries persisted full text into the prompt."""
        full_text = "Complete source text that must reach Source Chat."
        source = Source(id="source:123", title="T", full_text=full_text)
        mock_get_insights = AsyncMock(return_value=[])

        with (
            patch(
                "open_notebook.utils.context_builder.Source.get",
                new=AsyncMock(return_value=source),
            ),
            patch.object(Source, "get_insights", new=mock_get_insights),
        ):
            result = await build_source_context("source:123", max_tokens=500)

        formatted = _format_source_context(result)
        assert full_text in formatted
        assert SOURCE_TRUNCATION_NOTICE not in formatted
        assert result["metadata"]["source_text_status"] == "available"
        assert result["metadata"]["source_truncated"] is False
        mock_get_insights.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_large_source_is_deterministically_and_explicitly_truncated(self):
        """An oversized source keeps a marked prefix instead of disappearing."""
        full_text = "evidence " * 1000
        source = _mock_source([])
        source.get_context.return_value["full_text"] = full_text

        with patch(
            "open_notebook.utils.context_builder.Source.get",
            new=AsyncMock(return_value=source),
        ):
            first = await build_source_context("source:123", max_tokens=120)
            second = await build_source_context("source:123", max_tokens=120)

        first_text = first["sources"][0]["full_text"]
        assert first_text == second["sources"][0]["full_text"]
        assert first_text.endswith(SOURCE_TRUNCATION_NOTICE)
        assert len(first_text) < len(full_text)
        assert first["total_tokens"] <= 120
        assert first["metadata"]["source_text_status"] == "truncated"
        assert first["metadata"]["source_truncated"] is True
        assert first["total_tokens"] == token_count(_format_source_context(first))
        assert _source_content_is_available(first["sources"][0], first)

        formatted = _format_source_context(first)
        assert first_text in formatted
        assert SOURCE_TRUNCATION_NOTICE in formatted

    @pytest.mark.parametrize(
        ("status", "full_text", "expected"),
        [
            ("available", "complete text", True),
            ("truncated", "partial text", True),
            ("missing", "", False),
            ("omitted_budget", "stale text", False),
            (None, "legacy text", True),
            (None, "", False),
        ],
    )
    def test_source_content_availability_rules(
        self,
        status,
        full_text,
        expected,
    ):
        """Explicit statuses win, while legacy contexts fall back to their text."""
        metadata = {} if status is None else {"source_text_status": status}

        assert (
            _source_content_is_available(
                {"id": "source:123", "full_text": full_text},
                {"metadata": metadata},
            )
            is expected
        )

    @pytest.mark.asyncio
    async def test_large_source_reserves_budget_for_insights(self):
        """An oversized source leaves deterministic headroom for insights."""
        full_text = "evidence " * 1000
        source = _mock_source([_insight("source_insight:1")])
        source.get_context.return_value["full_text"] = full_text

        with patch(
            "open_notebook.utils.context_builder.Source.get",
            new=AsyncMock(return_value=source),
        ):
            result = await build_source_context("source:123", max_tokens=500)

        assert [insight["id"] for insight in result["insights"]] == ["source_insight:1"]
        assert result["sources"][0]["full_text"].endswith(SOURCE_TRUNCATION_NOTICE)
        assert result["total_tokens"] <= 500
        assert result["metadata"]["insight_count"] == 1
        assert result["metadata"]["source_text_status"] == "truncated"

    @pytest.mark.asyncio
    async def test_tiny_budget_omits_source_with_explicit_status(self):
        """A budget smaller than source metadata never returns oversized context."""
        source = _mock_source([])
        source.get_context.return_value["full_text"] = "evidence " * 1000

        with patch(
            "open_notebook.utils.context_builder.Source.get",
            new=AsyncMock(return_value=source),
        ):
            result = await build_source_context("source:123", max_tokens=1)

        assert result["sources"] == []
        assert result["total_tokens"] <= 1
        assert result["metadata"]["source_text_status"] == "omitted_budget"

    def test_notice_only_budget_omits_source(self):
        """A truncation notice alone is not reported as available source text."""
        source_context = {
            "id": "source:123",
            "title": "T",
            "full_text": "evidence " * 100,
            "insights": [],
        }
        notice_only = {
            **source_context,
            "full_text": SOURCE_TRUNCATION_NOTICE,
        }
        one_character = {
            **source_context,
            "full_text": "e" + SOURCE_TRUNCATION_NOTICE,
        }
        notice_tokens = token_count(
            _format_source_context(
                {"sources": [notice_only], "insights": []}
            )
        )
        one_character_tokens = token_count(
            _format_source_context(
                {"sources": [one_character], "insights": []}
            )
        )
        assert notice_tokens < one_character_tokens

        budgeted_source, source_truncated = _truncate_source_to_token_budget(
            source_context,
            one_character_tokens - 1,
        )

        assert budgeted_source is None
        assert source_truncated is True

    def test_truncation_handles_non_monotonic_bpe_counts(self):
        """A longer fitting token prefix survives a shorter over-budget one."""
        full_text = "abcdefghij"
        source_context = {
            "id": "source:123",
            "title": "T",
            "full_text": full_text,
            "insights": [],
        }

        class NonMonotonicEncoding:
            def encode(self, text, **_kwargs):
                if text == full_text:
                    return list(range(len(full_text)))
                if SOURCE_TRUNCATION_NOTICE in text:
                    prefix = text.split("**Content:**\n", maxsplit=1)[1].split(
                        SOURCE_TRUNCATION_NOTICE,
                        maxsplit=1,
                    )[0]
                    token_counts = {8: 11, 9: 10, 10: 12}
                    return list(range(token_counts.get(len(prefix), len(prefix) + 1)))
                return list(range(20))

            def decode_bytes(self, tokens):
                return full_text[: len(tokens)].encode()

        with patch(
            "tiktoken.get_encoding",
            return_value=NonMonotonicEncoding(),
        ):
            budgeted_source, source_truncated = _truncate_source_to_token_budget(
                source_context,
                max_tokens=10,
            )

        assert budgeted_source is not None
        assert budgeted_source["full_text"] == (
            full_text[:9] + SOURCE_TRUNCATION_NOTICE
        )
        assert source_truncated is True

    def test_token_prefix_search_has_bounded_candidate_checks(self):
        """Large tokenized sources do not trigger a linear re-encode scan."""
        full_text = "x" * 10_000
        source_context = {
            "id": "source:123",
            "title": "T",
            "full_text": full_text,
            "insights": [],
        }

        class CountingEncoding:
            def __init__(self):
                self.encode_calls = 0

            def encode(self, text, **_kwargs):
                self.encode_calls += 1
                if text == full_text:
                    return list(range(len(full_text)))
                if SOURCE_TRUNCATION_NOTICE in text:
                    prefix = text.split("**Content:**\n", maxsplit=1)[1].split(
                        SOURCE_TRUNCATION_NOTICE,
                        maxsplit=1,
                    )[0]
                    return list(range(len(prefix) + 20))
                return list(range(len(full_text) + 20))

            def decode_bytes(self, tokens):
                return ("x" * len(tokens)).encode()

        encoding = CountingEncoding()
        with patch("tiktoken.get_encoding", return_value=encoding):
            budgeted_source, source_truncated = _truncate_source_to_token_budget(
                source_context,
                max_tokens=1_000,
            )

        assert budgeted_source is not None
        assert budgeted_source["full_text"].startswith("x" * 980)
        assert source_truncated is True
        assert encoding.encode_calls < 35

    @pytest.mark.asyncio
    async def test_large_source_reuses_initial_tokenization(self):
        """Source Chat does not re-tokenize the full document during truncation."""
        full_text = "x" * 10_000
        source = _mock_source([])
        source.get_context.return_value["full_text"] = full_text

        class CountingEncoding:
            def __init__(self):
                self.full_text_calls = 0
                self.full_render_calls = 0

            def encode(self, text, **_kwargs):
                if text == full_text:
                    self.full_text_calls += 1
                    return list(range(len(full_text)))
                if full_text in text:
                    self.full_render_calls += 1
                    return list(range(len(full_text) + 20))
                if SOURCE_TRUNCATION_NOTICE in text:
                    prefix = text.split("**Content:**\n", maxsplit=1)[1].split(
                        SOURCE_TRUNCATION_NOTICE,
                        maxsplit=1,
                    )[0]
                    return list(range(len(prefix) + 20))
                return []

            def decode_bytes(self, tokens):
                return ("x" * len(tokens)).encode()

        encoding = CountingEncoding()
        with (
            patch(
                "open_notebook.utils.context_builder.Source.get",
                new=AsyncMock(return_value=source),
            ),
            patch("tiktoken.get_encoding", return_value=encoding),
        ):
            result = await build_source_context("source:123", max_tokens=1_000)

        assert result["metadata"]["source_truncated"] is True
        assert encoding.full_render_calls == 1
        assert encoding.full_text_calls == 1

    def test_incomplete_utf8_prefix_is_not_reported_as_source_text(self):
        """A decoded-empty token prefix follows the omitted-budget path."""
        full_text = "🙂"
        source_context = {
            "id": "source:123",
            "title": "T",
            "full_text": full_text,
            "insights": [],
        }

        class IncompleteEncoding:
            def encode(self, text, **_kwargs):
                if text == full_text:
                    return [1]
                if SOURCE_TRUNCATION_NOTICE in text:
                    return [1]
                return list(range(20))

            def decode_bytes(self, _tokens):
                return b"\xf0"

        with patch("tiktoken.get_encoding", return_value=IncompleteEncoding()):
            budgeted_source, source_truncated = _truncate_source_to_token_budget(
                source_context,
                max_tokens=10,
            )

        assert budgeted_source is None
        assert source_truncated is True

    def test_word_fallback_search_has_logarithmic_candidate_checks(self):
        """Offline fallback does not repeatedly scan every word prefix."""
        full_text = "word " * 1_000
        source_context = {
            "id": "source:123",
            "title": "T",
            "full_text": full_text,
            "insights": [],
        }

        def fallback_count(text):
            return int(len(text.split()) * 1.3)

        with (
            patch("tiktoken.get_encoding", side_effect=OSError("offline")),
            patch(
                "open_notebook.utils.context_builder.token_count",
                side_effect=fallback_count,
            ) as mock_token_count,
        ):
            budgeted_source, source_truncated = _truncate_source_to_token_budget(
                source_context,
                max_tokens=100,
            )

        assert budgeted_source is not None
        assert source_truncated is True
        assert mock_token_count.call_count < 15

    def test_formatter_does_not_apply_a_second_character_limit(self):
        """Formatting preserves text already accepted by the token budget."""
        full_text = "x" * 6000
        formatted = _format_source_context(
            {
                "sources": [
                    {
                        "id": "source:123",
                        "title": "T",
                        "full_text": full_text,
                    }
                ],
                "insights": [],
                "total_tokens": token_count(full_text),
                "metadata": {
                    "source_count": 1,
                    "insight_count": 0,
                    "source_text_status": "available",
                },
            }
        )

        assert full_text in formatted
        formatted_content = formatted.split("**Content:**\n", maxsplit=1)[1]
        assert formatted_content == f"{full_text}\n"
        assert "[Content truncated]" not in formatted
        assert "CONTEXT METADATA" not in formatted

    @pytest.mark.asyncio
    async def test_missing_source_text_is_reported_honestly(self):
        """A source without text is identified without a content indicator."""
        source = _mock_source([_insight("source_insight:1")])
        source.get_context.return_value["full_text"] = None

        with patch(
            "open_notebook.utils.context_builder.Source.get",
            new=AsyncMock(return_value=source),
        ):
            result = await build_source_context("source:123", max_tokens=500)

        formatted = _format_source_context(result)
        assert "[Source text is unavailable in this context.]" in formatted
        assert result["metadata"]["source_text_status"] == "missing"
        assert not _source_content_is_available(result["sources"][0], result)
        assert result["metadata"]["insight_count"] == 1

    @pytest.mark.asyncio
    async def test_missing_source_yields_empty_context(self):
        """A missing source produces an empty context, not an error."""
        from open_notebook.exceptions import NotFoundError

        with patch(
            "open_notebook.utils.context_builder.Source.get",
            new=AsyncMock(side_effect=NotFoundError("nope")),
        ):
            result = await build_source_context("source:missing")

        assert result["sources"] == []
        assert result["insights"] == []
        assert result["total_tokens"] == 0
        assert result["metadata"]["source_text_status"] == "not_found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
