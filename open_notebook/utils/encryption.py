"""
Field-level encryption for sensitive data using API keys.

This module provides encryption/decryption for API keys stored in the database.
Fernet uses AES-128-CBC with HMAC-SHA256 for authenticated encryption.

OPEN_NOTEBOOK_ENCRYPTION_KEY accepts **any string**. A Fernet key is derived
from it via PBKDF2-HMAC-SHA256, so users can set a simple passphrase like
``OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret`` and it will work. Values written
by versions predating the PBKDF2 derivation (bare SHA-256, unmarked) still
decrypt through the legacy path.

Usage:
    # Encrypt before storing
    encrypted = encrypt_value(api_key)

    # Decrypt when reading
    decrypted = decrypt_value(encrypted)
"""

import base64
import hashlib
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger


def get_secret_from_env(var_name: str) -> Optional[str]:
    """
    Get a secret from environment, supporting Docker secrets pattern.

    Checks for VAR_FILE first (Docker secrets), then falls back to VAR.

    Args:
        var_name: Base name of the environment variable (e.g., "OPEN_NOTEBOOK_ENCRYPTION_KEY")

    Returns:
        The secret value, or None if not configured.
    """
    # Check for _FILE variant first (Docker secrets)
    file_path = os.environ.get(f"{var_name}_FILE")
    if file_path:
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                secret = path.read_text().strip()
                if secret:
                    logger.debug(f"Loaded {var_name} from file: {file_path}")
                    return secret
                else:
                    logger.warning(f"{var_name}_FILE points to empty file: {file_path}")
            else:
                logger.warning(f"{var_name}_FILE path does not exist: {file_path}")
        except Exception as e:
            logger.error(f"Failed to read {var_name} from file {file_path}: {e}")

    # Fall back to direct environment variable
    return os.environ.get(var_name)


def _get_or_create_encryption_key() -> str:
    """
    Get encryption key from environment, requires explicit configuration.

    Priority:
    1. OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE (Docker secrets)
    2. OPEN_NOTEBOOK_ENCRYPTION_KEY (environment variable)

    For production deployments, you MUST set OPEN_NOTEBOOK_ENCRYPTION_KEY explicitly!

    Returns:
        Encryption key string.

    Raises:
        ValueError: If no encryption key is configured.
    """
    # First check environment/Docker secrets
    key = get_secret_from_env("OPEN_NOTEBOOK_ENCRYPTION_KEY")
    if key:
        return key

    raise ValueError(
        "OPEN_NOTEBOOK_ENCRYPTION_KEY is not set. "
        "Set this environment variable to any secret string to enable "
        "encrypted storage of API keys in the database."
    )


# Lazy-loaded encryption key: initialized on first use, not at import time.
# This prevents the entire app from crashing if the key is not yet configured
# when other modules import from this file.
_ENCRYPTION_KEY: Optional[str] = None


def _get_encryption_key() -> str:
    """Get the encryption key, initializing lazily on first call."""
    global _ENCRYPTION_KEY
    if _ENCRYPTION_KEY is None:
        _ENCRYPTION_KEY = _get_or_create_encryption_key()
    return _ENCRYPTION_KEY


# Version marker prefixed to every value written by the PBKDF2 derivation.
# Unmarked values are legacy (bare SHA-256 derivation) or plaintext.
PBKDF2_MARKER: str = "pbkdf2v1:"

# PBKDF2 cost parameter (OWASP guidance for HMAC-SHA256). Kept as a module
# constant so tests can monkeypatch it low; production must keep 600k.
PBKDF2_ITERATIONS: int = 600_000

# Fixed application salt (domain separation). Shared by all deployments by
# design: the threat model assumes a high-entropy OPEN_NOTEBOOK_ENCRYPTION_KEY
# (see docs/7-DEVELOPMENT/security.md), so the salt slows brute force without
# acting as a per-install secret. Recorded in ADR-009.
PBKDF2_SALT: bytes = b"open-notebook-credential-v1"


def derive_fernet_key(passphrase: str) -> str:
    """
    Derive a valid Fernet key from an arbitrary passphrase via PBKDF2.

    Uses PBKDF2-HMAC-SHA256 with the fixed application salt. Deliberately
    expensive so offline brute force of a weak passphrase is costly.

    Args:
        passphrase: The configured encryption key string.

    Returns:
        URL-safe base64-encoded 32-byte derived key.
    """
    derived = hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode(), PBKDF2_SALT, PBKDF2_ITERATIONS
    )
    return base64.urlsafe_b64encode(derived).decode()


def _derive_legacy_fernet_key(passphrase: str) -> str:
    """
    Derive the pre-#1317 Fernet key (bare unsalted SHA-256).

    Kept so values written before the PBKDF2 migration still decrypt.
    Must never be used for new writes.

    Args:
        passphrase: The configured encryption key string.

    Returns:
        URL-safe base64-encoded derived key.
    """
    derived = hashlib.sha256(passphrase.encode()).digest()
    return base64.urlsafe_b64encode(derived).decode()


# Cached Fernet instances, one per derivation scheme, initialized lazily on
# first use alongside _ENCRYPTION_KEY. Caching matters because PBKDF2 at the
# production iteration count is deliberately expensive (~50ms+).
_FERNET: Optional[Fernet] = None
_FERNET_LEGACY: Optional[Fernet] = None


def get_fernet() -> Fernet:
    """
    Get Fernet instance with the configured encryption key (PBKDF2 scheme).

    Returns:
        Fernet instance.

    Raises:
        ValueError: If encryption key is not configured.
    """
    global _FERNET
    if _FERNET is None:
        _FERNET = Fernet(derive_fernet_key(_get_encryption_key()).encode())
    return _FERNET


def _get_legacy_fernet() -> Fernet:
    """
    Get Fernet instance under the pre-#1317 derivation (decrypt-only).

    Returns:
        Fernet instance.

    Raises:
        ValueError: If encryption key is not configured.
    """
    global _FERNET_LEGACY
    if _FERNET_LEGACY is None:
        _FERNET_LEGACY = Fernet(
            _derive_legacy_fernet_key(_get_encryption_key()).encode()
        )
    return _FERNET_LEGACY


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value using Fernet symmetric encryption (PBKDF2 scheme).

    The stored form carries the version marker. Input that is already valid
    marked ciphertext is returned unchanged so a decrypt/save round trip can
    never double-wrap; anything else (including marker-like plaintext) is
    encrypted normally, so no input can be stored in a form that will never
    decrypt.

    Args:
        value: The plain text string to encrypt.

    Returns:
        Version-marked encrypted string.

    Raises:
        ValueError: If encryption is not configured.
    """
    if value.startswith(PBKDF2_MARKER):
        try:
            decrypt_value(value)
        except ValueError:
            pass
        else:
            logger.debug("encrypt_value received valid marked input; leaving as-is")
            return value
    fernet = get_fernet()
    return PBKDF2_MARKER + fernet.encrypt(value.encode()).decode()


def looks_like_fernet_token(s: str) -> bool:
    """
    Check if string looks like a Fernet encrypted token.

    Fernet tokens are versioned (1 byte) + timestamp (8 bytes) + IV (16 bytes)
    + ciphertext (variable, multiple of 16 with PKCS7 padding) + HMAC (32 bytes).
    Minimum decoded size is 73 bytes (1+8+16+16+32) for the smallest payload.
    """
    if len(s) < 100:  # Base64 of 73 bytes = ~100 chars minimum
        return False
    try:
        decoded = base64.urlsafe_b64decode(s)
        # Fernet: version(1) + timestamp(8) + IV(16) + ciphertext(>=16) + HMAC(32)
        # Minimum 73 bytes, ciphertext must be multiple of 16 (AES block size)
        if len(decoded) < 73:
            return False
        ciphertext_len = len(decoded) - 1 - 8 - 16 - 32
        return ciphertext_len > 0 and ciphertext_len % 16 == 0
    except Exception:
        return False


def decrypt_value(value: str) -> str:
    """
    Decrypt a Fernet-encrypted string value.

    Version-marked values decrypt under PBKDF2 only; any failure raises and
    the input is never returned as if it were a usable key. Unmarked values
    take the legacy path (old derivation, then plaintext fallback).

    Args:
        value: The encrypted string (or plain text for legacy data).

    Returns:
        Decrypted plain text string, or original value if not encrypted.

    Raises:
        ValueError: If encryption is not configured, if a marked value
            fails to decrypt, or if unmarked data looks encrypted but the
            key is incorrect.
    """
    if value.startswith(PBKDF2_MARKER):
        try:
            return get_fernet().decrypt(value[len(PBKDF2_MARKER) :].encode()).decode()
        except InvalidToken as e:
            raise ValueError(
                "Decryption failed: versioned value could not be decrypted. "
                "Check OPEN_NOTEBOOK_ENCRYPTION_KEY configuration."
            ) from e
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Decryption failed: unable to decrypt value.") from e

    try:
        return _get_legacy_fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        if looks_like_fernet_token(value):
            # Looks like encrypted data but failed to decrypt - likely wrong key
            raise ValueError(
                "Decryption failed: data appears to be encrypted but key is incorrect. "
                "Check OPEN_NOTEBOOK_ENCRYPTION_KEY configuration."
            )
        # Not a valid token - treat as legacy plaintext
        return value
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError("Decryption failed: unable to decrypt value.")
