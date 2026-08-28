"""Pricing lookup for LLM usage-cost tracking.

OpenRouter's `/api/v1/models` catalog (already used for model discovery in
open_notebook/ai/model_discovery.py) is the only pricing source this
codebase has: it publishes `pricing.prompt` / `pricing.completion` in USD
per token for every model it proxies. No other provider registered here
exposes machine-readable per-token pricing, so lookups for any other
provider - or any failure fetching/parsing the catalog - fall back to
(0.0, 0.0). Pricing is a best-effort enrichment for usage tracking; it must
never raise or block an LLM call.
"""

import time
from typing import Any, Dict, Tuple

import httpx
from loguru import logger

from open_notebook.ai.provider_registry import PROVIDERS

# Refresh at most every few minutes - a simple module-level cache is enough
# here; this isn't hit on a hot path (once per LLM call at most) and doesn't
# need a DB-backed cache or background refresh job.
_CACHE_TTL_SECONDS = 300

_price_cache: Dict[str, Tuple[float, float]] = {}
_cache_loaded_at: float = 0.0


def _parse_price(value: Any) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


async def _refresh_openrouter_pricing() -> None:
    global _price_cache, _cache_loaded_at

    url = PROVIDERS["openrouter"].openai_compat_discovery_url
    if not url:
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        logger.warning(f"Failed to refresh OpenRouter pricing cache: {e}")
        # Keep serving the previous (possibly empty) cache rather than
        # hammering the API again on the very next call.
        _cache_loaded_at = time.monotonic()
        return

    new_cache: Dict[str, Tuple[float, float]] = {}
    for model in data.get("data", []):
        model_id = model.get("id")
        if not model_id:
            continue
        pricing = model.get("pricing") or {}
        new_cache[model_id.lower()] = (
            _parse_price(pricing.get("prompt")),
            _parse_price(pricing.get("completion")),
        )

    _price_cache = new_cache
    _cache_loaded_at = time.monotonic()


async def get_price_per_token(provider: str, model_name: str) -> Tuple[float, float]:
    """Return (input_price, output_price) in USD per token for a model.

    Defaults to (0.0, 0.0) - never raises - for free models, non-OpenRouter
    providers, or any network/parsing failure.
    """
    if not provider or not model_name or provider.lower() != "openrouter":
        return (0.0, 0.0)

    try:
        if not _price_cache or (time.monotonic() - _cache_loaded_at) > _CACHE_TTL_SECONDS:
            await _refresh_openrouter_pricing()
        return _price_cache.get(model_name.lower(), (0.0, 0.0))
    except Exception as e:
        logger.warning(f"Pricing lookup failed for {provider}/{model_name}: {e}")
        return (0.0, 0.0)
