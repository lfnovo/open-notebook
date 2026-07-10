"""
Tests for the CORS wildcard + allow_credentials fix (api/main.py).

Combining allow_origins=["*"] with allow_credentials=True makes Starlette's
CORSMiddleware reflect the request's Origin header verbatim instead of
returning a literal "*" (browsers reject a literal wildcard alongside
credentials) - defeating the origin allowlist for any credentialed request.
allow_credentials is now keyed on the parsed origins list: False whenever it
contains "*" (whether from the unset default or an explicit CORS_ORIGINS=*),
True once an operator scopes CORS_ORIGINS to specific origins.
"""

from starlette.middleware.cors import CORSMiddleware
from starlette.testclient import TestClient

from api import main as api_main


class TestRealAppDefaultsToNoCredentialsWithWildcard:
    """The test environment has no CORS_ORIGINS set, matching the shipped
    default - this validates the actual registered app, not a simulation."""

    def test_default_test_environment_is_wildcard(self):
        assert api_main.CORS_IS_DEFAULT_WILDCARD is True
        assert api_main.CORS_ALLOWED_ORIGINS == ["*"]
        assert api_main.CORS_ALLOW_CREDENTIALS is False

    def test_cors_middleware_registered_with_credentials_disabled(self):
        matches = [
            m for m in api_main.app.user_middleware if m.cls is CORSMiddleware
        ]
        assert len(matches) == 1
        assert matches[0].kwargs["allow_credentials"] is False

    def test_real_response_does_not_claim_allow_credentials(self):
        client = TestClient(api_main.app)
        response = client.get(
            "/health", headers={"Origin": "https://evil.example.com"}
        )
        assert response.status_code == 200
        assert "access-control-allow-credentials" not in {
            k.lower() for k in response.headers.keys()
        }
        # Still reflects the origin (wildcard-equivalent), just without
        # granting credentialed access.
        assert response.headers.get("access-control-allow-origin") in ("*", "https://evil.example.com")


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

        headers = api_main._cors_headers(FakeRequest())
        assert "Access-Control-Allow-Credentials" not in headers

    def test_includes_allow_credentials_header_for_explicit_origins(self, monkeypatch):
        monkeypatch.setattr(api_main, "CORS_ALLOW_CREDENTIALS", True)
        monkeypatch.setattr(
            api_main, "CORS_ALLOWED_ORIGINS", ["https://notebook.example.com"]
        )

        class FakeRequest:
            headers = {"origin": "https://notebook.example.com"}

        headers = api_main._cors_headers(FakeRequest())
        assert headers["Access-Control-Allow-Credentials"] == "true"

    def test_disallowed_origin_still_gets_no_allow_origin_header(self, monkeypatch):
        monkeypatch.setattr(api_main, "CORS_ALLOW_CREDENTIALS", True)
        monkeypatch.setattr(
            api_main, "CORS_ALLOWED_ORIGINS", ["https://notebook.example.com"]
        )

        class FakeRequest:
            headers = {"origin": "https://evil.example.com"}

        headers = api_main._cors_headers(FakeRequest())
        assert "Access-Control-Allow-Origin" not in headers
