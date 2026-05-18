from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mpeg", ".mpg"}
VIDEO_HOST_HINTS = ("youtube.com", "youtu.be", "vimeo.com", "bilibili.com")


def _has_video_extension(value: Optional[str]) -> bool:
    if not value:
        return False
    suffix = Path(urlparse(value).path).suffix.lower()
    return suffix in VIDEO_EXTENSIONS


def is_video_source(url: Optional[str] = None, file_path: Optional[str] = None) -> bool:
    if _has_video_extension(file_path) or _has_video_extension(url):
        return True
    if not url:
        return False
    hostname = (urlparse(url).hostname or "").lower()
    return any(_hostname_matches_hint(hostname, hint) for hint in VIDEO_HOST_HINTS)


def _hostname_matches_hint(hostname: str, hint: str) -> bool:
    return hostname == hint or hostname.endswith(f".{hint}")
