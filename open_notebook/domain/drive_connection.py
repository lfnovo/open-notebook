"""
Google Drive connection domain model.

A singleton record holding the OAuth connection this Open Notebook instance
uses to browse/import files from a single Google Drive account. This app is
single-user/couple-scale (see AGENTS.md), not multi-tenant, so there is
exactly one connection for the whole instance - the same singleton pattern
used by DefaultModels/ContentSettings/ProviderConfig
(open_notebook/domain/base.py RecordModel, open_notebook/ai/models.py,
open_notebook/domain/content_settings.py), sharing their `open_notebook`
singleton-records table via the fixed id `open_notebook:drive_connection`
(migration 26).

This is deliberately NOT the Credential model (open_notebook/domain/credential.py):
Credential is shaped for static, form-entered API keys for AI providers.
A Drive connection is fundamentally different - an access_token/refresh_token
pair obtained via a redirect-based OAuth flow, with a token_expiry that must
be checked (and the access_token refreshed) on every use.

access_token/refresh_token are stored Fernet-encrypted at rest using the same
helper as AI provider credentials (open_notebook/utils/encryption.py). Unlike
Credential (which decrypts eagerly in get()/get_all() and exposes plaintext
fields), the fields on this model always hold ciphertext once persisted -
callers must go through decrypt_access_token()/decrypt_refresh_token() to get
plaintext, and store_tokens() to write new (plaintext) tokens. This mirrors
RecordModel's raw object.__setattr__ load path (no field validators run), so
keeping "the field is ciphertext" as an invariant is simpler than trying to
decrypt transparently on load.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional, cast

from open_notebook.domain.base import RecordModel
from open_notebook.utils.encryption import decrypt_value, encrypt_value


class DriveConnection(RecordModel):
    record_id: ClassVar[str] = "open_notebook:drive_connection"

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    account_email: Optional[str] = None
    connected_at: Optional[datetime] = None

    @classmethod
    async def get_instance(cls) -> "DriveConnection":
        """Narrows RecordModel.get_instance()'s base-class return type for
        callers/mypy (mirrors DefaultModels.get_instance() in
        open_notebook/ai/models.py - same fix, no behavior change: RecordModel's
        `cls()` dispatch already returns a real DriveConnection at runtime)."""
        return cast("DriveConnection", await super().get_instance())

    @property
    def is_connected(self) -> bool:
        return bool(self.access_token and self.refresh_token)

    def decrypt_access_token(self) -> Optional[str]:
        if not self.access_token:
            return None
        return decrypt_value(self.access_token)

    def decrypt_refresh_token(self) -> Optional[str]:
        if not self.refresh_token:
            return None
        return decrypt_value(self.refresh_token)

    def is_access_token_expired(self, skip_seconds: int = 60) -> bool:
        """True if the access token is missing, expired, or expiring within
        `skip_seconds` - refresh proactively instead of racing a Drive API call
        against the actual expiry."""
        if not self.access_token or not self.token_expiry:
            return True
        expiry = self.token_expiry
        if expiry.tzinfo is None:
            # RecordModel loads DB values via object.__setattr__ with no field
            # validation (see base.py _load_from_db); be defensive about
            # naive datetimes rather than assume the driver always returns
            # timezone-aware ones.
            expiry = expiry.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (expiry - now).total_seconds() <= skip_seconds

    async def store_tokens(
        self,
        *,
        access_token: str,
        refresh_token: Optional[str],
        token_expiry: datetime,
        account_email: Optional[str] = None,
    ) -> None:
        """Encrypt and persist tokens.

        `refresh_token` is optional because Google only returns one on the
        first consent for a given user+client (subsequent access_type=offline
        exchanges with prompt=consent still return it here since we always
        pass prompt=consent, but a plain token *refresh* call never does) -
        preserve the existing encrypted refresh_token when none is supplied.
        `account_email` is optional so a token-refresh-only call doesn't have
        to re-fetch/re-pass it.
        """
        self.access_token = encrypt_value(access_token)
        if refresh_token:
            self.refresh_token = encrypt_value(refresh_token)
        self.token_expiry = token_expiry
        if account_email:
            self.account_email = account_email
        if not self.connected_at:
            self.connected_at = datetime.now(timezone.utc)
        await self.update()

    async def disconnect(self) -> None:
        """Clear the connection record (DELETE /api/drive/disconnect)."""
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.account_email = None
        self.connected_at = None
        await self.update()
