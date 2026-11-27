"""Mermaid -> PNG for the artifact pipeline.

pandoc has no Mermaid support: a ```mermaid``` fence is emitted as a plain code
block, never as a picture (verified against the pandoc 3.9 manual - no such
feature). The documented ecosystem answer is ``@mermaid-js/mermaid-cli`` (Node
+ Puppeteer), which is impractical here because the target host ships no
node/npm. The browserless alternative is the ``mermaidx`` wheel (QuickJS-ng +
resvg, no Node, no Chrome), measured at ~0.2 s per diagram.

This module:

    1. extracts every mermaid fence from the generated Markdown
    2. renders it to a 2x PNG (the safe raster for pptx: SVG rendering is bound
       to the Office reader)
    3. rewrites the fence as ``![](diagrams/fig-N.png)``, inserting a short
       lead-in line when the diagram would otherwise open its slide - text
       before non-text is what makes pandoc choose ``Content with Caption``

Everything is pure Python except the injected ``renderer``, so the logic is
unit-tested without the engine installed.
"""

import importlib
import importlib.metadata
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from loguru import logger

DEFAULT_LEAD_IN = "Summary diagram."
PNG_BACKGROUND = "#ffffff"
IMAGES_SUBDIR = "diagrams"

#: ``renderer(source, destination, scale)`` - injected so tests need no engine.
Renderer = Callable[[str, Path, float], None]

_BLOCK_RE = re.compile(
    r"^[ \t]*```[ \t]*(?:mermaid|\{[^}\n]*\.mermaid[^}\n]*\})[ \t]*\r?\n"
    r"(?P<code>.*?)^[ \t]*```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
_HEADING_RE = re.compile(r"^#{1,6}\s")


@dataclass
class DiagramBlock:
    """One ``mermaid`` fenced block found in the Markdown.

    Attributes:
        source: Diagram source (the fence body).
        start: Offset of the fence start in the document.
        end: Offset just after the fence end.
    """

    source: str
    start: int
    end: int


def extract_mermaid_blocks(markdown: str) -> list[DiagramBlock]:
    """Find every ```mermaid (or ```{.mermaid}) fence, in document order.

    Args:
        markdown: Document Markdown.

    Returns:
        The mermaid blocks with their offsets.
    """
    return [
        DiagramBlock(
            source=match.group("code").strip(), start=match.start(), end=match.end()
        )
        for match in _BLOCK_RE.finditer(markdown)
    ]


def make_renderer() -> tuple[Optional[Renderer], Optional[str]]:
    """Pick the first available browserless Mermaid engine.

    The import is lazy: the pipeline runs without the dependency until a
    diagram is actually needed.

    Returns:
        ``(renderer, label)``, or ``(None, None)`` when neither ``mermaidx``
        (current name) nor ``mmdc`` (old name, deprecated) is installed.
    """
    for name in ("mermaidx", "mmdc"):
        try:
            module = importlib.import_module(name)
        except ImportError:
            continue
        try:
            version = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            version = str(getattr(module, "__version__", "?"))

        def render(
            source: str, dest: Path, scale: float, _module: Any = module
        ) -> None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            diagram = _module.render(source)
            dest.write_bytes(diagram.png(scale=scale, background=PNG_BACKGROUND))

        return render, f"{name} {version}"
    logger.warning("No Mermaid engine installed (mermaidx/mmdc) - diagrams unavailable")
    return None, None


def _text_fence(source: str) -> str:
    """Keep the source readable as code when it cannot be drawn.

    Args:
        source: Diagram source.

    Returns:
        The source as a plain text fence.
    """
    return "```text\n" + source + "\n```"


def _opens_slide(before: str) -> bool:
    """True when the last non-blank line before the block is a heading.

    Args:
        before: Document text preceding the diagram.

    Returns:
        Whether the diagram would open a slide.
    """
    lines = [line for line in before.splitlines() if line.strip()]
    if not lines:
        return True
    return _HEADING_RE.match(lines[-1]) is not None


def _figure(rel_path: str, lead_in: str, before: str) -> str:
    """Image reference, with a lead-in line when the diagram opens a slide.

    Args:
        rel_path: Image path relative to the output directory.
        lead_in: Line to insert before the image.
        before: Document text preceding the diagram.

    Returns:
        The Markdown image reference.
    """
    if lead_in.strip() and _opens_slide(before):
        return f"{lead_in.strip()}\n\n![]({rel_path})"
    return f"![]({rel_path})"


def _rewrite(
    markdown: str,
    blocks: Sequence[DiagramBlock],
    replacement: Callable[[int, DiagramBlock], str],
) -> str:
    """Replace each block (original offsets) by ``replacement(index, block)``.

    Args:
        markdown: Document Markdown.
        blocks: Blocks to replace, in document order.
        replacement: Callable returning the replacement text.

    Returns:
        The rewritten document.
    """
    parts: list[str] = []
    cursor = 0
    for index, block in enumerate(blocks, start=1):
        parts.append(markdown[cursor : block.start])
        parts.append(replacement(index, block))
        cursor = block.end
    parts.append(markdown[cursor:])
    return "".join(parts)


def render_diagrams(
    markdown: str,
    out_dir: Path,
    renderer: Optional[Renderer],
    scale: float = 2.0,
    lead_in: str = DEFAULT_LEAD_IN,
    images_subdir: str = IMAGES_SUBDIR,
) -> tuple[str, dict[str, Any]]:
    """Render every mermaid fence to a PNG and rewrite the document.

    Never raises: a block that fails to render (or a missing engine) keeps its
    source as a plain text fence and is recorded in the report, so the document
    is always renderable by pandoc.

    Args:
        markdown: Document Markdown.
        out_dir: Directory the images are written under.
        renderer: Engine callable, or ``None`` when no engine is installed.
        scale: Raster scale passed to the engine (2x for pptx safety).
        lead_in: Line inserted when a diagram would open its slide.
        images_subdir: Subdirectory of ``out_dir`` holding the PNGs.

    Returns:
        ``(rewritten_markdown, report)`` where the report counts the blocks
        found/rendered and lists the images and the failures.
    """
    blocks = extract_mermaid_blocks(markdown)
    report: dict[str, Any] = {
        "blocks_found": len(blocks),
        "blocks_rendered": 0,
        "images": [],
        "failures": [],
    }
    if not blocks:
        return markdown, report

    if renderer is None:
        report["failures"] = [
            {"index": index, "error": "no renderer"}
            for index in range(1, len(blocks) + 1)
        ]
        logger.warning(f"{len(blocks)} mermaid block(s) kept as text: no engine")
        return _rewrite(
            markdown, blocks, lambda _i, block: _text_fence(block.source)
        ), report

    def replacement(index: int, block: DiagramBlock) -> str:
        rel_path = f"{images_subdir}/fig-{index}.png"
        dest = out_dir / images_subdir / f"fig-{index}.png"
        try:
            renderer(block.source, dest, scale)
        except Exception as exc:
            logger.warning(f"Mermaid block {index} failed: {exc}")
            report["failures"].append(
                {"index": index, "error": f"{type(exc).__name__}: {exc}"}
            )
            return _text_fence(block.source)
        report["blocks_rendered"] += 1
        report["images"].append(rel_path)
        logger.info(f"Diagram {index} -> {rel_path}")
        return _figure(rel_path, lead_in, markdown[: block.start])

    return _rewrite(markdown, blocks, replacement), report
