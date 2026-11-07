"""
Tests for the CORS wildcard + allow_credentials fix (api/main.py).

Combining allow_origins=["*"] with allow_credentials=True makes Starlette's
CORSMiddleware reflect the request's Origin header verbatim instead of
returning a literal "*" (browsers reject a literal wildcard alongside
credentials) - defeating the origin allowlist for any credentialed request.
allow_credentials is now keyed on the parsed origins list: False whenever it
contains "*" (whether from the unset default or an explicit CORS_ORIGINS=*),
True once an operator scopes CORS_ORIGINS to specific origins.

Without OPEN_NOTEBOOK_PASSWORD and with CORS_ORIGINS unset, the default only
admits localhost origins (ADR-014).
"""

from typing import cast

import pytest
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.testclient import TestClient

from api import main as api_main


class TestRealAppWithoutPasswordIsLocalhostOnly:
    """The test environment sets no password and no CORS_ORIGINS, matching
    the shipped default - this validates the actual registered app, not a
    simulation. Without a password the default only admits localhost origins."""

    def test_default_test_environment_is_localhost_only(self):
        assert api_main.CORS_LOCALHOST_ONLY is True
        assert api_main.CORS_IS_DEFAULT_WILDCARD is False
        assert api_main.CORS_ALLOWED_ORIGINS == []
        assert api_main.CORS_ALLOWED_ORIGIN_REGEX == api_main.LOCALHOST_ORIGIN_REGEX
        assert api_main.CORS_ALLOW_CREDENTIALS is False

    def test_cors_middleware_registered_with_localhost_regex(self):
        matches = [m for m in api_main.app.user_middleware if m.cls is CORSMiddleware]
        assert len(matches) == 1
        assert matches[0].kwargs["allow_credentials"] is False
        assert (
            matches[0].kwargs["allow_origin_regex"] == api_main.LOCALHOST_ORIGIN_REGEX
        )

    @pytest.mark.parametrize(
        "origin",
        [
            "http://localhost:8502",
            "http://localhost:3000",
            "http://127.0.0.1:8502",
            "http://[::1]:8502",
            "https://localhost",
        ],
    )
    def test_localhost_origins_are_allowed(self, origin):
        client = TestClient(api_main.app)
        response = client.get("/health", headers={"Origin": origin})
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
        assert "access-control-allow-credentials" not in {
            k.lower() for k in response.headers.keys()
        }

    @pytest.mark.parametrize(
        "origin",
        [
            "https://evil.example.com",
            "http://localhost.evil.example.com",
            "http://127.0.0.1.evil.example.com:8502",
            "http://192.168.1.10:8502",
        ],
    )
    def test_other_origins_are_not_allowed(self, origin):
        client = TestClient(api_main.app)
        response = client.get("/health", headers={"Origin": origin})
        assert response.status_code == 200
        assert "access-control-allow-origin" not in {
            k.lower() for k in response.headers.keys()
        }

    def test_preflight_from_other_origin_is_rejected(self):
        client = TestClient(api_main.app)
        response = client.options(
            "/api/notebooks",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 400


class TestLocalhostOnlyPolicySelection:
    """CORS_LOCALHOST_ONLY is fixed at api.main import time, so these exercise
    the same predicate used there."""

    def test_no_password_and_no_cors_origins_is_localhost_only(self):
        assert api_main._uses_localhost_only_cors(None, password_set=False) is True

    def test_password_keeps_the_wildcard_default(self):
        assert api_main._uses_localhost_only_cors(None, password_set=True) is False

    def test_explicit_cors_origins_are_kept_without_password(self):
        assert (
            api_main._uses_localhost_only_cors(
                "http://192.168.1.10:8502", password_set=False
            )
            is False
        )

    def test_explicit_wildcard_is_kept_without_password(self):
        assert api_main._uses_localhost_only_cors("*", password_set=False) is False


class TestExplicitWildcardAlsoDisablesCredentials:
    """An operator who sets CORS_ORIGINS=* explicitly must get the same
    treatment as the unset default. The predicate keys on the parsed list
    containing "*", not on whether the env var was set - keying on the env
    var would reintroduce the exact reflect-any-Origin behavior this fix
    prevents. CORS_ALLOW_CREDENTIALS is fixed at api.main import time, so
    these exercise the real parser plus the same expression used there."""

    def test_explicit_wildcard_disables_credentials(self):
        origins = api_main._parse_cors_origins("*")
        assert origins == ["*"]
        assert ("*" not in origins) is False

    def test_explicit_origins_enable_credentials(self):
        origins = api_main._parse_cors_origins(
            "https://notebook.example.com, https://other.example.com"
        )
        assert origins == [
            "https://notebook.example.com",
            "https://other.example.com",
        ]
        assert ("*" not in origins) is True


class TestCorsHeadersHelperMatchesMiddlewarePolicy:
    """api/main.py's _cors_headers() manually builds CORS headers for error
    responses (for errors raised before CORSMiddleware runs) - it must not
    grant credentials the real middleware wouldn't."""

    def test_omits_allow_credentials_header_for_wildcard(self, monkeypatch):
        monkeypatch.setattr(api_main, "CORS_ALLOW_CREDENTIALS", False)
        monkeypatch.setattr(api_main, "CORS_ALLOWED_ORIGINS", ["*"])

        class FakeRequest:
            headers = {"origin": "https://evil.example.com"}

        # cast: _cors_headers only reads request.headers
        headers = api_main._cors_headers(cast(Request, FakeRequest()))
        assert "Access-Control-Allow-Credentials" not in headers

    def test_includes_allow_credentials_header_for_explicit_origins(self, monkeypatch):
        monkeypatch.setattr(api_main, "CORS_ALLOW_CREDENTIALS", True)
        monkeypatch.setattr(
            api_main, "CORS_ALLOWED_ORIGINS", ["https://notebook.example.com"]
        )

        class FakeRequest:
            headers = {"origin": "https://notebook.example.com"}

        # cast: _cors_headers only reads request.headers
        headers = api_main._cors_headers(cast(Request, FakeRequest()))
        assert headers["Access-Control-Allow-Credentials"] == "true"

    def test_disallowed_origin_still_gets_no_allow_origin_header(self, monkeypatch):
        monkeypatch.setattr(api_main, "CORS_ALLOW_CREDENTIALS", True)
        monkeypatch.setattr(
            api_main, "CORS_ALLOWED_ORIGINS", ["https://notebook.example.com"]
        )

        class FakeRequest:
            headers = {"origin": "https://evil.example.com"}

        # cast: _cors_headers only reads request.headers
        headers = api_main._cors_headers(cast(Request, FakeRequest()))
        assert "Access-Control-Allow-Origin" not in headers


class TestCorsHeadersHelperLocalhostOnly:
    """_cors_headers() must follow the localhost-only regex the same way the
    real middleware does."""

    def _headers_for(self, origin, monkeypatch):
        monkeypatch.setattr(api_main, "CORS_ALLOW_CREDENTIALS", False)
        monkeypatch.setattr(api_main, "CORS_ALLOWED_ORIGINS", [])
        monkeypatch.setattr(
            api_main, "CORS_ALLOWED_ORIGIN_REGEX", api_main.LOCALHOST_ORIGIN_REGEX
        )

        class FakeRequest:
            headers = {"origin": origin}

        # cast: _cors_headers only reads request.headers
        return api_main._cors_headers(cast(Request, FakeRequest()))

    def test_localhost_origin_is_reflected(self, monkeypatch):
        headers = self._headers_for("http://localhost:8502", monkeypatch)
        assert headers["Access-Control-Allow-Origin"] == "http://localhost:8502"

    def test_other_origin_is_not_reflected(self, monkeypatch):
        headers = self._headers_for("https://evil.example.com", monkeypatch)
        assert "Access-Control-Allow-Origin" not in headers
