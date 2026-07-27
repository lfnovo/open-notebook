"""
Runtime availability probes for the opt-in heavy extraction engines.

Docling and local Crawl4AI are installed on demand at container startup (see
scripts/docker-entrypoint.sh and
docs/7-DEVELOPMENT/decisions/ADR-007-optin-runtimes.md), so availability is a
*runtime* property: it cannot be read off the enable flags, and it does not
survive a redeploy that drops them.

This lives in open_notebook.utils (not api/) because both layers need it: the
capabilities router reports it to the frontend, and the source-processing graph
must not hand content-core an engine whose runtime is absent — the engine
choice is persisted in the database and therefore outlives the environment that
made it available.
"""

import importlib.util
import os
import sys

from loguru import logger


def docling_available() -> bool:
    """True when Docling is installed (its document engine, OCR and image sources work)."""
    try:
        # content-core's own routing gate — the authoritative signal, not just a spec check.
        from content_core.extraction import DOCLING_AVAILABLE

        return bool(DOCLING_AVAILABLE)
    except (ImportError, AttributeError):
        # Content-core absent or its API moved — fall back to a plain spec check.
        return importlib.util.find_spec("docling") is not None
    except Exception:
        # An unexpected failure shouldn't be silently masked as "unavailable".
        logger.opt(exception=True).warning(
            "Unexpected error probing Docling availability; reporting unavailable"
        )
        return False


def crawl4ai_remote_configured() -> bool:
    """True when a remote Crawl4AI server is configured (CRAWL4AI_API_URL)."""
    try:
        from content_core.config import get_crawl4ai_api_url

        return bool(get_crawl4ai_api_url())
    except (ImportError, AttributeError):
        return bool(os.environ.get("CRAWL4AI_API_URL"))
    except Exception:
        logger.opt(exception=True).warning(
            "Unexpected error probing Crawl4AI remote config; falling back to env var"
        )
        return bool(os.environ.get("CRAWL4AI_API_URL"))


def _default_playwright_cache() -> str | None:
    """Playwright's default browser download directory when PLAYWRIGHT_BROWSERS_PATH is unset."""
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Caches/ms-playwright")
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        return os.path.join(local, "ms-playwright") if local else None
    return os.path.expanduser("~/.cache/ms-playwright")  # linux and others


def _chromium_browser_present() -> bool:
    """True when a Playwright Chromium browser is installed on disk.

    Local Crawl4AI needs both the package AND a Chromium browser. The startup
    installer downloads them in separate steps and degrades gracefully, so the
    package can be present while the browser download failed — checking the
    browser here keeps this an honest "usable capability" signal.

    Playwright installs browsers into PLAYWRIGHT_BROWSERS_PATH (Docker) or, when
    that's unset, its per-user default cache (dev). Resolving the path does not
    download anything, so we must confirm a chromium build actually exists in
    whichever directory applies before reporting local Crawl4AI available.
    """
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or _default_playwright_cache()
    if not base or not os.path.isdir(base):
        return False
    try:
        return any("chromium" in name for name in os.listdir(base))
    except OSError:
        return False


def crawl4ai_local_ready() -> bool:
    """True when local Crawl4AI can actually render: package installed + Chromium present."""
    if importlib.util.find_spec("crawl4ai") is None:
        return False
    return _chromium_browser_present()


def crawl4ai_available() -> bool:
    """True when Crawl4AI can run at all — locally installed or offloaded to a server."""
    return crawl4ai_local_ready() or crawl4ai_remote_configured()


# Engine name -> (availability probe, env var that enables it). Engines absent
# from this map need no runtime and are always usable.
_ENGINE_RUNTIMES: dict[str, tuple[str, str]] = {
    "crawl4ai": ("crawl4ai_available", "OPEN_NOTEBOOK_ENABLE_CRAWL4AI"),
    "docling": ("docling_available", "OPEN_NOTEBOOK_ENABLE_DOCLING"),
}


def engine_runtime_missing(engine: str | None) -> str | None:
    """Return the env var that would enable ``engine``, or None if it is usable.

    Used to avoid passing content-core an engine whose runtime is absent, which
    fails extraction outright with no indication of the real cause.
    """
    if not engine:
        return None
    entry = _ENGINE_RUNTIMES.get(engine.strip().lower())
    if entry is None:
        return None  # Engine needs no opt-in runtime (auto/simple/firecrawl/jina).
    probe_name, env_var = entry
    probe = globals()[probe_name]
    return None if probe() else env_var
