"""CORS helpers for the API.

The default CORS policy used while no password is set admits browser origins
on this machine plus origins on the same host the browser used to reach the
API. That keeps the default UI working from another machine on the LAN or a
VPS (the UI on port 8502 calls the API on port 5055 of the same host) while
other web pages the user visits can't read an unauthenticated API's answers.
"""

import re
from collections.abc import Sequence
from contextvars import ContextVar
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

# Browser origins on this machine: localhost, 127.0.0.1 or [::1], any port.
LOCALHOST_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"

# The Host header of the request being handled, for is_allowed_origin(),
# which Starlette calls without the request.
_request_host: ContextVar[str | None] = ContextVar("cors_request_host", default=None)


def origin_matches_host(origin: str | None, host: str | None) -> bool:
    """Whether an Origin names the same host the request was sent to.

    Compares host names only: the UI and the API sit on different ports of
    the same host, so the port and scheme don't have to match. Both headers
    are set by the browser, so a page on another site can't make them agree
    (short of DNS rebinding, which CORS doesn't cover either way).
    """
    if not origin or not host:
        return False
    try:
        origin_parts = urlsplit(origin)
        request_host = urlsplit(f"//{host}").hostname
    except ValueError:
        return False
    if origin_parts.scheme not in ("http", "https"):
        return False
    return origin_parts.hostname is not None and origin_parts.hostname == request_host


def is_allowed_by_default_policy(origin: str | None, host: str | None) -> bool:
    """The no-password default: localhost origins and same-host origins."""
    if not origin:
        return False
    if re.fullmatch(LOCALHOST_ORIGIN_REGEX, origin):
        return True
    return origin_matches_host(origin, host)


class SameHostCORSMiddleware(CORSMiddleware):
    """CORSMiddleware that can also admit origins on the request's own host."""

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: Sequence[str] = (),
        allow_methods: Sequence[str] = ("GET",),
        allow_headers: Sequence[str] = (),
        allow_credentials: bool = False,
        allow_origin_regex: str | None = None,
        allow_same_host: bool = False,
    ) -> None:
        super().__init__(
            app,
            allow_origins=allow_origins,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            allow_credentials=allow_credentials,
            allow_origin_regex=allow_origin_regex,
        )
        self.allow_same_host = allow_same_host

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.allow_same_host or scope["type"] != "http":
            await super().__call__(scope, receive, send)
            return
        token = _request_host.set(Headers(scope=scope).get("host"))
        try:
            await super().__call__(scope, receive, send)
        finally:
            _request_host.reset(token)

    def is_allowed_origin(self, origin: str) -> bool:
        if super().is_allowed_origin(origin):
            return True
        return self.allow_same_host and origin_matches_host(origin, _request_host.get())
