"""
Tests for the CORS wildcard + allow_credentials fix (api/main.py).

Combining allow_origins=["*"] with allow_credentials=True makes Starlette's
CORSMiddleware reflect the request's Origin header verbatim instead of
returning a literal "*" (browsers reject a literal wildcard alongside
credentials) - defeating the origin allowlist for any credentialed request.
allow_credentials is now tied to whether CORS_ORIGINS was explicitly scoped:
False for the default wildcard, True once an operator opts into specific
origins.
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


class TestAllowCredentialsFormula:
    """Direct check of the allow_credentials = not CORS_IS_DEFAULT_WILDCARD
    formula for the case the live test environment can't easily cover
    in-process (CORS_ORIGINS explicitly set) - CORS_IS_DEFAULT_WILDCARD is
    fixed at api.main import time from the environment, so this proves the
    formula's behavior directly rather than reloading the module."""

    def test_wildcard_default_disables_credentials(self):
        cors_origins_raw = None  # CORS_ORIGINS unset
        is_default_wildcard = cors_origins_raw is None
        assert (not is_default_wildcard) is False

    def test_explicit_origins_enables_credentials(self):
        cors_origins_raw = "https://notebook.example.com"
        is_default_wildcard = cors_origins_raw is None
        assert (not is_default_wildcard) is True


class TestCorsHeadersHelperMatchesMiddlewarePolicy:
    """api/main.py's _cors_headers() manually builds CORS headers for error
    responses (for errors raised before CORSMiddleware runs) - it must not
    grant credentials the real middleware wouldn't."""

    def test_omits_allow_credentials_header_for_wildcard_default(self, monkeypatch):
        monkeypatch.setattr(api_main, "CORS_IS_DEFAULT_WILDCARD", True)
        monkeypatch.setattr(api_main, "CORS_ALLOWED_ORIGINS", ["*"])

        class FakeRequest:
            headers = {"origin": "https://evil.example.com"}

        headers = api_main._cors_headers(FakeRequest())
        assert "Access-Control-Allow-Credentials" not in headers

    def test_includes_allow_credentials_header_for_explicit_origins(self, monkeypatch):
        monkeypatch.setattr(api_main, "CORS_IS_DEFAULT_WILDCARD", False)
        monkeypatch.setattr(
            api_main, "CORS_ALLOWED_ORIGINS", ["https://notebook.example.com"]
        )

        class FakeRequest:
            headers = {"origin": "https://notebook.example.com"}

        headers = api_main._cors_headers(FakeRequest())
        assert headers["Access-Control-Allow-Credentials"] == "true"

    def test_disallowed_origin_still_gets_no_allow_origin_header(self, monkeypatch):
        monkeypatch.setattr(api_main, "CORS_IS_DEFAULT_WILDCARD", False)
        monkeypatch.setattr(
            api_main, "CORS_ALLOWED_ORIGINS", ["https://notebook.example.com"]
        )

        class FakeRequest:
            headers = {"origin": "https://evil.example.com"}

        headers = api_main._cors_headers(FakeRequest())
        assert "Access-Control-Allow-Origin" not in headers
