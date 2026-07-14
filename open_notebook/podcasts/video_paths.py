"""Contain and resolve storyboard-video files under ``PODCASTS_FOLDER/videos``.

New video jobs and the six pre-v1.13 local artifacts use a mix of paths rooted
at ``data/podcasts/videos`` and ``notebook_data/podcasts/videos``. This helper
maps those known legacy forms to the active data volume while refusing file
URIs, unrelated absolute paths, traversal, and symlink escapes.
"""

import os
from pathlib import Path
from typing import Optional

from open_notebook.podcasts.audio_paths import podcasts_root

_LEGACY_VIDEO_MARKERS = (
    ("data", "podcasts", "videos"),
    ("notebook_data", "podcasts", "videos"),
)


def videos_root() -> Path:
    """Return the real, active storyboard-video root."""
    return Path(os.path.realpath(podcasts_root() / "videos"))


def _existing_legacy_video_roots() -> tuple[Path, ...]:
    """Return legacy roots that physically exist in this runtime."""
    candidates = (
        Path("data/podcasts/videos"),
        Path("notebook_data/podcasts/videos"),
        Path("/app/data/podcasts/videos"),
        Path("/data/podcasts/videos"),
    )
    roots = []
    for candidate in candidates:
        resolved = Path(os.path.realpath(candidate))
        if resolved.exists() and resolved not in roots:
            roots.append(resolved)
    return tuple(roots)


def _legacy_suffix(path: Path) -> Optional[tuple[str, ...]]:
    parts = path.parts
    if parts and parts[0] == "videos":
        return tuple(parts[1:])

    for marker in _LEGACY_VIDEO_MARKERS:
        width = len(marker)
        for index in range(len(parts) - width + 1):
            if tuple(parts[index : index + width]) == marker:
                return tuple(parts[index + width :])
    return None


def resolve_contained_video_path(stored_path: Optional[str]) -> Optional[Path]:
    """Resolve current and known legacy video paths without escaping the root."""
    if not stored_path or "://" in stored_path:
        return None

    raw = Path(stored_path)
    root = videos_root()

    direct = Path(os.path.realpath(raw))
    for allowed_root in (root, *_existing_legacy_video_roots()):
        if direct != allowed_root and direct.is_relative_to(allowed_root):
            return direct

    suffix = _legacy_suffix(raw)
    if not suffix:
        return None

    mapped = Path(os.path.realpath(root.joinpath(*suffix)))
    if mapped == root or not mapped.is_relative_to(root):
        return None
    return mapped
