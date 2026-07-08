"""
Internal subscription gateway.

Exposes an OpenAI-compatible surface (``/v1/chat/completions``, ``/v1/models``,
``/v1/embeddings``) scoped to a single subscription credential. Esperanto's
``openai_compatible`` provider talks to this as if it were a normal provider,
with ``base_url`` pointing here. The gateway:

  1. resolves the credential id from the path,
  2. gets a valid OAuth access token (refreshing if near expiry),
  3. translates the OpenAI request into the upstream subscription API
     (Anthropic Messages for ``claude``; ChatGPT backend Responses for
     ``chatgpt``) and translates the (possibly streamed) response back.

All the fragile, ToS-gray subscription logic is isolated here so the rest of
the app — ModelManager, Esperanto, the domain — needs no changes. See
``open_notebook/ai/subscription_tokens.py`` for the experimental/ToS caveat.

The loopback call from Esperanto is authenticated by the normal password
middleware (the credential injects the app password as its ``api_key``); this
router additionally requires the path credential to actually be an OAuth
subscription credential.
"""

from __future__ import annotations

from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

from api import subscription_gateway_translate as tr
from open_notebook.ai.subscription_tokens import get_valid_access_token
from open_notebook.domain.credential import Credential

router = APIRouter(prefix="/subscription-gateway")

# Curated, editable model lists surfaced via /v1/models so Esperanto discovery
# and model registration work. Users can also register any model name manually.
CURATED_MODELS = {
    "claude": [
        "claude-opus-4-8",
        "claude-opus-4-20250514",
        "claude-sonnet-4-20250514",
        "claude-3-5-haiku-20241022",
    ],
    "chatgpt": [
        "gpt-5.5",
        "gpt-5.4",
        "gpt-5.4-mini",
    ],
}

UPSTREAM_TIMEOUT = httpx.Timeout(600.0, connect=30.0)


async def _load_subscription_credential(credential_id: str) -> Credential:
    try:
        cred = await Credential.get(credential_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Credential not found: {e}")
    if cred.auth_type != "oauth_subscription":
        raise HTTPException(
            status_code=400,
            detail="Credential is not an OAuth subscription credential",
        )
    return cred


@router.get("/{credential_id}/v1/models")
async def list_models(credential_id: str):
    """Return a curated OpenAI-style model list for this subscription."""
    cred = await _load_subscription_credential(credential_id)
    models = CURATED_MODELS.get(cred.subscription_kind, [])
    return {
        "object": "list",
        "data": [{"id": m, "object": "model", "owned_by": cred.subscription_kind} for m in models],
    }


@router.post("/{credential_id}/v1/embeddings")
async def embeddings(credential_id: str):
    """Subscriptions do not grant embeddings access."""
    raise HTTPException(
        status_code=501,
        detail=(
            "Embeddings are not available through a subscription credential. "
            "Configure a normal API-key credential for embedding models."
        ),
    )


@router.post("/{credential_id}/v1/chat/completions")
async def chat_completions(credential_id: str, request: Request):
    """Translate an OpenAI chat-completions request to the subscription's
    upstream API and stream/return the result in OpenAI shape."""
    cred = await _load_subscription_credential(credential_id)
    body: Dict[str, Any] = await request.json()
    model = body.get("model", "")
    stream = bool(body.get("stream", False))

    access_token = await get_valid_access_token(cred)

    # The ChatGPT backend Responses API only accepts streaming requests, so we
    # always stream upstream for chatgpt and aggregate when the caller wants a
    # single (non-streaming) response.
    upstream_stream_only = cred.subscription_kind == "chatgpt"

    if cred.subscription_kind == "claude":
        url = "https://api.anthropic.com/v1/messages"
        upstream_body = tr.openai_to_anthropic(body)
        headers = tr.anthropic_headers(access_token)
        sse_translate = tr.anthropic_sse_to_openai
        json_translate = tr.anthropic_to_openai
    elif cred.subscription_kind == "chatgpt":
        url = tr.CHATGPT_RESPONSES_URL
        upstream_body = tr.openai_to_responses(body)
        upstream_body["stream"] = True
        headers = tr.chatgpt_headers(access_token, cred.account_id)
        sse_translate = tr.responses_sse_to_openai
        json_translate = tr.responses_to_openai
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported subscription kind: {cred.subscription_kind}",
        )

    if stream:
        return StreamingResponse(
            _stream_upstream(url, upstream_body, headers, sse_translate, model, cred),
            media_type="text/event-stream",
        )

    if upstream_stream_only:
        # Aggregate the upstream SSE into a single OpenAI chat completion.
        return JSONResponse(
            content=await _aggregate_stream(url, upstream_body, headers, sse_translate, model, cred)
        )

    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
        resp = await client.post(url, json=upstream_body, headers=headers)
        if resp.status_code >= 400:
            logger.warning(
                f"Subscription upstream error {resp.status_code} for "
                f"{cred.subscription_kind}: {resp.text[:500]}"
            )
            return JSONResponse(
                status_code=resp.status_code,
                content={"error": {"message": resp.text, "type": "upstream_error"}},
            )
        return JSONResponse(content=json_translate(resp.json(), model))


async def _aggregate_stream(url, upstream_body, headers, sse_translate, model, cred):
    """Consume an upstream SSE stream and assemble a single OpenAI chat
    completion dict (used for providers that only support streaming)."""
    content_parts: list[str] = []
    finish_reason = "stop"
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
        async with client.stream("POST", url, json=upstream_body, headers=headers) as resp:
            if resp.status_code >= 400:
                text = (await resp.aread()).decode("utf-8", "replace")
                logger.warning(
                    f"Subscription upstream error {resp.status_code} for "
                    f"{cred.subscription_kind}: {text[:500]}"
                )
                return {"error": {"message": text, "type": "upstream_error"}}
            async for event_type, data in _aiter_sse(resp):
                if event_type == "done":
                    break
                chunk = sse_translate(event_type, data, model)
                if chunk is None:
                    continue
                delta = chunk["choices"][0]["delta"]
                if delta.get("content"):
                    content_parts.append(delta["content"])
                if chunk["choices"][0].get("finish_reason"):
                    finish_reason = chunk["choices"][0]["finish_reason"]
    return {
        "id": "chatcmpl-subscription",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "".join(content_parts)},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


async def _stream_upstream(url, upstream_body, headers, sse_translate, model, cred):
    """Async generator yielding OpenAI-shaped SSE bytes from an upstream stream."""
    import json as _json

    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
        async with client.stream("POST", url, json=upstream_body, headers=headers) as resp:
            if resp.status_code >= 400:
                text = (await resp.aread()).decode("utf-8", "replace")
                logger.warning(
                    f"Subscription upstream stream error {resp.status_code} for "
                    f"{cred.subscription_kind}: {text[:500]}"
                )
                err = _json.dumps(
                    {"error": {"message": text, "type": "upstream_error"}}
                )
                yield f"data: {err}\n\n".encode()
                yield b"data: [DONE]\n\n"
                return

            async for event_type, data in _aiter_sse(resp):
                if event_type == "done":
                    break
                chunk = sse_translate(event_type, data, model)
                if chunk is not None:
                    yield f"data: {_json.dumps(chunk)}\n\n".encode()
    yield b"data: [DONE]\n\n"


async def _aiter_sse(resp: httpx.Response):
    """Async adaptation of translate.iter_sse_events over an httpx stream."""
    event_type = None
    import json as _json

    async for raw in resp.aiter_lines():
        line = raw.rstrip("\n")
        if not line:
            event_type = None
            continue
        if line.startswith("event:"):
            event_type = line[len("event:") :].strip()
        elif line.startswith("data:"):
            payload = line[len("data:") :].strip()
            if payload == "[DONE]":
                yield ("done", {})
                continue
            try:
                data = _json.loads(payload)
            except ValueError:
                continue
            etype = event_type or (data.get("type") if isinstance(data, dict) else None)
            yield (etype or "", data)
