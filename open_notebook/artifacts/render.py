"""Markdown -> pptx/docx/html via pandoc, using the shipped reference deck.

Every pandoc call in the artifact pipeline goes through this module, so the
rendering dependency is one seam: replacing pandoc means replacing this file.

The reference deck (``assets/reference-deck.pptx``) is pandoc's own reference
restyled to a 16:9 canvas with the project palette; it is passed as
``--reference-doc`` only to the format it applies to, because a ``.pptx``
reference handed to the docx writer would break the output. Images referenced
by the document (the Mermaid PNGs) live next to the Markdown, hence
``--resource-path``.
"""

import importlib
import re
from pathlib import Path
from typing import Any, Optional, Sequence

from loguru import logger

SUPPORTED_FORMATS = ("md", "html", "docx", "pptx")
PANDOC_FORMATS = {"html": "html", "docx": "docx", "pptx": "pptx"}

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
REFERENCE_DECK_NAME = "reference-deck.pptx"


def reference_deck_path() -> Optional[Path]:
    """Locate the shipped pandoc reference deck.

    Returns:
        The reference deck path, or ``None`` when the asset is missing (the
        renderer then falls back to pandoc's default reference).
    """
    deck = ASSETS_DIR / REFERENCE_DECK_NAME
    if deck.is_file():
        return deck
    logger.warning(f"Reference deck not found at {deck} - using pandoc's default")
    return None


def slugify(text: str, max_len: int = 50) -> str:
    """Build a filesystem-safe slug.

    Args:
        text: Title or label to slugify.
        max_len: Maximum slug length.

    Returns:
        A lowercase, dash-separated slug (``artifact`` when nothing is left).
    """
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower()
    return (slug[:max_len] or "artifact").strip("-")


def build_base_name(title: str, kind: str) -> str:
    """Build the output file base name for one artifact.

    Args:
        title: Document title.
        kind: Artifact kind.

    Returns:
        ``<slug>-<kind>``, used for every requested format.
    """
    return f"{slugify(title or kind)}-{kind}"


def _pandoc_convert(
    source: str, to: str, outputfile: str, extra_args: Sequence[str]
) -> None:
    """Single ``pypandoc.convert_file`` call site.

    pypandoc is imported lazily (and dynamically) so this module stays
    importable when the binary is absent, and every render failure is caught
    by the caller instead of aborting the whole artifact.

    Args:
        source: Path of the Markdown file to convert.
        to: Pandoc output format.
        outputfile: Path of the file to write.
        extra_args: Extra pandoc arguments.
    """
    pypandoc: Any = importlib.import_module("pypandoc")
    pypandoc.convert_file(
        source, to, outputfile=outputfile, extra_args=list(extra_args)
    )


def render_artifact(
    markdown_text: str,
    out_dir: Path,
    base_name: str,
    formats: Sequence[str],
    reference_doc: Optional[Path] = None,
) -> dict[str, str]:
    """Write the requested formats under ``out_dir``.

    Markdown is always written: when it is not requested it is still needed as
    the pandoc input, so it is written as a hidden work file and removed once
    rendering is done.

    Args:
        markdown_text: Document Markdown to render.
        out_dir: Directory the outputs are written to.
        base_name: Base name shared by every output file.
        formats: Requested formats (``md``, ``html``, ``docx``, ``pptx``).
        reference_doc: Optional pandoc ``--reference-doc`` file; ``None`` uses
            the shipped reference deck.

    Returns:
        Mapping of the formats that were written to their absolute paths.
    """
    outputs: dict[str, str] = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    want_md = "md" in formats
    md_path = out_dir / f"{base_name}.md"
    work_path = md_path if want_md else out_dir / f".{base_name}.source.md"
    work_path.write_text(markdown_text, encoding="utf-8")
    if want_md:
        outputs["md"] = str(md_path)
        logger.info(f"Wrote {md_path}")

    deck = reference_doc if reference_doc is not None else reference_deck_path()
    reference = str(deck) if deck else ""
    for fmt in formats:
        if fmt == "md":
            continue
        if fmt not in PANDOC_FORMATS:
            logger.warning(f"Unsupported format {fmt!r} - skipped")
            continue
        target = out_dir / f"{base_name}.{fmt}"
        extra: list[str] = [f"--resource-path={out_dir}"]
        if fmt == "html":
            extra.append("--standalone")
        if reference and reference.endswith(f".{fmt}"):
            extra.append(f"--reference-doc={reference}")
        try:
            _pandoc_convert(str(work_path), PANDOC_FORMATS[fmt], str(target), extra)
            outputs[fmt] = str(target)
            logger.info(f"Rendered {target}")
        except Exception as exc:
            logger.error(f"Render failed for {fmt}: {exc}")
    if not want_md:
        work_path.unlink(missing_ok=True)
    return outputs
