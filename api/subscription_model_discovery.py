"""Discover the models exposed by OAuth subscription providers.

The official subscription clients own these catalogs. Open Notebook reads the
same live sources instead of maintaining a second, inevitably stale model list.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

import httpx
from loguru import logger

from api import subscription_gateway_translate as tr
from open_notebook.ai.subscription_tokens import get_valid_access_token

CHATGPT_MODELS_URL = "https://chatgpt.com/backend-api/codex/models"
CLAUDE_MODEL_CATALOG_URL = (
    "https://downloads.claude.ai/model-catalog/v1/catalog.json"
)
DISCOVERY_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# Used only when a provider is temporarily unavailable after a successful
# discovery in this process. There is deliberately no bundled/static fallback.
_last_successful_models: dict[str, list[dict[str, str]]] = {}


def _client_version() -> str:
    try:
        return version("open-notebook")
    except PackageNotFoundError:
        return "0.0.0"


def _parse_chatgpt_models(payload: dict[str, Any]) -> list[dict[str, str]]:
    rows = payload.get("models")
    if not isinstance(rows, list):
        raise ValueError("ChatGPT model catalog did not contain a models list")

    discovered: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("visibility") != "list":
            continue
        model_id = row.get("slug")
        if not isinstance(model_id, str) or not model_id or model_id in seen:
            continue
        seen.add(model_id)
        display_name = row.get("display_name")
        summary = row.get("description")
        description = " — ".join(
            value
            for value in (display_name, summary)
            if isinstance(value, str) and value and value != model_id
        )
        model = {"name": model_id}
        if description:
            model["description"] = description
        discovered.append(model)

    if not discovered:
        raise ValueError("ChatGPT model catalog contained no picker-visible models")
    return discovered


def _parse_claude_models(payload: dict[str, Any]) -> list[dict[str, str]]:
    surfaces = payload.get("surfaces")
    cc = surfaces.get("cc") if isinstance(surfaces, dict) else None
    configs = cc.get("model_selector_config") if isinstance(cc, dict) else None
    if not isinstance(configs, list):
        raise ValueError("Claude Code model catalog did not contain selector config")

    config = next(
        (
            candidate
            for candidate in configs
            if isinstance(candidate, dict) and candidate.get("id") == "cc"
        ),
        None,
    )
    rows = config.get("models") if isinstance(config, dict) else None
    if not isinstance(rows, list):
        raise ValueError("Claude Code selector config did not contain a models list")

    discovered: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        offered_on = row.get("offered_on")
        if not isinstance(offered_on, list) or "first_party" not in offered_on:
            continue
        model_id = row.get("id")
        if not isinstance(model_id, str) or not model_id or model_id in seen:
            continue
        seen.add(model_id)
        display_name = row.get("name")
        summary = row.get("description")
        description = " — ".join(
            value
            for value in (display_name, summary)
            if isinstance(value, str) and value and value != model_id
        )
        model = {"name": model_id}
        if description:
            model["description"] = description
        discovered.append(model)

    if not discovered:
        raise ValueError("Claude Code catalog contained no first-party models")
    return discovered


async def _discover_chatgpt_models(credential) -> list[dict[str, str]]:
    access_token = await get_valid_access_token(credential)
    headers = tr.chatgpt_headers(access_token, credential.account_id)
    headers["user-agent"] = f"open-notebook/{_client_version()}"
    async with httpx.AsyncClient(timeout=DISCOVERY_TIMEOUT) as client:
        response = await client.get(
            CHATGPT_MODELS_URL,
            params={"client_version": _client_version()},
            headers=headers,
        )
        response.raise_for_status()
        return _parse_chatgpt_models(response.json())


async def _discover_claude_models() -> list[dict[str, str]]:
    async with httpx.AsyncClient(timeout=DISCOVERY_TIMEOUT) as client:
        response = await client.get(
            CLAUDE_MODEL_CATALOG_URL,
            headers={"user-agent": f"open-notebook/{_client_version()}"},
        )
        response.raise_for_status()
        return _parse_claude_models(response.json())


async def discover_subscription_models(credential) -> list[dict[str, str]]:
    """Return the current picker models for one subscription credential."""
    kind = credential.subscription_kind
    cache_key = f"{kind}:{credential.id}"
    try:
        if kind == "chatgpt":
            models = await _discover_chatgpt_models(credential)
        elif kind == "claude":
            models = await _discover_claude_models()
        else:
            raise ValueError(f"Unsupported subscription kind: {kind}")
    except Exception:
        cached = _last_successful_models.get(cache_key)
        if cached:
            logger.warning(
                f"Subscription model refresh failed for {kind}; using the last "
                "successful catalog from this process"
            )
            return cached
        raise

    _last_successful_models[cache_key] = models
    return models
