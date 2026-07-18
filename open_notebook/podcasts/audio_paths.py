"""Single choke point for podcast episode audio file paths (#1030).

``PodcastEpisode.audio_file`` stores a path RELATIVE to ``PODCASTS_FOLDER``
(e.g. ``episodes/<uuid>/audio/<uuid>.mp3``). Two helpers enforce that
contract at the only two places paths cross the DB boundary:

- ``to_relative_audio_path()`` — write side (podcast generation command):
  converts the generated file path to the relative storage form and refuses
  to produce a value outside the podcasts root, so the DB never holds an
  absolute or escaping path.
- ``resolve_contained_audio_path()`` — read side (every API consumption
  point: stream, list/get, delete, retry): joins the stored value with
  ``PODCASTS_FOLDER``, resolves symlinks/``..`` and verifies containment.
  Any absolute, ``file://`` or escaping value is treated as legacy-invalid
  and returns ``None`` (callers keep today's 403/404 behavior from #1018).

Storing relative paths makes path traversal unrepresentable for new rows
and lets previously generated episodes survive a ``DATA_FOLDER`` move.
Migration 21 converts pre-existing rows written under the known roots.
"""

import os
from pathlib import Path
from typing import Optional, Union
from urllib.parse import unquote, urlparse

from open_notebook.config import PODCASTS_FOLDER


def podcasts_root() -> Path:
    """Real (symlink-resolved, absolute) path of the podcasts output root.

    Computed on every call rather than at import time so tests can
    monkeypatch ``PODCASTS_FOLDER`` on this module.
    """
    return Path(os.path.realpath(PODCASTS_FOLDER))


def to_relative_audio_path(audio_path: Union[str, Path]) -> str:
    """Convert a generated audio file path to the DB storage form.

    Accepts the absolute (or CWD-relative) path produced by podcast-creator,
    including the legacy ``file://`` URI form, and returns it relative to
    ``PODCASTS_FOLDER`` as a POSIX-style string.

    Raises:
        ValueError: if the path resolves outside the podcasts root — the DB
            must never hold an absolute or escaping value. ValueError also
            marks the generation job as permanently failed (no retry).
    """
    raw = str(audio_path)
    if raw.startswith("file://"):
        raw = unquote(urlparse(raw).path)
    resolved = Path(os.path.realpath(raw))
    root = podcasts_root()
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError(
            f"Generated audio file path is outside the podcasts folder: {audio_path}"
        )
    return resolved.relative_to(root).as_posix()


def resolve_contained_audio_path(audio_file: Optional[str]) -> Optional[Path]:
    """Resolve a stored ``audio_file`` value to a real filesystem path.

    Joins the stored relative path with ``PODCASTS_FOLDER``, resolves
    symlinks and ``..`` components, and verifies the result stays inside the
    podcasts root.

    Returns ``None`` for anything that must not be followed:
    - empty/None values
    - absolute paths and ``file://`` URIs (legacy rows migration 21 could
      not convert — exactly the out-of-root cases #1018's guards reject)
    - relative paths that escape the root (``..`` or symlink traversal)
    """
    if not audio_file:
        return None
    if "://" in audio_file:
        return None
    candidate = Path(audio_file)
    if candidate.is_absolute():
        return None
    root = podcasts_root()
    resolved = Path(os.path.realpath(root / candidate))
    if resolved == root or not resolved.is_relative_to(root):
        return None
    return resolved
