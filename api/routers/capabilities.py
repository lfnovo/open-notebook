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

from fastapi import APIRouter

from api.models import CapabilitiesResponse

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


def _docling_available() -> bool:
    """True when Docling is installed (its document engine, OCR and image sources work)."""
    try:
        # content-core's own routing gate — the authoritative signal, not just a spec check.
        from content_core.extraction import DOCLING_AVAILABLE

        return bool(DOCLING_AVAILABLE)
    except Exception:
        return importlib.util.find_spec("docling") is not None


def _crawl4ai_remote_configured() -> bool:
    """True when a remote Crawl4AI server is configured (CRAWL4AI_API_URL)."""
    try:
        from content_core.config import get_crawl4ai_api_url

        return bool(get_crawl4ai_api_url())
    except Exception:
        import os

        return bool(os.environ.get("CRAWL4AI_API_URL"))


@router.get("", response_model=CapabilitiesResponse)
async def get_capabilities():
    """Report which opt-in extraction runtimes are available in this container."""
    crawl4ai_remote = _crawl4ai_remote_configured()
    crawl4ai_local = importlib.util.find_spec("crawl4ai") is not None
    return CapabilitiesResponse(
        docling_available=_docling_available(),
        crawl4ai_available=crawl4ai_local or crawl4ai_remote,
        crawl4ai_remote_configured=crawl4ai_remote,
    )
