"""Files dropped onto a notebook's notes pane: validation, storage, text extraction.

The original is stored under ``NOTE_FILES_FOLDER`` as ``<uuid><ext>`` (the
user's file name is kept only in the database, never used as a path).
"""

import asyncio
import os
import re
import uuid
from pathlib import Path
from typing import Tuple

from content_core import ContentCoreConfig, extract_content
from loguru import logger

from open_notebook.config import NOTE_FILES_FOLDER
from open_notebook.exceptions import InvalidInputError, UnsupportedTypeException

# Extension -> MIME type. The MIME type served back is always taken from here,
# never from the upload, so a crafted file cannot choose how it is rendered.
ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".html": "text/html",
    ".htm": "text/html",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}

_STORED_NAME = re.compile(r"^[0-9a-f]{32}\.[a-z]{2,8}$")


def classify_upload(filename: str, head: bytes) -> Tuple[str, str]:
    """Return ``(extension, mime)`` for an upload, or raise.

    Checks the extension against the allow-list and sanity-checks the first
    bytes so e.g. an executable renamed to ``.pdf`` is rejected.
    """
    ext = Path(filename or "").suffix.lower()
    mime = ALLOWED_TYPES.get(ext)
    if mime is None:
        raise UnsupportedTypeException(
            "Unsupported file type. Use PDF, HTML, DOCX, TXT or Markdown."
        )
    if ext == ".pdf" and b"%PDF" not in head[:1024]:
        raise InvalidInputError("This file is not a valid PDF")
    if ext == ".docx" and not head.startswith(b"PK\x03\x04"):
        raise InvalidInputError("This file is not a valid DOCX document")
    if ext not in (".pdf", ".docx") and b"\x00" in head[:8192]:
        raise InvalidInputError("This file does not look like a text document")
    return ext, mime


def write_note_file(content: bytes, ext: str) -> str:
    """Store the bytes and return the stored file name."""
    stored = f"{uuid.uuid4().hex}{ext}"
    Path(NOTE_FILES_FOLDER, stored).write_bytes(content)
    return stored


def note_file_path(stored: str) -> Path:
    """Resolve a stored file name to a path inside the note files folder."""
    if not _STORED_NAME.match(stored or ""):
        raise InvalidInputError("Invalid stored file name")
    root = Path(NOTE_FILES_FOLDER).resolve()
    path = (root / stored).resolve()
    if not str(path).startswith(str(root) + os.sep):
        raise InvalidInputError("Invalid stored file name")
    return path


def remove_note_file(stored: str) -> None:
    """Best-effort removal; a missing file or bad name is only logged."""
    try:
        note_file_path(stored).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Failed to remove note file {stored}: {e}")


async def extract_note_text(path: Path) -> str:
    """Extract readable text (markdown where possible) from a stored file."""
    try:
        result = await extract_content(file_path=str(path), config=ContentCoreConfig())
    except Exception as e:
        logger.warning(f"Text extraction failed for {path.name}: {e}")
        raise InvalidInputError(
            "Could not read this file. It may be corrupted or password protected."
        ) from e
    return (result.content or "").strip()


async def store_note_file(content: bytes, ext: str) -> str:
    """Write the bytes off the event loop and return the stored name."""
    return await asyncio.to_thread(write_note_file, content, ext)
