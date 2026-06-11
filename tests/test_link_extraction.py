"""Unit tests for markdown link extraction."""

from open_notebook.utils.link_extraction import extract_links_from_markdown


class TestExtractLinksFromMarkdown:
    def test_extracts_absolute_links(self):
        md = "See [Example](https://other.com/page) and [Home](https://example.com/home)."
        links = extract_links_from_markdown(md, "https://example.com/article")
        urls = [link["url"] for link in links]
        assert "https://other.com/page" in urls
        assert "https://example.com/home" in urls

    def test_resolves_relative_links_against_base(self):
        md = "[Docs](/docs/intro)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        assert links[0]["url"] == "https://example.com/docs/intro"

    def test_tags_same_domain(self):
        md = "[Internal](/x) [External](https://other.com/y)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        by_url = {link["url"]: link["same_domain"] for link in links}
        assert by_url["https://example.com/x"] is True
        assert by_url["https://other.com/y"] is False

    def test_drops_mailto_tel_javascript_and_anchors(self):
        md = "[m](mailto:a@b.com) [t](tel:123) [j](javascript:void(0)) [a](#section)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        assert links == []

    def test_dedupes_repeated_urls(self):
        md = "[a](https://example.com/x) [b](https://example.com/x)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        assert len(links) == 1

    def test_drops_fragment_and_excludes_base_url_itself(self):
        md = "[self](https://example.com/article#top) [self2](https://example.com/article)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        assert links == []

    def test_empty_or_none_markdown_returns_empty(self):
        assert extract_links_from_markdown("", "https://example.com") == []
        assert extract_links_from_markdown(None, "https://example.com") == []

    def test_malformed_markdown_does_not_raise(self):
        md = "[broken](  ) [no-close](https://example.com/x"
        links = extract_links_from_markdown(md, "https://example.com/article")
        # The unclosed link is not matched; result is a list (no exception)
        assert isinstance(links, list)

    def test_keeps_link_text(self):
        md = "[Click here](https://other.com/z)"
        links = extract_links_from_markdown(md, "https://example.com/article")
        assert links[0]["text"] == "Click here"
