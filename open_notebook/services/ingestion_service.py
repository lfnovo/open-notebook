"""
RAGAnything extraction wrapper for rich document parsing.

Handles PDF, DOCX, PPTX with structured table extraction.
Falls back to content-core when RAGAnything is not installed.
"""

from typing import Optional

from loguru import logger

RAGANYTHING_FILE_EXTENSIONS = {".pdf", ".docx", ".pptx"}


def _try_import_raganything():
    """
    Attempt to import RAGAnything at runtime.

    Returns the module on success, None on import failure.
    This allows the system to degrade gracefully when
    RAGAnything and its heavy dependencies (MinerU) are absent.
    """
    try:
        import raganything

        return raganything
    except ImportError:
        logger.warning(
            "RAGAnything is not installed. "
            "Rich document parsing for PDF/DOCX/PPTX will use content-core fallback. "
            "Install with: pip install raganything"
        )
        return None


def _is_raganything_file(file_path: str) -> bool:
    """Check whether the file extension is handled by RAGAnything."""
    from pathlib import Path

    suffix = Path(file_path).suffix.lower()
    return suffix in RAGANYTHING_FILE_EXTENSIONS


async def raganything_extract(file_path: str) -> Optional[str]:
    """
    Extract content from a document using RAGAnything.

    Returns extracted text (with structured tables) on success,
    or None when:
      - The file type is not supported by RAGAnything (txt, md, etc.)
      - RAGAnything is not installed

    The caller is expected to fall back to content-core when None is returned.
    """
    if not _is_raganything_file(file_path):
        return None

    rag_module = _try_import_raganything()
    if rag_module is None:
        return None

    try:
        logger.info(f"Processing {file_path} with RAGAnything")
        result = await rag_module.process_document(file_path)

        content = result.get("content") if isinstance(result, dict) else str(result)

        if not content or not content.strip():
            logger.warning(
                f"RAGAnything returned empty content for {file_path}, "
                "falling back to content-core"
            )
            return None

        logger.info(f"RAGAnything extracted {len(content)} characters from {file_path}")
        return content

    except Exception as error:
        logger.error(f"RAGAnything extraction failed for {file_path}: {error}")
        return None
