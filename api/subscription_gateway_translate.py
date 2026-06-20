"""
Pure request/response translation for the subscription gateway.

The gateway accepts OpenAI-style ``/chat/completions`` requests (that is what
Esperanto's ``openai_compatible`` provider speaks) and must translate them to
the upstream API the subscription actually exposes:

  * ``claude``  -> Anthropic Messages API (``/v1/messages``)
  * ``chatgpt`` -> ChatGPT backend Responses API (Codex)

and translate the responses (including streamed SSE events) back into the
OpenAI chat-completions shape that Esperanto parses.

Everything here is pure and synchronous so it can be unit-tested without HTTP.
The HTTP plumbing, auth, and token refresh live in
``api/routers/subscription_gateway.py``.

Scope (v1): text content, system prompt, multi-turn, streaming, and basic
tool calls. Images / audio / structured-output fidelity are intentionally
deferred and documented as known gaps.

The ChatGPT/Responses translation is reverse-engineered from the Codex CLI and
is the most fragile part of this module — see the subscription_tokens module
docstring for the experimental/ToS caveat.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

ANTHROPIC_VERSION = "2023-06-01"
ANTHROPIC_OAUTH_BETA = "oauth-2025-04-20"
DEFAULT_MAX_TOKENS = 4096

# Anthropic stop_reason -> OpenAI finish_reason
_ANTHROPIC_FINISH = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "max_tokens": "length",
    "tool_use": "tool_calls",
}


def _openai_chat_completion(
    *,
    content: str,
    model: str,
    finish_reason: str = "stop",
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    usage: Optional[Dict[str, int]] = None,
    response_id: str = "chatcmpl-subscription",
    created: int = 0,
) -> Dict[str, Any]:
    """Build a minimal OpenAI chat-completion response dict."""
    message: Dict[str, Any] = {"role": "assistant", "content": content or ""}
    if tool_calls:
        message["tool_calls"] = tool_calls
        message["content"] = content or None
    return {
        "id": response_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": usage
        or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _openai_chunk(
    *,
    model: str,
    delta: Dict[str, Any],
    finish_reason: Optional[str] = None,
    response_id: str = "chatcmpl-subscription",
    created: int = 0,
) -> Dict[str, Any]:
    """Build a single OpenAI streaming chunk dict."""
    return {
        "id": response_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {"index": 0, "delta": delta, "finish_reason": finish_reason}
        ],
    }


# ---------------------------------------------------------------------------
# Anthropic (claude) translation
# ---------------------------------------------------------------------------


def openai_to_anthropic(body: Dict[str, Any]) -> Dict[str, Any]:
    """Translate an OpenAI chat-completions request into an Anthropic Messages
    request body."""
    system_parts: List[str] = []
    messages: List[Dict[str, Any]] = []

    for msg in body.get("messages", []):
        role = msg.get("role")
        content = msg.get("content")
        if role == "system":
            if isinstance(content, str):
                system_parts.append(content)
            elif isinstance(content, list):
                system_parts.extend(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict)
                )
            continue
        if role == "tool":
            # OpenAI tool result -> Anthropic tool_result block on a user message
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_call_id", ""),
                            "content": content if isinstance(content, str) else json.dumps(content),
                        }
                    ],
                }
            )
            continue
        if role == "assistant" and msg.get("tool_calls"):
            blocks: List[Dict[str, Any]] = []
            if isinstance(content, str) and content:
                blocks.append({"type": "text", "text": content})
            for tc in msg["tool_calls"]:
                fn = tc.get("function", {})
                try:
                    args = json.loads(fn.get("arguments", "{}") or "{}")
                except json.JSONDecodeError:
                    args = {}
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": fn.get("name", ""),
                        "input": args,
                    }
                )
            messages.append({"role": "assistant", "content": blocks})
            continue

        # Plain user/assistant text (string or OpenAI content-part list).
        if isinstance(content, list):
            text = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") in (None, "text")
            )
        else:
            text = content or ""
        messages.append({"role": role or "user", "content": text})

    out: Dict[str, Any] = {
        "model": body.get("model", ""),
        "messages": messages,
        "max_tokens": body.get("max_tokens") or DEFAULT_MAX_TOKENS,
        "stream": bool(body.get("stream", False)),
    }
    if system_parts:
        out["system"] = "\n\n".join(system_parts)
    if body.get("temperature") is not None:
        out["temperature"] = body["temperature"]
    if body.get("top_p") is not None:
        out["top_p"] = body["top_p"]
    if body.get("tools"):
        out["tools"] = [
            {
                "name": t["function"]["name"],
                "description": t["function"].get("description", ""),
                "input_schema": t["function"].get("parameters", {"type": "object"}),
            }
            for t in body["tools"]
            if t.get("type") == "function" and t.get("function")
        ]
    return out


def anthropic_to_openai(resp: Dict[str, Any], model: str) -> Dict[str, Any]:
    """Translate a non-streaming Anthropic Messages response into an OpenAI
    chat-completion response."""
    text_parts: List[str] = []
    tool_calls: List[Dict[str, Any]] = []
    for block in resp.get("content", []):
        if block.get("type") == "text":
            text_parts.append(block.get("text", ""))
        elif block.get("type") == "tool_use":
            tool_calls.append(
                {
                    "id": block.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": json.dumps(block.get("input", {})),
                    },
                }
            )
    usage_in = resp.get("usage", {}) or {}
    prompt = int(usage_in.get("input_tokens", 0) or 0)
    completion = int(usage_in.get("output_tokens", 0) or 0)
    return _openai_chat_completion(
        content="".join(text_parts),
        model=resp.get("model", model),
        finish_reason=_ANTHROPIC_FINISH.get(resp.get("stop_reason"), "stop"),
        tool_calls=tool_calls or None,
        usage={
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
        },
        response_id=resp.get("id", "chatcmpl-subscription"),
    )


def anthropic_sse_to_openai(
    event_type: str, data: Dict[str, Any], model: str
) -> Optional[Dict[str, Any]]:
    """Translate a single Anthropic SSE event into an OpenAI streaming chunk
    dict, or None if the event carries nothing for the client.

    The gateway drives this per event; it is responsible for emitting the final
    ``[DONE]`` sentinel itself.
    """
    if event_type == "message_start":
        return _openai_chunk(model=model, delta={"role": "assistant"})
    if event_type == "content_block_delta":
        delta = data.get("delta", {})
        if delta.get("type") == "text_delta":
            return _openai_chunk(model=model, delta={"content": delta.get("text", "")})
        if delta.get("type") == "input_json_delta":
            # Partial tool-call arguments.
            return _openai_chunk(
                model=model,
                delta={
                    "tool_calls": [
                        {
                            "index": data.get("index", 0),
                            "function": {"arguments": delta.get("partial_json", "")},
                        }
                    ]
                },
            )
        return None
    if event_type == "content_block_start":
        block = data.get("content_block", {})
        if block.get("type") == "tool_use":
            return _openai_chunk(
                model=model,
                delta={
                    "tool_calls": [
                        {
                            "index": data.get("index", 0),
                            "id": block.get("id", ""),
                            "type": "function",
                            "function": {"name": block.get("name", ""), "arguments": ""},
                        }
                    ]
                },
            )
        return None
    if event_type == "message_delta":
        stop_reason = data.get("delta", {}).get("stop_reason")
        if stop_reason:
            return _openai_chunk(
                model=model,
                delta={},
                finish_reason=_ANTHROPIC_FINISH.get(stop_reason, "stop"),
            )
        return None
    return None


def anthropic_headers(access_token: str) -> Dict[str, str]:
    """Headers for an Anthropic OAuth (subscription) Messages call.

    Critically uses Bearer auth + the oauth beta header and does NOT send
    ``x-api-key`` — that combination is what distinguishes subscription auth
    from API-key auth.
    """
    return {
        "authorization": f"Bearer {access_token}",
        "anthropic-version": ANTHROPIC_VERSION,
        "anthropic-beta": ANTHROPIC_OAUTH_BETA,
        "content-type": "application/json",
    }


# ---------------------------------------------------------------------------
# ChatGPT backend Responses API (chatgpt / Codex) translation
# ---------------------------------------------------------------------------

CHATGPT_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"


def openai_to_responses(body: Dict[str, Any]) -> Dict[str, Any]:
    """Translate an OpenAI chat-completions request into a ChatGPT backend
    Responses API request.

    The Responses API takes top-level ``instructions`` (system) plus an
    ``input`` list of typed message items. This v1 maps text content only.
    """
    instructions: List[str] = []
    input_items: List[Dict[str, Any]] = []
    for msg in body.get("messages", []):
        role = msg.get("role")
        content = msg.get("content")
        text = (
            content
            if isinstance(content, str)
            else "".join(
                part.get("text", "")
                for part in (content or [])
                if isinstance(part, dict)
            )
        )
        if role == "system":
            instructions.append(text)
            continue
        # Responses input content types are role-relative.
        content_type = "output_text" if role == "assistant" else "input_text"
        input_items.append(
            {
                "type": "message",
                "role": role or "user",
                "content": [{"type": content_type, "text": text}],
            }
        )

    out: Dict[str, Any] = {
        "model": body.get("model", ""),
        "input": input_items,
        "stream": bool(body.get("stream", False)),
        # Codex sends store=false for stateless calls.
        "store": False,
        # The ChatGPT backend Responses API requires a non-empty `instructions`
        # field. Use the request's system message(s) when present, otherwise a
        # minimal default so the call is accepted.
        "instructions": "\n\n".join(instructions)
        if instructions
        else "You are a helpful assistant.",
    }
    if body.get("temperature") is not None:
        out["temperature"] = body["temperature"]
    if body.get("top_p") is not None:
        out["top_p"] = body["top_p"]
    return out


def _responses_extract_text(resp: Dict[str, Any]) -> str:
    """Pull assistant text out of a Responses API result object."""
    # Convenience aggregate, when present.
    if isinstance(resp.get("output_text"), str):
        return resp["output_text"]
    parts: List[str] = []
    for item in resp.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") in ("output_text", "text"):
                    parts.append(c.get("text", ""))
    return "".join(parts)


def responses_to_openai(resp: Dict[str, Any], model: str) -> Dict[str, Any]:
    """Translate a non-streaming Responses API result into an OpenAI
    chat-completion response."""
    usage_in = resp.get("usage", {}) or {}
    prompt = int(usage_in.get("input_tokens", 0) or 0)
    completion = int(usage_in.get("output_tokens", 0) or 0)
    return _openai_chat_completion(
        content=_responses_extract_text(resp),
        model=resp.get("model", model),
        finish_reason="stop",
        usage={
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion or (prompt + completion),
        },
        response_id=resp.get("id", "chatcmpl-subscription"),
    )


def responses_sse_to_openai(
    event_type: str, data: Dict[str, Any], model: str
) -> Optional[Dict[str, Any]]:
    """Translate a single Responses API SSE event into an OpenAI streaming
    chunk dict, or None. The gateway emits the final ``[DONE]`` itself."""
    if event_type == "response.output_text.delta":
        return _openai_chunk(model=model, delta={"content": data.get("delta", "")})
    if event_type == "response.completed":
        return _openai_chunk(model=model, delta={}, finish_reason="stop")
    return None


def chatgpt_headers(access_token: str, account_id: Optional[str]) -> Dict[str, str]:
    """Headers for a ChatGPT backend Responses (Codex) call."""
    headers = {
        "authorization": f"Bearer {access_token}",
        "content-type": "application/json",
        "openai-beta": "responses=experimental",
        "originator": "codex_cli_rs",
    }
    if account_id:
        headers["chatgpt-account-id"] = account_id
    return headers


# ---------------------------------------------------------------------------
# Shared SSE line parsing
# ---------------------------------------------------------------------------


def iter_sse_events(lines: Iterable[str]):
    """Yield (event_type, data_dict) tuples from raw SSE text lines.

    Handles the ``event:`` / ``data:`` line pairs used by both Anthropic and
    the Responses API. ``[DONE]`` data is yielded as ("done", {}).
    """
    event_type: Optional[str] = None
    for raw in lines:
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
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            # Anthropic puts the type inside the JSON too; prefer the event line.
            etype = event_type or (data.get("type") if isinstance(data, dict) else None)
            yield (etype or "", data)
