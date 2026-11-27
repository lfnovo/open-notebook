"""Unit tests for the Mermaid -> PNG step.

The rendering engine is injected (and, for ``make_renderer``, faked through
``sys.modules``), so the suite never needs mermaidx, Node or a browser.
"""

import importlib.metadata
import sys
from types import SimpleNamespace

from open_notebook.artifacts import diagrams

ONE_BLOCK = "## Section\n\n```mermaid\ngraph TD; A-->B\n```\n"
TEXT_BEFORE_BLOCK = "Some text first.\n\n```mermaid\ngraph TD; A-->B\n```\n"


def _fake_renderer(record):
    """Renderer that records its calls and writes a fake PNG."""

    def render(source, dest, scale):
        record.append((source, dest.name, scale))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"png-bytes")

    return render


class TestExtractMermaidBlocks:
    def test_a_single_fence_is_found(self):
        blocks = diagrams.extract_mermaid_blocks(ONE_BLOCK)
        assert len(blocks) == 1
        assert blocks[0].source == "graph TD; A-->B"

    def test_the_attribute_form_is_found(self):
        markdown = "```{.mermaid caption='x'}\ngraph LR\n```\n"
        assert len(diagrams.extract_mermaid_blocks(markdown)) == 1

    def test_other_fences_are_ignored(self):
        markdown = "```python\nprint(1)\n```\n\n```text\nnot a diagram\n```\n"
        assert diagrams.extract_mermaid_blocks(markdown) == []

    def test_blocks_are_returned_in_document_order(self):
        markdown = "```mermaid\nfirst\n```\n\n```mermaid\nsecond\n```\n"
        sources = [b.source for b in diagrams.extract_mermaid_blocks(markdown)]
        assert sources == ["first", "second"]

    def test_offsets_point_at_the_fence(self):
        markdown = "intro\n\n```mermaid\ngraph TD\n```\n"
        block = diagrams.extract_mermaid_blocks(markdown)[0]
        assert markdown[block.start :].startswith("```mermaid")
        assert markdown[: block.start].endswith("intro\n\n")


class TestRenderDiagrams:
    def test_fence_is_replaced_by_the_rendered_image(self, tmp_path):
        record: list[tuple[str, str, float]] = []
        markdown, report = diagrams.render_diagrams(
            ONE_BLOCK, tmp_path, renderer=_fake_renderer(record)
        )
        assert report["blocks_found"] == 1
        assert report["blocks_rendered"] == 1
        assert report["images"] == ["diagrams/fig-1.png"]
        assert report["failures"] == []
        assert record == [("graph TD; A-->B", "fig-1.png", 2.0)]
        assert (tmp_path / "diagrams" / "fig-1.png").read_bytes() == b"png-bytes"
        assert markdown == (
            "## Section\n\nSummary diagram.\n\n![](diagrams/fig-1.png)\n"
        )

    def test_no_lead_in_when_the_diagram_does_not_open_the_slide(self, tmp_path):
        markdown, _ = diagrams.render_diagrams(
            TEXT_BEFORE_BLOCK, tmp_path, renderer=_fake_renderer([])
        )
        assert markdown == "Some text first.\n\n![](diagrams/fig-1.png)\n"

    def test_every_block_gets_its_own_image(self, tmp_path):
        markdown = "```mermaid\nfirst\n```\n\n```mermaid\nsecond\n```\n"
        rewritten, report = diagrams.render_diagrams(
            markdown, tmp_path, renderer=_fake_renderer([])
        )
        assert report["blocks_found"] == 2
        assert report["images"] == ["diagrams/fig-1.png", "diagrams/fig-2.png"]
        assert rewritten.count("![](diagrams/") == 2

    def test_a_failing_block_keeps_its_source_as_text(self, tmp_path):
        def failing(source, dest, scale):
            raise RuntimeError("engine crashed")

        markdown, report = diagrams.render_diagrams(
            ONE_BLOCK, tmp_path, renderer=failing
        )
        assert report["blocks_rendered"] == 0
        assert report["images"] == []
        assert report["failures"] == [
            {"index": 1, "error": "RuntimeError: engine crashed"}
        ]
        assert "```text\ngraph TD; A-->B\n```" in markdown

    def test_without_an_engine_blocks_are_demoted_to_text(self, tmp_path):
        markdown, report = diagrams.render_diagrams(ONE_BLOCK, tmp_path, renderer=None)
        assert report["blocks_found"] == 1
        assert report["blocks_rendered"] == 0
        assert report["failures"] == [{"index": 1, "error": "no renderer"}]
        assert markdown == "## Section\n\n```text\ngraph TD; A-->B\n```\n"

    def test_document_without_diagrams_is_untouched(self, tmp_path):
        markdown, report = diagrams.render_diagrams(
            "# Title\n\nplain body\n", tmp_path, renderer=_fake_renderer([])
        )
        assert markdown == "# Title\n\nplain body\n"
        assert report["blocks_found"] == 0

    def test_scale_and_subdirectory_are_configurable(self, tmp_path):
        record: list[tuple[str, str, float]] = []
        markdown, report = diagrams.render_diagrams(
            ONE_BLOCK,
            tmp_path,
            renderer=_fake_renderer(record),
            scale=3.0,
            images_subdir="figs",
        )
        assert record[0][2] == 3.0
        assert report["images"] == ["figs/fig-1.png"]
        assert "![](figs/fig-1.png)" in markdown


class TestMakeRenderer:
    def test_mermaidx_is_used_when_available(self, monkeypatch, tmp_path):
        sources = []
        png_calls = []

        class _FakeDiagram:
            def png(self, scale=2.0, background="#ffffff"):
                png_calls.append((scale, background))
                return b"real-png"

        class _FakeMermaidx:
            __version__ = "9.9.9"

            def render(self, source):
                sources.append(source)
                return _FakeDiagram()

        monkeypatch.setitem(sys.modules, "mermaidx", _FakeMermaidx())

        renderer, label = diagrams.make_renderer()
        assert renderer is not None
        assert label is not None and label.startswith("mermaidx ")
        renderer("graph TD", tmp_path / "diagrams" / "fig-1.png", 2.0)
        assert sources == ["graph TD"]
        assert png_calls == [(2.0, diagrams.PNG_BACKGROUND)]
        assert (tmp_path / "diagrams" / "fig-1.png").read_bytes() == b"real-png"

    def test_no_engine_installed_returns_none(self, monkeypatch):
        def raising(name):
            raise ImportError(name)

        monkeypatch.setattr(
            diagrams,
            "importlib",
            SimpleNamespace(import_module=raising, metadata=importlib.metadata),
        )
        assert diagrams.make_renderer() == (None, None)
