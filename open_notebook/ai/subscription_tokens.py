"""
Subscription OAuth token management.

This module is the single seam for authenticating Open Notebook against a
consumer AI *subscription* (Codex / ChatGPT, Claude Pro/Max) instead of a
pay-per-token API key. It:

  * imports the OAuth tokens that the official CLIs already store on disk
    (``~/.codex/auth.json`` for Codex/ChatGPT, ``~/.claude/.credentials.json``
    for Claude Code), and
  * refreshes those tokens against each provider's OAuth token endpoint when
    they are near expiry, persisting the new tokens back onto the Credential.

It deliberately knows nothing about request/response translation — that lives
in the subscription gateway. A future in-app OAuth *login* flow (authorize +
callback) would plug in here alongside the import functions; the Credential
storage shape is already designed for it.

IMPORTANT — EXPERIMENTAL / UNOFFICIAL:
    The OAuth client ids and token endpoints below are public-but-unofficial
    constants used by the official CLIs. Using a ChatGPT / Claude consumer
    subscription through a third-party app very likely violates the providers'
    Terms of Service and can get accounts flagged. These values can also change
    without notice. This path is opt-in and surfaced as "experimental" in the UI.
"""

from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from loguru import logger
from pydantic import SecretStr

# --- Local CLI credential file locations -----------------------------------

CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"
CLAUDE_AUTH_PATH = Path.home() / ".claude" / ".credentials.json"

# --- Unofficial OAuth constants (see module docstring) ---------------------
# Codex authenticates against a ChatGPT account; refresh goes through the
# OpenAI auth service. The client_id is the public Codex CLI client id.
CHATGPT_OAUTH = {
    "client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
    "token_url": "https://auth.openai.com/oauth/token",
}
# Claude Code's public OAuth client id; refresh goes through the Anthropic
# console OAuth token endpoint.
CLAUDE_OAUTH = {
    "client_id": "9d1c250a-e61b-44d9-88ed-5944d1962f5e",
    "token_url": "https://console.anthropic.com/v1/oauth/token",
}

# Refresh a token this long before it actually expires, to avoid races where a
# token expires mid-request.
EXPIRY_SKEW = timedelta(seconds=120)

# Per-credential locks so concurrent requests don't double-refresh a token.
_refresh_locks: Dict[str, asyncio.Lock] = {}


def _lock_for(credential_id: str) -> asyncio.Lock:
    lock = _refresh_locks.get(credential_id)
    if lock is None:
        lock = asyncio.Lock()
        _refresh_locks[credential_id] = lock
    return lock


def _decode_jwt_exp(token: str) -> Optional[datetime]:
    """Best-effort decode of a JWT's `exp` claim into a UTC datetime.

    Codex stores its access token as a JWT but does not record an explicit
    expiry in auth.json, so we read it from the token itself. Returns None if
    the token is not a decodable JWT.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        exp = claims.get("exp")
        if exp is None:
            return None
        return datetime.fromtimestamp(int(exp), tz=timezone.utc)
    except Exception:
        return None


# --- Detection / import ----------------------------------------------------


def detect_local_cli_tokens() -> Dict[str, bool]:
    """Return which CLI subscriptions have an importable token on this machine.

    Returns a dict like ``{"chatgpt": True, "claude": False}``. A provider is
    considered available only if its credential file exists and parses into the
    expected shape with a non-empty access token.
    """
    result = {"chatgpt": False, "claude": False}
    try:
        result["chatgpt"] = bool(_read_codex_tokens())
    except Exception as e:
        logger.debug(f"Codex CLI token not available: {e}")
    try:
        result["claude"] = bool(_read_claude_tokens())
    except Exception as e:
        logger.debug(f"Claude CLI token not available: {e}")
    return result


def _read_codex_tokens() -> Optional[Dict[str, Any]]:
    if not CODEX_AUTH_PATH.exists():
        return None
    data = json.loads(CODEX_AUTH_PATH.read_text())
    tokens = data.get("tokens") or {}
    access = tokens.get("access_token")
    refresh = tokens.get("refresh_token")
    if not access or not refresh:
        return None
    return {
        "access_token": access,
        "refresh_token": refresh,
        "account_id": tokens.get("account_id"),
        "expiry": _decode_jwt_exp(access),
    }


def _read_claude_tokens() -> Optional[Dict[str, Any]]:
    if not CLAUDE_AUTH_PATH.exists():
        return None
    data = json.loads(CLAUDE_AUTH_PATH.read_text())
    oauth = data.get("claudeAiOauth") or {}
    access = oauth.get("accessToken")
    refresh = oauth.get("refreshToken")
    if not access or not refresh:
        return None
    expires_at = oauth.get("expiresAt")
    expiry = None
    if expires_at is not None:
        # Claude stores epoch milliseconds.
        expiry = datetime.fromtimestamp(int(expires_at) / 1000, tz=timezone.utc)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "account_id": None,
        "expiry": expiry,
    }


def import_from_cli(kind: str) -> Dict[str, Any]:
    """Import OAuth tokens for ``kind`` ("chatgpt" | "claude") from the local CLI.

    Returns a dict with access_token, refresh_token, account_id, expiry. Raises
    ValueError if no importable token is present.
    """
    reader = {"chatgpt": _read_codex_tokens, "claude": _read_claude_tokens}.get(kind)
    if reader is None:
        raise ValueError(f"Unknown subscription kind: {kind}")
    tokens = reader()
    if not tokens:
        path = CODEX_AUTH_PATH if kind == "chatgpt" else CLAUDE_AUTH_PATH
        raise ValueError(
            f"No {kind} subscription token found. Expected the official CLI to "
            f"have written credentials to {path}."
        )
    return tokens


# --- Refresh ---------------------------------------------------------------


async def _refresh_chatgpt(refresh_token: str) -> Dict[str, Any]:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CHATGPT_OAUTH["client_id"],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(CHATGPT_OAUTH["token_url"], json=payload)
        resp.raise_for_status()
        data = resp.json()
    access = data["access_token"]
    return {
        "access_token": access,
        # OpenAI may or may not rotate the refresh token.
        "refresh_token": data.get("refresh_token", refresh_token),
        "expiry": _decode_jwt_exp(access)
        or (datetime.now(timezone.utc) + timedelta(seconds=int(data.get("expires_in", 3600)))),
    }


async def _refresh_claude(refresh_token: str) -> Dict[str, Any]:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLAUDE_OAUTH["client_id"],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(CLAUDE_OAUTH["token_url"], json=payload)
        resp.raise_for_status()
        data = resp.json()
    expires_in = int(data.get("expires_in", 3600))
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", refresh_token),
        "expiry": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
    }


_REFRESHERS = {"chatgpt": _refresh_chatgpt, "claude": _refresh_claude}


async def get_valid_access_token(credential) -> str:
    """Return a valid access token for a subscription credential, refreshing it
    if it is missing or within the expiry skew window.

    On refresh, the new access/refresh tokens and expiry are persisted onto the
    credential. Guarded by a per-credential lock to avoid concurrent double
    refreshes. ``credential`` is a ``Credential`` (typed loosely to avoid a
    circular import).
    """
    if credential.auth_type != "oauth_subscription":
        raise ValueError("Credential is not an OAuth subscription credential")
    if not credential.access_token:
        raise ValueError("Subscription credential has no access token")

    now = datetime.now(timezone.utc)
    expiry = credential.token_expiry
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if expiry is not None and now < (expiry - EXPIRY_SKEW):
        return credential.access_token.get_secret_value()

    refresher = _REFRESHERS.get(credential.subscription_kind)
    if refresher is None:
        # Unknown kind: fall back to whatever token we have rather than failing.
        return credential.access_token.get_secret_value()

    if not credential.refresh_token:
        # Can't refresh; return the (possibly expired) token and let upstream 401.
        return credential.access_token.get_secret_value()

    lock = _lock_for(str(credential.id))
    async with lock:
        # Re-read in case another waiter just refreshed.
        from open_notebook.domain.credential import Credential

        fresh = await Credential.get(str(credential.id))
        fresh_expiry = fresh.token_expiry
        if fresh_expiry is not None and fresh_expiry.tzinfo is None:
            fresh_expiry = fresh_expiry.replace(tzinfo=timezone.utc)
        if fresh_expiry is not None and datetime.now(timezone.utc) < (
            fresh_expiry - EXPIRY_SKEW
        ):
            # Update our in-hand object so the caller sees the refreshed token.
            credential.access_token = fresh.access_token
            credential.refresh_token = fresh.refresh_token
            credential.token_expiry = fresh.token_expiry
            return fresh.access_token.get_secret_value()

        logger.info(
            f"Refreshing {credential.subscription_kind} subscription token for "
            f"credential {credential.id}"
        )
        new_tokens = await refresher(fresh.refresh_token.get_secret_value())

        fresh.access_token = SecretStr(new_tokens["access_token"])
        fresh.refresh_token = SecretStr(new_tokens["refresh_token"])
        fresh.token_expiry = new_tokens["expiry"]
        await fresh.save()

        # Sync the in-hand object.
        credential.access_token = fresh.access_token
        credential.refresh_token = fresh.refresh_token
        credential.token_expiry = fresh.token_expiry
        return new_tokens["access_token"]
