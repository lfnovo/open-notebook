"""
Unit tests for the open_notebook.utils module.

This test suite focuses on testing utility functions that perform actual logic
without heavy mocking - string processing, validation, and algorithms.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from open_notebook.utils import (
    clean_thinking_content,
    compare_versions,
    get_installed_version,
    parse_thinking_content,
    remove_non_ascii,
    remove_non_printable,
    token_count,
)
from open_notebook.utils.context_builder import build_source_context

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
    return SimpleNamespace(
        id=insight_id, insight_type="summary", content=content
    )


class TestBuildSourceContext:
    """Test suite for build_source_context (used by the source-chat graph)."""

    @pytest.mark.asyncio
    async def test_source_and_insights_shape(self):
        """The response carries the source's full-text context and its insights."""
        source = _mock_source([_insight("source_insight:1")])

        with patch(
            "open_notebook.utils.context_builder.Source.get",
            new=AsyncMock(return_value=source),
        ) as mock_get:
            result = await build_source_context("123")

        mock_get.assert_awaited_once_with("source:123")  # bare id gets prefixed
        # Long context is used so full_text is always included — a source
        # with no insights would otherwise leave the LLM with only the title.
        source.get_context.assert_awaited_once_with(context_size="long")
        assert result["sources"] == [
            {"id": "source:123", "title": "T", "full_text": "body"}
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
        }

    @pytest.mark.asyncio
    async def test_truncates_insights_to_token_budget(self):
        """Insights are dropped (last first) when over the token budget."""
        big = "word " * 500
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
    async def test_keeps_source_when_it_alone_exceeds_budget(self):
        """A source whose full_text alone exceeds max_tokens is still
        returned (not dropped) — an empty context is worse than one over
        budget, and the prompt formatter caps full_text length downstream."""
        source = SimpleNamespace(id="source:123")
        big_text = "word " * 20000  # far bigger than the token budget below
        source.get_context = AsyncMock(
            return_value={"id": "source:123", "title": "T", "full_text": big_text}
        )
        source.get_insights = AsyncMock(return_value=[])

        with patch(
            "open_notebook.utils.context_builder.Source.get",
            new=AsyncMock(return_value=source),
        ):
            result = await build_source_context("source:123", max_tokens=600)

        assert len(result["sources"]) == 1
        assert result["sources"][0]["full_text"] == big_text
        assert result["total_tokens"] > 600

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
