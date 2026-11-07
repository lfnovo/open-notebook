"""Single choke point for generated artifact file paths (#203 artifacts tab).

Mirrors ``open_notebook/podcasts/audio_paths.py`` for the artifacts root.
``GeneratedArtifact.output_path`` stores a path RELATIVE to
``ARTIFACTS_FOLDER`` (e.g. ``<uuid>/my-report-report.docx``). Two helpers
enforce that contract at the only two places paths cross the DB boundary:

- ``to_relative_artifact_path()`` - write side (the generation command):
  converts a generated file path to the relative storage form and refuses to
  produce a value outside the artifacts root, so the DB never holds an
  absolute or escaping path.
- ``resolve_contained_artifact_path()`` - read side (download, list, delete):
  joins the stored value with ``ARTIFACTS_FOLDER``, resolves symlinks/``..``
  and verifies containment. Any absolute or escaping value is treated as
  invalid and returns ``None``.

Storing relative paths makes path traversal unrepresentable for new rows and
lets previously generated artifacts survive a ``DATA_FOLDER`` move.
"""

import os
from pathlib import Path
from typing import Optional, Union

from open_notebook.config import ARTIFACTS_FOLDER


def artifacts_root() -> Path:
    """Real (symlink-resolved, absolute) path of the artifacts output root.

    Computed on every call rather than at import time so tests can
    monkeypatch ``ARTIFACTS_FOLDER`` on this module.

    Returns:
        The resolved artifacts root directory.
    """
    return Path(os.path.realpath(ARTIFACTS_FOLDER))


def to_relative_artifact_path(artifact_path: Union[str, Path]) -> str:
    """Convert a generated artifact file path to the DB storage form.

    Args:
        artifact_path: Absolute (or CWD-relative) path of a rendered file.

    Returns:
        The path relative to ``ARTIFACTS_FOLDER`` as a POSIX-style string.

    Raises:
        ValueError: If the path resolves outside the artifacts root - the DB
            must never hold an absolute or escaping value.
    """
    raw = str(artifact_path)
    resolved = Path(os.path.realpath(raw))
    root = artifacts_root()
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError(
            f"Generated artifact path is outside the artifacts folder: {artifact_path}"
        )
    return resolved.relative_to(root).as_posix()


def resolve_contained_artifact_path(output_path: Optional[str]) -> Optional[Path]:
    """Resolve a stored ``output_path`` value to a real filesystem path.

    Args:
        output_path: Value stored on ``GeneratedArtifact.output_path``.

    Returns:
        The contained absolute path, or ``None`` for anything that must not
        be followed: empty values, absolute paths, URIs and relative paths
        that escape the artifacts root (``..`` or symlink traversal).
    """
    if not output_path:
        return None
    if "://" in output_path:
        return None
    candidate = Path(output_path)
    if candidate.is_absolute():
        return None
    root = artifacts_root()
    resolved = Path(os.path.realpath(root / candidate))
    if resolved == root or not resolved.is_relative_to(root):
        return None
    return resolved
