"""Tests for password authentication (api/auth.py and api/routers/auth.py).

A minimal standalone FastAPI app is built per-test so the production app (and its
database wiring) is never imported. The password is injected by patching
`get_secret_from_env` where each module imports it -- note that
`PasswordAuthMiddleware` reads the password once in ``__init__`` (so the patch
must be active while the app is built) whereas ``check_api_password`` and
``GET /auth/status`` read it at call time.
"""

import asyncio
import hmac
import json
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from api.auth import PasswordAuthMiddleware, check_api_password

PASSWORD = "s3cret-p@ss"
UNICODE_PASSWORD = "pässwörd-中文"


def _build_app(password, excluded_paths=None):
    """Build a standalone app with the middleware mounted.

    Starlette instantiates middleware lazily when the middleware stack is built,
    so the patch must still be active at ``build_middleware_stack()`` time -- that
    is when ``PasswordAuthMiddleware.__init__`` reads the password (once).
    """
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"ok": "root"}

    @app.get("/health")
    async def health():
        return {"ok": "health"}

    @app.get("/api/protected")
    async def protected():
        return {"ok": "protected"}

    @app.options("/api/protected")
    async def protected_options():
        return {"ok": "preflight"}

    @app.post("/api/protected")
    async def protected_post():
        return {"ok": "protected"}

    @app.put("/api/protected")
    async def protected_put():
        return {"ok": "protected"}

    @app.delete("/api/protected")
    async def protected_delete():
        return {"ok": "protected"}

    with patch("api.auth.get_secret_from_env", return_value=password):
        app.add_middleware(PasswordAuthMiddleware, excluded_paths=excluded_paths)
        app.middleware_stack = app.build_middleware_stack()

    return app


def _client(password, excluded_paths=None):
    return TestClient(_build_app(password, excluded_paths))


def _raw_asgi_get(app, path, auth_header_bytes=None):
    """Drive the app over raw ASGI so the exact header BYTES can be controlled.

    httpx (used by TestClient) encodes header values as ASCII and raises
    ``UnicodeEncodeError`` for anything else, so a non-ASCII credential cannot be
    sent through ``TestClient`` at all; driving raw ASGI is the only way to express
    the latin-1 wire bytes Starlette decodes. Returns (status_code, body).
    """
    headers = [(b"host", b"testserver")]
    if auth_header_bytes is not None:
        headers.append((b"authorization", auth_header_bytes))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "root_path": "",
        "query_string": b"",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app(scope, receive, send))

    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    )
    return status, body.decode("utf-8")


@pytest.fixture
def client():
    """Client for an app with a password configured."""
    return _client(PASSWORD)


class TestPasswordAuthMiddleware:
    """Middleware behaviour when a password IS configured."""

    def test_correct_password_allows_request(self, client):
        response = client.get(
            "/api/protected", headers={"Authorization": f"Bearer {PASSWORD}"}
        )
        assert response.status_code == 200
        assert response.json() == {"ok": "protected"}

    def test_wrong_password_rejected(self, client):
        response = client.get(
            "/api/protected", headers={"Authorization": "Bearer wrong-password"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid password"
        assert response.headers["WWW-Authenticate"] == "Bearer"

    def test_password_prefix_is_rejected(self, client):
        """A truncated password must not be accepted."""
        response = client.get(
            "/api/protected", headers={"Authorization": f"Bearer {PASSWORD[:-1]}"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid password"

    def test_missing_authorization_header_rejected(self, client):
        response = client.get("/api/protected")
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing authorization header"
        assert response.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.parametrize(
        "header",
        [
            "Basic xyz",
            f"Basic {PASSWORD}",
            PASSWORD,  # bare token, no scheme / no space
            "Bearer",  # scheme only, no space-separated credentials
            f"Token {PASSWORD}",
        ],
    )
    def test_malformed_authorization_header_rejected(self, client, header):
        response = client.get("/api/protected", headers={"Authorization": header})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authorization header format"
        assert response.headers["WWW-Authenticate"] == "Bearer"

    def test_empty_authorization_header_counts_as_missing(self, client):
        """``""`` is falsy, so it takes the missing branch, not the malformed one."""
        response = client.get("/api/protected", headers={"Authorization": ""})
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing authorization header"
        assert response.headers["WWW-Authenticate"] == "Bearer"

    @pytest.mark.parametrize(
        "header",
        [
            "Bearer ",  # scheme + space, empty credentials
            f"Bearer  {PASSWORD}",  # double space -> credentials start with a space
            f"Bearer {PASSWORD} ",  # trailing space is part of the credentials
        ],
    )
    def test_bearer_with_degenerate_credentials_is_invalid_password(
        self, client, header
    ):
        """The split succeeds here, so these reach the compare -- not the format error."""
        response = client.get("/api/protected", headers={"Authorization": header})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid password"

    def test_bearer_scheme_is_case_insensitive(self, client):
        response = client.get(
            "/api/protected", headers={"Authorization": f"bearer {PASSWORD}"}
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "path", ["/", "/health", "/docs", "/openapi.json", "/redoc"]
    )
    def test_default_excluded_paths_need_no_header(self, client, path):
        response = client.get(path)
        assert response.status_code == 200

    def test_options_preflight_needs_no_header(self, client):
        response = client.options("/api/protected")
        assert response.status_code == 200
        assert response.json() == {"ok": "preflight"}

    def test_custom_excluded_paths_replace_defaults(self):
        custom = _client(PASSWORD, excluded_paths=["/health"])
        assert custom.get("/health").status_code == 200
        assert custom.get("/").status_code == 401

    def test_empty_excluded_paths_falls_back_to_defaults(self):
        """``excluded_paths or [...]`` truthiness: ``[]`` is NOT 'exclude nothing'."""
        custom = _client(PASSWORD, excluded_paths=[])
        assert custom.get("/").status_code == 200
        assert custom.get("/health").status_code == 200
        assert custom.get("/api/protected").status_code == 401

    @pytest.mark.parametrize(
        "path", ["/health/deep", "/health/", "/docs/oauth2-redirect"]
    )
    def test_excluded_path_match_is_exact(self, client, path):
        """Exclusion is exact-match: no sub-path or trailing-slash may slip through."""
        response = client.get(path)
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing authorization header"

    def test_query_string_does_not_defeat_exclusion(self, client):
        """``request.url.path`` strips the query string, so ``/health?x=1`` matches."""
        assert client.get("/health", params={"x": "1"}).status_code == 200

    @pytest.mark.parametrize("method", ["post", "put", "delete"])
    def test_non_get_methods_are_guarded(self, client, method):
        """Only OPTIONS is exempt -- every other verb needs the password."""
        assert getattr(client, method)("/api/protected").status_code == 401
        assert (
            getattr(client, method)(
                "/api/protected", headers={"Authorization": f"Bearer {PASSWORD}"}
            ).status_code
            == 200
        )

    def test_password_is_cached_at_init_not_reread_per_request(self):
        """The middleware snapshots the password in ``__init__``; rotation is ignored."""
        client = _client(PASSWORD)
        with patch("api.auth.get_secret_from_env", return_value="rotated-pw"):
            assert (
                client.get(
                    "/api/protected", headers={"Authorization": f"Bearer {PASSWORD}"}
                ).status_code
                == 200
            )
            assert (
                client.get(
                    "/api/protected", headers={"Authorization": "Bearer rotated-pw"}
                ).status_code
                == 401
            )

    def test_unauthenticated_unknown_path_is_401_not_404(self, client):
        """The middleware runs before routing, but does not mask routing when authed."""
        response = client.get("/api/does-not-exist")
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing authorization header"

        authed = client.get(
            "/api/does-not-exist", headers={"Authorization": f"Bearer {PASSWORD}"}
        )
        assert authed.status_code == 404

    def test_uses_constant_time_comparison(self, client):
        """The password check must go through ``hmac.compare_digest``, not ``!=``."""
        with patch(
            "api.auth.hmac.compare_digest", wraps=hmac.compare_digest
        ) as compare_digest:
            client.get("/api/protected", headers={"Authorization": "Bearer wrong"})
        compare_digest.assert_called_once()


class TestNoPasswordConfigured:
    """With no password set the middleware is a pass-through."""

    @pytest.mark.parametrize("password", [None, ""])
    def test_all_requests_pass_without_header(self, password):
        client = _client(password)
        assert client.get("/api/protected").status_code == 200
        assert client.get("/").status_code == 200
        assert client.options("/api/protected").status_code == 200

    def test_bogus_header_still_passes(self):
        client = _client(None)
        response = client.get(
            "/api/protected", headers={"Authorization": "Basic nonsense"}
        )
        assert response.status_code == 200


class TestNonAsciiPassword:
    """Guards the wire-byte handling in ``_credential_bytes``.

    ASGI carries raw header bytes and Starlette decodes them as latin-1, so the
    credential string the middleware sees is the latin-1 decoding of whatever the
    client put on the wire. ``_credential_bytes`` re-encodes with latin-1 to
    recover those exact bytes, which are then compared against the configured
    password's UTF-8 bytes. Clients must therefore send UTF-8, as HTTP clients
    conventionally do. These tests drive the app over raw ASGI to control the
    bytes exactly.
    """

    LATIN1_PASSWORD = "pässwörd"

    def test_correct_non_ascii_password_accepted(self):
        app = _build_app(self.LATIN1_PASSWORD)
        status, body = _raw_asgi_get(
            app,
            "/api/protected",
            f"Bearer {self.LATIN1_PASSWORD}".encode("utf-8"),
        )
        assert status == 200
        assert body == '{"ok":"protected"}'

    def test_wrong_non_ascii_password_rejected(self):
        app = _build_app(self.LATIN1_PASSWORD)
        status, body = _raw_asgi_get(
            app, "/api/protected", "Bearer pässwört".encode("utf-8")
        )
        assert status == 401
        assert json.loads(body)["detail"] == "Invalid password"

    def test_ascii_credential_rejected_for_non_ascii_password(self):
        response = _client(self.LATIN1_PASSWORD).get(
            "/api/protected", headers={"Authorization": "Bearer password"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid password"

    def test_latin1_encoded_credential_rejected_not_crashed(self):
        """A client sending latin-1 wire bytes is rejected cleanly, never a 500.

        UTF-8 is the expected wire encoding; latin-1 bytes for a non-ASCII
        password no longer match. Pure-ASCII passwords are unaffected because
        their latin-1 and UTF-8 encodings are identical.
        """
        app = _build_app(self.LATIN1_PASSWORD)
        status, body = _raw_asgi_get(
            app,
            "/api/protected",
            f"Bearer {self.LATIN1_PASSWORD}".encode("latin-1"),
        )
        assert status == 401
        assert json.loads(body)["detail"] == "Invalid password"

    def test_password_outside_latin1_authenticates_over_http(self):
        """A CJK password sent as UTF-8 authenticates successfully."""
        app = _build_app(UNICODE_PASSWORD)
        status, body = _raw_asgi_get(
            app, "/api/protected", f"Bearer {UNICODE_PASSWORD}".encode("utf-8")
        )
        assert status == 200
        assert body == '{"ok":"protected"}'

    def test_wrong_password_outside_latin1_rejected(self):
        app = _build_app(UNICODE_PASSWORD)
        status, body = _raw_asgi_get(
            app, "/api/protected", "Bearer 中文-wrong".encode("utf-8")
        )
        assert status == 401
        assert json.loads(body)["detail"] == "Invalid password"


class TestCheckApiPassword:
    """The `check_api_password` dependency reads the password at CALL time."""

    @pytest.mark.parametrize("password", [None, ""])
    def test_returns_true_when_no_password_configured(self, password):
        with patch("api.auth.get_secret_from_env", return_value=password):
            assert check_api_password(credentials=None) is True

    def test_returns_true_for_correct_password(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=PASSWORD)
        with patch("api.auth.get_secret_from_env", return_value=PASSWORD):
            assert check_api_password(credentials=creds) is True

    def test_returns_true_for_correct_non_ascii_password(self):
        creds = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=UNICODE_PASSWORD
        )
        with patch("api.auth.get_secret_from_env", return_value=UNICODE_PASSWORD):
            assert check_api_password(credentials=creds) is True

    def test_raises_401_when_credentials_missing(self):
        with patch("api.auth.get_secret_from_env", return_value=PASSWORD):
            with pytest.raises(HTTPException) as exc_info:
                check_api_password(credentials=None)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Missing authorization"
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    def test_raises_401_when_password_wrong(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="nope")
        with patch("api.auth.get_secret_from_env", return_value=PASSWORD):
            with pytest.raises(HTTPException) as exc_info:
                check_api_password(credentials=creds)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid password"
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    def test_password_read_at_call_time_not_import_time(self):
        """The dependency picks up a password configured after import."""
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=PASSWORD)

        with patch("api.auth.get_secret_from_env", return_value=None):
            assert check_api_password(credentials=creds) is True

        with patch("api.auth.get_secret_from_env", return_value="rotated"):
            with pytest.raises(HTTPException) as exc_info:
                check_api_password(credentials=creds)
        assert exc_info.value.status_code == 401

    def test_works_as_a_route_dependency(self):
        """End-to-end through FastAPI's HTTPBearer wiring."""
        app = FastAPI()

        @app.get("/guarded")
        async def guarded(_: bool = Depends(check_api_password)):
            return {"ok": True}

        client = TestClient(app)

        with patch("api.auth.get_secret_from_env", return_value=PASSWORD):
            assert client.get("/guarded").status_code == 401
            assert (
                client.get(
                    "/guarded", headers={"Authorization": "Bearer wrong"}
                ).status_code
                == 401
            )
            ok = client.get("/guarded", headers={"Authorization": f"Bearer {PASSWORD}"})
        assert ok.status_code == 200
        assert ok.json() == {"ok": True}

    @pytest.mark.parametrize(
        "header",
        [
            f"Basic {PASSWORD}",
            PASSWORD,  # bare token, no scheme
            f"Token {PASSWORD}",
            "Bearer",  # scheme only
            "Bearer ",  # scheme + empty credentials
        ],
    )
    def test_non_bearer_header_yields_missing_authorization(self, header):
        """``HTTPBearer(auto_error=False)`` hands us ``None``, never a 403."""
        app = FastAPI()

        @app.get("/guarded")
        async def guarded(_: bool = Depends(check_api_password)):
            return {"ok": True}

        client = TestClient(app)

        with patch("api.auth.get_secret_from_env", return_value=PASSWORD):
            response = client.get("/guarded", headers={"Authorization": header})
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing authorization"

    def test_dependency_bearer_scheme_is_case_insensitive(self):
        """``HTTPBearer`` accepts a lowercase scheme, so the password still matches."""
        app = FastAPI()

        @app.get("/guarded")
        async def guarded(_: bool = Depends(check_api_password)):
            return {"ok": True}

        client = TestClient(app)

        with patch("api.auth.get_secret_from_env", return_value=PASSWORD):
            response = client.get(
                "/guarded", headers={"Authorization": f"bearer {PASSWORD}"}
            )
        assert response.status_code == 200


class TestAuthStatusEndpoint:
    """GET /auth/status from api/routers/auth.py."""

    @pytest.fixture
    def status_client(self):
        from api.routers.auth import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_reports_enabled_when_password_set(self, status_client):
        with patch("api.routers.auth.get_secret_from_env", return_value=PASSWORD):
            response = status_client.get("/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_enabled"] is True
        assert data["message"] == "Authentication is required"

    @pytest.mark.parametrize("password", [None, ""])
    def test_reports_disabled_when_no_password(self, status_client, password):
        with patch("api.routers.auth.get_secret_from_env", return_value=password):
            response = status_client.get("/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["auth_enabled"] is False
        assert data["message"] == "Authentication is disabled"

    def test_never_leaks_the_password_value(self, status_client):
        with patch(
            "api.routers.auth.get_secret_from_env", return_value=UNICODE_PASSWORD
        ):
            response = status_client.get("/auth/status")
        assert UNICODE_PASSWORD not in response.text
        assert set(response.json()) == {"auth_enabled", "message"}

    def test_status_reflects_password_changes_between_calls(self, status_client):
        """The endpoint re-reads the password per request -- nothing is cached."""
        with patch("api.routers.auth.get_secret_from_env", return_value=None):
            first = status_client.get("/auth/status").json()
        with patch("api.routers.auth.get_secret_from_env", return_value=PASSWORD):
            second = status_client.get("/auth/status").json()

        assert first["auth_enabled"] is False
        assert first["message"] == "Authentication is disabled"
        assert second["auth_enabled"] is True
        assert second["message"] == "Authentication is required"

    def test_status_endpoint_is_reachable_behind_the_middleware(self):
        """/auth/status itself is NOT excluded -- it requires the password."""
        from api.routers.auth import router

        app = FastAPI()
        app.include_router(router)
        with patch("api.auth.get_secret_from_env", return_value=PASSWORD):
            app.add_middleware(PasswordAuthMiddleware)
            app.middleware_stack = app.build_middleware_stack()

        client = TestClient(app)
        with patch("api.routers.auth.get_secret_from_env", return_value=PASSWORD):
            assert client.get("/auth/status").status_code == 401
            response = client.get(
                "/auth/status", headers={"Authorization": f"Bearer {PASSWORD}"}
            )
        assert response.status_code == 200
        assert response.json()["auth_enabled"] is True
