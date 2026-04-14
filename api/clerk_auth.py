import asyncio
import time
from typing import Optional, Tuple

import httpx
import jwt
from jwcrypto import jwk
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


_JWKS_CACHE_TTL_SECONDS = 300  # 5 minutes
_jwks_cache: Optional[Tuple[dict, float]] = None
_jwks_lock = asyncio.Lock()


async def _fetch_jwks(jwks_url: str) -> dict:
    """Fetch JWKS from Clerk's well-known endpoint, with TTL-based cache."""
    global _jwks_cache
    async with _jwks_lock:
        if _jwks_cache is not None:
            cached_data, cached_at = _jwks_cache
            if (time.monotonic() - cached_at) < _JWKS_CACHE_TTL_SECONDS:
                return cached_data

        logger.info(f"Fetching JWKS from {jwks_url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10)
            response.raise_for_status()
            jwks_data = response.json()
            _jwks_cache = (jwks_data, time.monotonic())
            return jwks_data


def _get_signing_key(jwks_data: dict, kid: str) -> Optional[str]:
    """Extract the RSA public key matching the given kid from JWKS data."""
    for key_data in jwks_data.get("keys", []):
        if key_data.get("kid") == kid:
            jwk_key = jwk.JWK(**key_data)
            return jwk_key.export_to_pem()
    return None


async def verify_clerk_jwt(
    token: str,
    jwks_url: str,
    issuer: str,
) -> dict:
    """
    Verify a Clerk-issued JWT using the JWKS endpoint.

    Returns the decoded payload on success.
    Raises jwt.PyJWTError subtypes on any verification failure.
    """
    if not token:
        raise jwt.DecodeError("Empty token")

    unverified_header = jwt.get_unverified_header(token)

    algorithm = unverified_header.get("alg", "")
    if algorithm.lower() == "none":
        raise jwt.InvalidAlgorithmError("Algorithm 'none' is not allowed")

    kid = unverified_header.get("kid")
    if not kid:
        raise jwt.DecodeError("Token header missing 'kid'")

    jwks_data = await _fetch_jwks(jwks_url)
    public_key_pem = _get_signing_key(jwks_data, kid)

    if public_key_pem is None:
        # Key may have rotated within TTL window — clear cache and retry once
        clear_jwks_cache()
        jwks_data = await _fetch_jwks(jwks_url)
        public_key_pem = _get_signing_key(jwks_data, kid)

    if public_key_pem is None:
        raise jwt.InvalidSignatureError(f"No matching key found for kid '{kid}'")

    payload = jwt.decode(
        token,
        public_key_pem,
        algorithms=["RS256"],
        issuer=issuer,
        options={"require": ["exp", "iss", "sub"]},
    )
    return payload


def clear_jwks_cache() -> None:
    """Clear the cached JWKS data. Useful for testing or key rotation."""
    global _jwks_cache
    _jwks_cache = None


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Verifies Clerk JWT from Authorization header using JWKS."""

    def __init__(
        self,
        app,
        jwks_url: str,
        issuer: str,
        excluded_paths: Optional[list] = None,
        excluded_prefixes: Optional[list] = None,
    ):
        super().__init__(app)
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.excluded_paths = excluded_paths or ["/health", "/api/config"]
        self.excluded_prefixes = excluded_prefixes or ["/api/mcp/"]

    def _is_excluded(self, path: str) -> bool:
        if path in self.excluded_paths:
            return True
        for prefix in self.excluded_prefixes:
            if path.startswith(prefix):
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        if self._is_excluded(request.url.path):
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        if not self.jwks_url or not self.issuer:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.replace("Bearer ", "", 1)

        try:
            payload = await verify_clerk_jwt(
                token,
                jwks_url=self.jwks_url,
                issuer=self.issuer,
            )
        except jwt.PyJWTError as error:
            logger.debug(f"JWT verification failed: {error}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except httpx.HTTPError as error:
            logger.error(f"JWKS fetch failed: {error}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Unable to verify token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.user_id = payload["sub"]
        request.state.org_id = payload.get("org_id")

        return await call_next(request)
