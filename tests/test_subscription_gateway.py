"""Gateway-level tests with a mocked upstream (no real provider calls).

Verifies the gateway routes an OpenAI chat-completions request to the correct
upstream, sends subscription-correct headers (Bearer + anthropic-beta, no
x-api-key for Claude), and translates the response back to OpenAI shape —
all without touching a real subscription account.
"""

import json
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

import api.routers.subscription_gateway as gw
from api import subscription_gateway_translate as tr


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class _FakeClient:
    """Records the last POST and returns a canned response."""

    last = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeClient.last = {"url": url, "json": json, "headers": headers}
        # Canned Anthropic Messages response.
        return _FakeResponse(
            200,
            {
                "id": "msg_x",
                "model": "claude-sonnet-4-20250514",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "pong"}],
                "usage": {"input_tokens": 5, "output_tokens": 1},
            },
        )


@pytest.fixture
def client(monkeypatch):
    # Avoid real DB / token refresh: stub credential load + token.
    class _Cred:
        id = "credential:test"
        auth_type = "oauth_subscription"
        subscription_kind = "claude"
        account_id = None

    async def _load(_id):
        return _Cred()

    async def _token(_cred):
        return "oauth-access-token"

    monkeypatch.setattr(gw, "_load_subscription_credential", _load)
    monkeypatch.setattr(gw, "get_valid_access_token", _token)
    monkeypatch.setattr(gw.httpx, "AsyncClient", _FakeClient)

    from api.main import app

    return TestClient(app)


def test_claude_chat_completion_translates_and_sets_oauth_headers(client):
    resp = client.post(
        "/api/subscription-gateway/credential:test/v1/chat/completions",
        json={
            "model": "claude-sonnet-4-20250514",
            "messages": [
                {"role": "system", "content": "Be brief."},
                {"role": "user", "content": "ping"},
            ],
            "stream": False,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # Translated to OpenAI chat-completion shape.
    assert body["choices"][0]["message"]["content"] == "pong"
    assert body["choices"][0]["finish_reason"] == "stop"

    sent = _FakeClient.last
    assert sent["url"] == "https://api.anthropic.com/v1/messages"
    # Subscription-correct headers.
    assert sent["headers"]["authorization"] == "Bearer oauth-access-token"
    assert sent["headers"]["anthropic-beta"] == "oauth-2025-04-20"
    assert "x-api-key" not in sent["headers"]
    # Claude Code identity is injected first (required for OAuth subscription),
    # then the caller's system prompt; user message preserved.
    assert sent["json"]["system"] == [
        {"type": "text", "text": tr.CLAUDE_CODE_IDENTITY},
        {"type": "text", "text": "Be brief."},
    ]
    assert sent["json"]["messages"] == [{"role": "user", "content": "ping"}]


def test_embeddings_returns_501(client):
    resp = client.post(
        "/api/subscription-gateway/credential:test/v1/embeddings",
        json={"input": "x"},
    )
    assert resp.status_code == 501
