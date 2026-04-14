"""
Tests for Clerk JWT authentication middleware.

Self-contained test suite — mocks JWKS endpoint and JWT signing.
No real Clerk instance required.
"""

import time
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jwcrypto import jwk
from starlette.requests import Request
from starlette.responses import JSONResponse

from api.clerk_auth import ClerkAuthMiddleware, clear_jwks_cache


# =============================================================================
# TEST FIXTURES — RSA key pair and JWT factory
# =============================================================================


def _generate_rsa_key_pair():
    """Generate an RSA private key and matching JWK for JWKS mock."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    jwk_key = jwk.JWK.from_pem(public_pem)
    jwk_dict = jwk_key.export(as_dict=True)
    jwk_dict["kid"] = "test-key-1"
    jwk_dict["use"] = "sig"
    jwk_dict["alg"] = "RS256"
    return private_key, jwk_dict


PRIVATE_KEY, JWK_DICT = _generate_rsa_key_pair()
JWKS_RESPONSE = {"keys": [JWK_DICT]}

TEST_ISSUER = "https://test-app.clerk.accounts.dev"
TEST_JWKS_URL = "https://test-app.clerk.accounts.dev/.well-known/jwks.json"


def _make_jwt(
    sub="clerk_user_123",
    org_id=None,
    exp=None,
    iss=None,
    private_key=None,
    algorithm="RS256",
    kid="test-key-1",
    headers_override=None,
):
    """Build a signed JWT for testing."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "iss": iss or TEST_ISSUER,
        "iat": now,
        "exp": exp or (now + 3600),
        "nbf": now - 10,
    }
    if org_id is not None:
        payload["org_id"] = org_id

    key = private_key or PRIVATE_KEY
    headers = headers_override or {"kid": kid}
    return jwt.encode(payload, key, algorithm=algorithm, headers=headers)


def _build_test_app():
    """Build a minimal FastAPI app with ClerkAuthMiddleware for testing."""
    app = FastAPI()

    app.add_middleware(
        ClerkAuthMiddleware,
        jwks_url=TEST_JWKS_URL,
        issuer=TEST_ISSUER,
        excluded_paths=["/health", "/api/config"],
        excluded_prefixes=["/api/mcp/"],
    )

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.get("/api/config")
    async def config():
        return {"config": "ok"}

    @app.get("/api/mcp/tools")
    async def mcp_tools():
        return {"tools": []}

    @app.get("/api/workspaces")
    async def workspaces(request: Request):
        return {
            "user_id": request.state.user_id,
            "org_id": getattr(request.state, "org_id", None),
        }

    return app


@pytest.fixture(autouse=True)
def reset_jwks_cache():
    """Clear JWKS cache before each test to ensure isolation."""
    clear_jwks_cache()
    yield
    clear_jwks_cache()


@pytest.fixture
def test_app():
    return _build_test_app()


@pytest.fixture
def mock_jwks():
    """Patch _fetch_jwks in clerk_auth to return the test JWKS data."""

    async def fake_fetch_jwks(jwks_url: str) -> dict:
        return JWKS_RESPONSE

    with patch("api.clerk_auth._fetch_jwks", fake_fetch_jwks):
        yield


# =============================================================================
# HAPPY PATH
# =============================================================================


class TestClerkAuthHappyPath:
    """Tests for successful JWT verification flows."""

    @pytest.mark.asyncio
    async def test_valid_jwt_passes_middleware(self, test_app, mock_jwks):
        """Valid Clerk JWT -> request proceeds, user_id set on request.state."""
        token = _make_jwt(sub="clerk_user_123")
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/workspaces",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["user_id"] == "clerk_user_123"

    @pytest.mark.asyncio
    async def test_org_id_extracted(self, test_app, mock_jwks):
        """JWT with org_id claim -> request.state.org_id populated."""
        token = _make_jwt(sub="clerk_user_123", org_id="org_abc")
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/workspaces",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["org_id"] == "org_abc"

    @pytest.mark.asyncio
    async def test_excluded_paths_skip_auth(self, test_app, mock_jwks):
        """Request to /health -> no auth required."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_excluded_prefix_skip_auth(self, test_app, mock_jwks):
        """Request to /api/mcp/* -> no auth required."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/mcp/tools")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_options_preflight_skip_auth(self, test_app, mock_jwks):
        """CORS preflight OPTIONS request -> no auth required."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.options("/api/workspaces")
        assert response.status_code != 401


# =============================================================================
# ERROR CASES
# =============================================================================


class TestClerkAuthErrorCases:
    """Tests for authentication failure scenarios."""

    @pytest.mark.asyncio
    async def test_missing_auth_header_returns_401(self, test_app, mock_jwks):
        """No Authorization header -> 401."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/workspaces")
        assert response.status_code == 401
        assert (
            "Missing authorization" in response.json()["detail"].lower()
            or "missing authorization" in response.json()["detail"].lower()
        )

    @pytest.mark.asyncio
    async def test_invalid_jwt_returns_401(self, test_app, mock_jwks):
        """Malformed JWT -> 401."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/workspaces",
                headers={"Authorization": "Bearer garbage"},
            )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_jwt_returns_401(self, test_app, mock_jwks):
        """Expired JWT -> 401."""
        expired_token = _make_jwt(exp=int(time.time()) - 3600)
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/workspaces",
                headers={"Authorization": f"Bearer {expired_token}"},
            )
        assert response.status_code == 401


# =============================================================================
# ADVERSARIAL CASES
# =============================================================================


class TestClerkAuthAdversarial:
    """Tests for security edge cases."""

    @pytest.mark.asyncio
    async def test_jwt_signed_with_wrong_key_rejected(self, test_app, mock_jwks):
        """JWT signed with unknown key -> 401."""
        wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = _make_jwt(private_key=wrong_key, kid="unknown-kid")
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/workspaces",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_with_none_algorithm_rejected(self, test_app, mock_jwks):
        """JWT with alg=none -> 401."""
        now = int(time.time())
        payload = {
            "sub": "attacker",
            "iss": TEST_ISSUER,
            "iat": now,
            "exp": now + 3600,
        }
        # Craft an unsigned token manually
        none_token = jwt.encode(
            payload,
            key="",
            algorithm="none",  # nosec
        )
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/workspaces",
                headers={"Authorization": f"Bearer {none_token}"},
            )
        assert response.status_code == 401
