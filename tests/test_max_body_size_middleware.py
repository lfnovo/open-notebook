"""
Tests for api.middleware.MaxBodySizeMiddleware.

Covers the raw-ASGI unit behavior (Content-Length pre-check, streaming
enforcement for chunked/no-Content-Length requests, CORS interaction) plus
integration through a real FastAPI app and the actual registered app.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

from api.middleware import (
    DEFAULT_MAX_UPLOAD_SIZE_MB,
    MaxBodySizeMiddleware,
    get_max_upload_size_bytes,
)


async def _echo_body_app(scope, receive, send):
    """Minimal ASGI app that reads the full body then returns 200."""
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send(
        {"type": "http.response.body", "body": f"received {len(body)} bytes".encode()}
    )


def make_scope(headers=None, method="POST", path="/upload"):
    raw_headers = [
        (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
    ]
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": raw_headers,
    }


class FakeReceiveStream:
    """Feeds a list of body chunks as successive http.request ASGI messages."""

    def __init__(self, chunks):
        self._chunks = list(chunks)

    async def __call__(self):
        if not self._chunks:
            return {"type": "http.request", "body": b"", "more_body": False}
        chunk = self._chunks.pop(0)
        return {
            "type": "http.request",
            "body": chunk,
            "more_body": bool(self._chunks),
        }


class CollectingSend:
    def __init__(self):
        self.messages = []

    async def __call__(self, message):
        self.messages.append(message)

    @property
    def status(self):
        for m in self.messages:
            if m["type"] == "http.response.start":
                return m["status"]
        return None

    @property
    def body(self):
        return b"".join(
            m.get("body", b"")
            for m in self.messages
            if m["type"] == "http.response.body"
        )

    def header(self, name: bytes):
        for m in self.messages:
            if m["type"] == "http.response.start":
                for k, v in m["headers"]:
                    if k.lower() == name.lower():
                        return v.decode()
        return None


class TestConfig:
    def test_default_is_100mb(self, monkeypatch):
        monkeypatch.delenv("OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB", raising=False)
        assert DEFAULT_MAX_UPLOAD_SIZE_MB == 100
        assert get_max_upload_size_bytes() == 100 * 1024 * 1024

    def test_reads_env_override(self, monkeypatch):
        monkeypatch.setenv("OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB", "5")
        assert get_max_upload_size_bytes() == 5 * 1024 * 1024

    def test_malformed_env_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB", "not-a-number")
        assert get_max_upload_size_bytes() == 100 * 1024 * 1024

    def test_non_positive_env_falls_back_to_default(self, monkeypatch):
        # A zero/negative limit would 413 every request that has a body.
        monkeypatch.setenv("OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB", "0")
        assert get_max_upload_size_bytes() == 100 * 1024 * 1024
        monkeypatch.setenv("OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB", "-5")
        assert get_max_upload_size_bytes() == 100 * 1024 * 1024


class TestMiddlewareAsgiLevel:
    @pytest.mark.asyncio
    async def test_content_length_precheck_rejects_before_app_runs(self):
        app_called = False

        async def inner_app(scope, receive, send):
            nonlocal app_called
            app_called = True
            await _echo_body_app(scope, receive, send)

        middleware = MaxBodySizeMiddleware(inner_app, max_body_size=10)
        scope = make_scope(headers={"content-length": "1000"})
        send = CollectingSend()
        await middleware(scope, FakeReceiveStream([b"x" * 1000]), send)

        assert not app_called, "inner app must not run when Content-Length exceeds the limit"
        assert send.status == 413

    @pytest.mark.asyncio
    async def test_small_body_passes_through(self):
        middleware = MaxBodySizeMiddleware(_echo_body_app, max_body_size=1000)
        scope = make_scope(headers={"content-length": "5"})
        send = CollectingSend()
        await middleware(scope, FakeReceiveStream([b"hello"]), send)

        assert send.status == 200
        assert send.body == b"received 5 bytes"

    @pytest.mark.asyncio
    async def test_streaming_body_without_content_length_is_still_enforced(self):
        """A client can omit Content-Length (chunked transfer-encoding) - the
        middleware must still catch an oversized body as it streams in."""
        middleware = MaxBodySizeMiddleware(_echo_body_app, max_body_size=10)
        scope = make_scope(headers={})  # no content-length
        send = CollectingSend()
        chunks = [b"a" * 5, b"b" * 5, b"c" * 5]  # totals 15 > 10
        await middleware(scope, FakeReceiveStream(chunks), send)

        assert send.status == 413

    @pytest.mark.asyncio
    async def test_malformed_content_length_falls_back_to_streaming_check(self):
        middleware = MaxBodySizeMiddleware(_echo_body_app, max_body_size=10)
        scope = make_scope(headers={"content-length": "not-a-number"})
        send = CollectingSend()
        await middleware(scope, FakeReceiveStream([b"x" * 1000]), send)

        assert send.status == 413  # caught by streaming enforcement instead

    @pytest.mark.asyncio
    async def test_non_http_scope_passes_through_untouched(self):
        calls = []

        async def inner_app(scope, receive, send):
            calls.append(scope["type"])

        middleware = MaxBodySizeMiddleware(inner_app, max_body_size=10)
        await middleware({"type": "lifespan"}, FakeReceiveStream([]), CollectingSend())
        assert calls == ["lifespan"]

    @pytest.mark.asyncio
    async def test_exactly_at_limit_passes(self):
        middleware = MaxBodySizeMiddleware(_echo_body_app, max_body_size=10)
        scope = make_scope(headers={"content-length": "10"})
        send = CollectingSend()
        await middleware(scope, FakeReceiveStream([b"x" * 10]), send)
        assert send.status == 200

    @pytest.mark.asyncio
    async def test_one_byte_over_limit_rejected(self):
        middleware = MaxBodySizeMiddleware(_echo_body_app, max_body_size=10)
        scope = make_scope(headers={"content-length": "11"})
        send = CollectingSend()
        await middleware(scope, FakeReceiveStream([b"x" * 11]), send)
        assert send.status == 413


class TestCorsInteraction:
    @pytest.mark.asyncio
    async def test_cors_headers_present_on_413_when_wrapped_by_cors_middleware(self):
        """MaxBodySizeMiddleware must sit *inside* CORSMiddleware so a
        rejected upload still gets CORS headers (mirrors the ordering used
        in api/main.py)."""
        app = CORSMiddleware(
            MaxBodySizeMiddleware(_echo_body_app, max_body_size=10),
            allow_origins=["http://example.com"],
            allow_credentials=True,
        )
        scope = make_scope(
            headers={"content-length": "1000", "origin": "http://example.com"}
        )
        send = CollectingSend()
        await app(scope, FakeReceiveStream([b"x" * 1000]), send)

        assert send.status == 413
        assert send.header(b"access-control-allow-origin") == "http://example.com"


class TestFastApiIntegration:
    """Drives the middleware through a real FastAPI app + TestClient (real
    HTTP-shaped requests via httpx), not just hand-rolled ASGI messages."""

    @pytest.fixture
    def small_limit_app(self):
        app = FastAPI()

        @app.post("/echo")
        async def echo():
            return {"ok": True}

        app.add_middleware(MaxBodySizeMiddleware, max_body_size=100)
        return app

    def test_small_request_passes(self, small_limit_app):
        client = TestClient(small_limit_app)
        response = client.post("/echo", content=b"x" * 50)
        assert response.status_code == 200

    def test_oversized_request_rejected_with_413(self, small_limit_app):
        client = TestClient(small_limit_app)
        response = client.post("/echo", content=b"x" * 1000)
        assert response.status_code == 413
        assert "exceeds the maximum" in response.json()["detail"]


class TestRealAppWiring:
    def test_real_app_registers_middleware_with_configured_size(self):
        from api.main import MAX_UPLOAD_SIZE_BYTES, app

        matches = [m for m in app.user_middleware if m.cls is MaxBodySizeMiddleware]
        assert len(matches) == 1
        assert matches[0].kwargs["max_body_size"] == MAX_UPLOAD_SIZE_BYTES

    def test_real_app_wraps_it_inside_cors(self):
        """CORS must be outermost so it can attach headers to a 413 from
        MaxBodySizeMiddleware - i.e. CORSMiddleware must be added *after* it."""
        from api.main import app

        # getattr: Middleware.cls is typed as a callable protocol without
        # __name__, but every registered middleware here is a plain class.
        classes = [getattr(m.cls, "__name__", "") for m in app.user_middleware]
        assert classes.index("CORSMiddleware") < classes.index("MaxBodySizeMiddleware")
