"""
Unit tests for the open_notebook.utils module.

This test suite focuses on testing utility functions that perform actual logic
without heavy mocking - string processing, validation, and algorithms.
"""

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
from open_notebook.utils.context_builder import ContextBuilder, ContextConfig

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
        # Non-string input
        thinking, cleaned = parse_thinking_content(None)
        assert thinking == ""
        assert cleaned == ""

        # Integer input
        thinking, cleaned = parse_thinking_content(123)
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
# TEST SUITE 4: Context Builder Configuration
# ============================================================================


class TestContextBuilder:
    """Test suite for ContextBuilder initialization and configuration."""

    def test_context_config_defaults(self):
        """Test ContextConfig default values."""
        config = ContextConfig()

        assert config.sources == {}
        assert config.notes == {}
        assert config.include_insights is True
        assert config.include_notes is True
        assert config.priority_weights is not None
        assert "source" in config.priority_weights
        assert "note" in config.priority_weights
        assert "insight" in config.priority_weights

    def test_context_builder_initialization(self):
        """Test ContextBuilder initialization with various params."""
        builder = ContextBuilder(
            source_id="source:123",
            notebook_id="notebook:456",
            max_tokens=1000,
            include_insights=False,
        )

        assert builder.source_id == "source:123"
        assert builder.notebook_id == "notebook:456"
        assert builder.max_tokens == 1000
        assert builder.include_insights is False


# ============================================================================
# TEST SUITE 5: Video Utilities
# ============================================================================


class TestVideoUtilities:
    """Test suite for video processing utility functions."""

    def test_calculate_frame_params_short_video(self):
        """Test frame params for short videos (≤60s)."""
        from open_notebook.utils.video import calculate_frame_params

        # Boundary: exactly 60 seconds
        fps, max_frames = calculate_frame_params(60)
        assert fps == 1.0
        assert max_frames == 60

        # Under threshold
        fps, max_frames = calculate_frame_params(30)
        assert fps == 1.0
        assert max_frames == 60

    def test_calculate_frame_params_medium_video(self):
        """Test frame params for medium videos (61s-5min)."""
        from open_notebook.utils.video import calculate_frame_params

        # Just over 60s
        fps, max_frames = calculate_frame_params(61)
        assert fps == 0.5
        assert max_frames == 150

        # At 5 minute boundary
        fps, max_frames = calculate_frame_params(300)
        assert fps == 0.5
        assert max_frames == 150

    def test_calculate_frame_params_long_video(self):
        """Test frame params for long videos (5min-15min)."""
        from open_notebook.utils.video import calculate_frame_params

        # Just over 5 min
        fps, max_frames = calculate_frame_params(301)
        assert fps == 0.2
        assert max_frames == 180

        # At 15 minute boundary
        fps, max_frames = calculate_frame_params(900)
        assert fps == 0.2
        assert max_frames == 180

    def test_calculate_frame_params_very_long_video(self):
        """Test frame params for very long videos (>15min)."""
        from open_notebook.utils.video import calculate_frame_params

        # Just over 15 min
        fps, max_frames = calculate_frame_params(901)
        assert fps == 0.1
        assert max_frames == 180

        # Very long video (1 hour)
        fps, max_frames = calculate_frame_params(3600)
        assert fps == 0.1
        assert max_frames == 180


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
