"""
Google Drive Service

Business logic for the Google Drive integration: OAuth connect/disconnect,
browsing files (metadata only), and importing a file as a Source by handing
its bytes to the existing source-creation pipeline (api/routers/sources.py) -
so a Drive-imported source gets the same async content-core extraction,
embedding eligibility, and notebook association as an uploaded file.

Routers stay thin (api/routers/drive.py); all Drive/Google HTTP calls and the
token-refresh logic live here, per this codebase's API layer convention
(open_notebook/AGENTS.md).

Env vars (read directly, matching how other optional integrations in this
codebase resolve config - e.g. CORS_ORIGINS in api/main.py, the provider env
vars read ad hoc in api/credentials_service.py):
    GOOGLE_DRIVE_CLIENT_ID
    GOOGLE_DRIVE_CLIENT_SECRET
    GOOGLE_DRIVE_REDIRECT_URI
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx
from loguru import logger

from api.models import SourceCreate, SourceResponse
from open_notebook.domain.drive_connection import DriveConnection
from open_notebook.domain.notebook import Notebook
from open_notebook.exceptions import (
    AuthenticationError,
    ConfigurationError,
    ExternalServiceError,
    NotFoundError,
)

GOOGLE_DRIVE_CLIENT_ID = os.getenv("GOOGLE_DRIVE_CLIENT_ID", "")
GOOGLE_DRIVE_CLIENT_SECRET = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET", "")
GOOGLE_DRIVE_REDIRECT_URI = os.getenv("GOOGLE_DRIVE_REDIRECT_URI", "")

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"
DRIVE_FILES_ENDPOINT = "https://www.googleapis.com/drive/v3/files"

DRIVE_SCOPES = (
    "https://www.googleapis.com/auth/drive.readonly "
    "https://www.googleapis.com/auth/userinfo.email"
)

DRIVE_FILE_LIST_FIELDS = "nextPageToken,files(id,name,mimeType,modifiedTime,iconLink)"

# Native Google Docs/Sheets/Slides have no binary representation - export them
# through Drive's files.export endpoint into a format content-core already
# knows how to extract (see open_notebook/graphs/source.py content_process).
# Other google-apps.* types (forms, drawings, sites, apps script, ...) aren't
# meaningfully exportable as document text and are rejected up front.
GOOGLE_NATIVE_EXPORT_MAP: Dict[str, Tuple[str, str]] = {
    "application/vnd.google-apps.document": ("text/plain", ".txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", ".csv"),
    "application/vnd.google-apps.presentation": ("application/pdf", ".pdf"),
}
GOOGLE_NATIVE_MIME_PREFIX = "application/vnd.google-apps."

HTTP_TIMEOUT_SECONDS = 30.0


def _require_oauth_config() -> None:
    if not (GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET and GOOGLE_DRIVE_REDIRECT_URI):
        raise ConfigurationError(
            "Google Drive is not configured. Set GOOGLE_DRIVE_CLIENT_ID, "
            "GOOGLE_DRIVE_CLIENT_SECRET and GOOGLE_DRIVE_REDIRECT_URI to enable it."
        )


def build_auth_url() -> str:
    """Build the Google OAuth consent screen URL.

    access_type=offline + prompt=consent guarantee a refresh_token comes back
    even on a repeat connect (Google only issues one on the very first
    consent for a given user+client otherwise).
    """
    _require_oauth_config()
    params = {
        "client_id": GOOGLE_DRIVE_CLIENT_ID,
        "redirect_uri": GOOGLE_DRIVE_REDIRECT_URI,
        "response_type": "code",
        "scope": DRIVE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"


async def _post_token_request(data: Dict[str, str]) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_ENDPOINT, data=data, timeout=HTTP_TIMEOUT_SECONDS
            )
        if response.status_code >= 400:
            logger.warning(f"Google token endpoint returned {response.status_code}: {response.text}")
            raise AuthenticationError(
                "Google rejected the token request. The authorization code may "
                "have expired, or the connection needs to be re-established."
            )
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Network error calling Google token endpoint: {e}")
        raise ExternalServiceError(f"Failed to reach Google's token endpoint: {e}") from e


async def _exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    _require_oauth_config()
    return await _post_token_request(
        {
            "code": code,
            "client_id": GOOGLE_DRIVE_CLIENT_ID,
            "client_secret": GOOGLE_DRIVE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_DRIVE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    )


async def _refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    _require_oauth_config()
    return await _post_token_request(
        {
            "refresh_token": refresh_token,
            "client_id": GOOGLE_DRIVE_CLIENT_ID,
            "client_secret": GOOGLE_DRIVE_CLIENT_SECRET,
            "grant_type": "refresh_token",
        }
    )


async def _fetch_account_email(access_token: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        if response.status_code >= 400:
            logger.warning(f"Google userinfo endpoint returned {response.status_code}")
            return None
        return response.json().get("email")
    except httpx.HTTPError as e:
        logger.warning(f"Failed to fetch Drive account email: {e}")
        return None


def _expiry_from_expires_in(expires_in: Any) -> datetime:
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        seconds = 3600  # Google's default access token lifetime
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


async def handle_oauth_callback(code: str) -> DriveConnection:
    """Exchange the authorization code for tokens, fetch the account email,
    and persist the connection. Called by GET /api/drive/callback."""
    tokens = await _exchange_code_for_tokens(code)
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if not access_token:
        raise AuthenticationError("Google did not return an access token")
    if not refresh_token:
        # Should not happen with access_type=offline&prompt=consent, but fail
        # loudly rather than silently storing a connection that can never
        # refresh once the short-lived access token expires.
        raise AuthenticationError(
            "Google did not return a refresh token. Disconnect any existing "
            "Open Notebook access at https://myaccount.google.com/permissions "
            "and try connecting again."
        )

    account_email = await _fetch_account_email(access_token)

    conn = await DriveConnection.get_instance()
    await conn.store_tokens(
        access_token=access_token,
        refresh_token=refresh_token,
        token_expiry=_expiry_from_expires_in(tokens.get("expires_in")),
        account_email=account_email,
    )
    return conn


async def get_status() -> Dict[str, Any]:
    conn = await DriveConnection.get_instance()
    return {"connected": conn.is_connected, "account_email": conn.account_email}


async def disconnect() -> None:
    conn = await DriveConnection.get_instance()
    if conn.is_connected:
        # Best-effort revoke - a failure here must never block the user from
        # clearing their local connection.
        token = conn.decrypt_refresh_token() or conn.decrypt_access_token()
        if token:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        GOOGLE_REVOKE_ENDPOINT,
                        params={"token": token},
                        timeout=HTTP_TIMEOUT_SECONDS,
                    )
            except httpx.HTTPError as e:
                logger.warning(f"Failed to revoke Google Drive token (continuing anyway): {e}")
    await conn.disconnect()


async def _get_connected_connection() -> DriveConnection:
    conn = await DriveConnection.get_instance()
    if not conn.is_connected:
        raise AuthenticationError("Google Drive is not connected. Connect it in Settings first.")
    return conn


async def _ensure_valid_access_token(conn: DriveConnection) -> str:
    """Shared refresh helper used by both list_files() and import_file() -
    proactively refreshes the access token when it's missing/expired/about to
    expire, persists the refresh, and returns a usable plaintext token."""
    if conn.is_access_token_expired():
        refresh_token = conn.decrypt_refresh_token()
        if not refresh_token:
            raise AuthenticationError(
                "Google Drive connection has no refresh token. Reconnect it in Settings."
            )
        tokens = await _refresh_access_token(refresh_token)
        access_token = tokens.get("access_token")
        if not access_token:
            raise AuthenticationError(
                "Failed to refresh the Google Drive access token. Reconnect it in Settings."
            )
        await conn.store_tokens(
            access_token=access_token,
            # Google's refresh grant normally does not return a new
            # refresh_token; store_tokens() preserves the existing one when
            # refresh_token is falsy here.
            refresh_token=tokens.get("refresh_token"),
            token_expiry=_expiry_from_expires_in(tokens.get("expires_in")),
        )
        return access_token
    token = conn.decrypt_access_token()
    if not token:
        raise AuthenticationError("Google Drive connection is missing an access token. Reconnect it in Settings.")
    return token


async def list_files(query: Optional[str], page_token: Optional[str]) -> Dict[str, Any]:
    """List Drive files (metadata only - id, name, mimeType, modifiedTime,
    iconLink) matching an optional name search, per the "read metadata,
    extract text only when needed" requirement."""
    conn = await _get_connected_connection()
    access_token = await _ensure_valid_access_token(conn)

    params: Dict[str, str] = {
        "fields": DRIVE_FILE_LIST_FIELDS,
        "pageSize": "50",
        # Exclude trashed files and folders - only files can be imported as
        # sources. name contains is a simple, cheap server-side filter;
        # Drive's fullText search is intentionally not used here since we
        # only need metadata for browsing, not content search.
        "q": "trashed = false and mimeType != 'application/vnd.google-apps.folder'",
        "orderBy": "modifiedTime desc",
    }
    if query:
        # Escape backslashes and single quotes per Drive API query syntax.
        safe_query = query.replace("\\", "\\\\").replace("'", "\\'")
        params["q"] += f" and name contains '{safe_query}'"
    if page_token:
        params["pageToken"] = page_token

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                DRIVE_FILES_ENDPOINT,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        if response.status_code >= 400:
            logger.warning(f"Drive files.list returned {response.status_code}: {response.text}")
            raise ExternalServiceError("Google Drive rejected the file list request")
        data = response.json()
    except httpx.HTTPError as e:
        logger.error(f"Network error listing Drive files: {e}")
        raise ExternalServiceError(f"Failed to reach Google Drive: {e}") from e

    return {
        "files": data.get("files", []),
        "next_page_token": data.get("nextPageToken"),
    }


async def _download_file_bytes(file_id: str, mime_type: str, access_token: str) -> Tuple[bytes, str]:
    """Download a Drive file's content, returning (bytes, extension).

    Native Google Docs/Sheets/Slides have no binary form and must go through
    files.export; anything else (PDF, docx, txt, ... already uploaded to
    Drive in a normal format) is fetched as-is via alt=media.
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    if mime_type.startswith(GOOGLE_NATIVE_MIME_PREFIX):
        export = GOOGLE_NATIVE_EXPORT_MAP.get(mime_type)
        if not export:
            raise ExternalServiceError(
                f"Google Drive file type '{mime_type}' cannot be exported as a document "
                "(only Docs, Sheets and Slides are supported)."
            )
        export_mime_type, extension = export
        url = f"{DRIVE_FILES_ENDPOINT}/{file_id}/export"
        params = {"mimeType": export_mime_type}
    else:
        url = f"{DRIVE_FILES_ENDPOINT}/{file_id}"
        params = {"alt": "media"}
        extension = ""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, params=params, headers=headers, timeout=HTTP_TIMEOUT_SECONDS
            )
        if response.status_code >= 400:
            logger.warning(f"Drive file download returned {response.status_code}: {response.text}")
            raise ExternalServiceError("Google Drive rejected the file download request")
        return response.content, extension
    except httpx.HTTPError as e:
        logger.error(f"Network error downloading Drive file {file_id}: {e}")
        raise ExternalServiceError(f"Failed to download file from Google Drive: {e}") from e


async def _fetch_file_metadata(file_id: str, access_token: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DRIVE_FILES_ENDPOINT}/{file_id}",
                params={"fields": "id,name,mimeType"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=HTTP_TIMEOUT_SECONDS,
            )
        if response.status_code >= 400:
            logger.warning(f"Drive files.get returned {response.status_code}: {response.text}")
            raise ExternalServiceError("Google Drive rejected the file metadata request")
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Network error fetching Drive file metadata {file_id}: {e}")
        raise ExternalServiceError(f"Failed to reach Google Drive: {e}") from e


def _drive_filename_with_extension(name: str, mime_type: str, export_extension: str) -> str:
    import mimetypes
    from pathlib import Path

    if export_extension:
        # Native Google Docs/Sheets/Slides: the Drive display name never
        # carries a real extension, so append the one for the export format.
        return f"{name}{export_extension}"

    if Path(name).suffix:
        return name

    guessed = mimetypes.guess_extension(mime_type) or ""
    return f"{name}{guessed}"


async def import_file(file_id: str, notebook_id: str) -> SourceResponse:
    """Download a Drive file and hand it to the existing source-creation
    pipeline, so it behaves identically to an uploaded source (same async
    processing, same content-core extraction, same embedding eligibility).

    `api.routers.sources` internals are imported lazily (function-local) to
    avoid making this module's import time depend on that router's full
    dependency chain (content_core, surreal_commands, ...) - mirrors this
    codebase's existing pattern of deferred imports for cross-module calls
    (see e.g. api/credentials_service.py's
    `from open_notebook.ai.models import Model`).
    """
    from api.routers.sources import (
        _build_content_state,
        _create_source_async_path,
        _write_uploaded_file,
    )

    # Notebook.get() raises NotFoundError itself when missing; the global
    # exception handlers in api/main.py map that to a 404.
    if not await Notebook.get(notebook_id):
        raise NotFoundError(f"Notebook {notebook_id} not found")

    conn = await _get_connected_connection()
    access_token = await _ensure_valid_access_token(conn)

    metadata = await _fetch_file_metadata(file_id, access_token)
    mime_type = metadata.get("mimeType", "")
    drive_name = metadata.get("name") or file_id

    content, export_extension = await _download_file_bytes(file_id, mime_type, access_token)
    filename = _drive_filename_with_extension(drive_name, mime_type, export_extension)

    file_path = await asyncio.to_thread(_write_uploaded_file, filename, content)

    source_data = SourceCreate(
        type="upload",
        notebooks=[notebook_id],
        title=drive_name,
        transformations=[],
        embed=False,
        delete_source=False,
        async_processing=True,
    )

    content_state = await _build_content_state(source_data, file_path)
    return await _create_source_async_path(source_data, content_state, [], file_path)
