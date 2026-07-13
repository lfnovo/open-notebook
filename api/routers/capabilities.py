"""
Capabilities Router

Reports the runtime availability of the opt-in heavy extraction engines
(Docling, Crawl4AI local) so the frontend can gate the corresponding engine
options and the OCR toggle. These runtimes are installed on demand at container
startup (see scripts/docker-entrypoint.sh and
docs/7-DEVELOPMENT/decisions/ADR-007-optin-runtimes.md), so this endpoint probes
what is *actually* importable/reachable rather than trusting the enable flags.

Endpoints:
- GET /capabilities - Availability of Docling and Crawl4AI runtimes
"""

import importlib.util
import os

from fastapi import APIRouter
from loguru import logger

from api.models import CapabilitiesResponse

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


def _docling_available() -> bool:
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


def _crawl4ai_remote_configured() -> bool:
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


def _chromium_browser_present() -> bool:
    """True when a Playwright Chromium browser is installed on disk.

    Local Crawl4AI needs both the package AND a Chromium browser. The startup
    installer downloads them in separate steps and degrades gracefully, so the
    package can be present while the browser download failed — checking the
    browser here keeps this endpoint an honest "usable capability" signal.
    """
    base = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not base:
        # No managed browser path (non-Docker/dev): trust the package install
        # and let Playwright resolve its default browser location itself.
        return True
    try:
        return os.path.isdir(base) and any(
            "chromium" in name for name in os.listdir(base)
        )
    except OSError:
        return False


def _crawl4ai_local_ready() -> bool:
    """True when local Crawl4AI can actually render: package installed + Chromium present."""
    if importlib.util.find_spec("crawl4ai") is None:
        return False
    return _chromium_browser_present()


@router.get("", response_model=CapabilitiesResponse)
async def get_capabilities():
    """Report which opt-in extraction runtimes are available in this container."""
    crawl4ai_remote = _crawl4ai_remote_configured()
    crawl4ai_local = _crawl4ai_local_ready()
    return CapabilitiesResponse(
        docling_available=_docling_available(),
        crawl4ai_available=crawl4ai_local or crawl4ai_remote,
        crawl4ai_remote_configured=crawl4ai_remote,
    )
