import os

from loguru import logger
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Matches the file-size guidance already documented in
# docs/3-USER-GUIDE/adding-sources.md ("Very large files (>100MB) - Timeout").
DEFAULT_MAX_UPLOAD_SIZE_MB = 100


def get_max_upload_size_bytes() -> int:
    """Read the configured max request body size, in bytes.

    Configurable via OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB for deployments that
    need larger audio/video uploads; falls back to the default on unset,
    malformed, or non-positive values (a zero/negative limit would reject
    every request that has a body).
    """
    raw = os.environ.get("OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB", "").strip()
    try:
        mb = float(raw) if raw else DEFAULT_MAX_UPLOAD_SIZE_MB
    except ValueError:
        mb = DEFAULT_MAX_UPLOAD_SIZE_MB
    if mb <= 0:
        logger.warning(
            f"OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB={raw!r} is not a positive size; "
            f"using the default of {DEFAULT_MAX_UPLOAD_SIZE_MB}MB"
        )
        mb = DEFAULT_MAX_UPLOAD_SIZE_MB
    return int(mb * 1024 * 1024)


class _RequestBodyTooLarge(Exception):
    pass


class MaxBodySizeMiddleware:
    """
    Raw ASGI middleware rejecting requests whose body exceeds a configured
    maximum, so a large upload can't exhaust memory/disk on a deployment
    with no fronting proxy enforcing its own limit (e.g. the shipped
    docker-compose.yml, which exposes the API directly).

    Implemented at the raw ASGI level (not BaseHTTPMiddleware) so the check
    can run ahead of FastAPI's own body/form parsing instead of after it.
    Rejects on the `Content-Length` header up front when present (the common
    case, and cheap), and also counts bytes as the body streams in - a
    client can lie about Content-Length or omit it entirely with chunked
    transfer-encoding.
    """

    def __init__(self, app: ASGIApp, max_body_size: int) -> None:
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        content_length = headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_body_size:
                    logger.warning(
                        f"Rejected {scope.get('method', '?')} {scope.get('path', '?')}: "
                        f"declared body of {content_length} bytes exceeds the "
                        f"{self.max_body_size}-byte limit"
                    )
                    await _send_413(send)
                    return
            except ValueError:
                pass  # malformed header - fall through to streaming enforcement

        total_size = 0
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        async def receive_wrapper() -> Message:
            nonlocal total_size
            message = await receive()
            if message["type"] == "http.request":
                total_size += len(message.get("body") or b"")
                if total_size > self.max_body_size:
                    raise _RequestBodyTooLarge()
            return message

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except _RequestBodyTooLarge:
            logger.warning(
                f"Rejected {scope.get('method', '?')} {scope.get('path', '?')}: "
                f"streamed body exceeded the {self.max_body_size}-byte limit"
            )
            if not response_started:
                await _send_413(send)
            # Else the app already started responding - nothing safe to send;
            # let the connection drop rather than violate the ASGI protocol
            # with a second response.start.


async def _send_413(send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b'{"detail":"Request body exceeds the maximum allowed upload size"}',
        }
    )
