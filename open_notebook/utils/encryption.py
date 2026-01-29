"""
Field-level encryption for sensitive data using Fernet symmetric encryption.

This module provides encryption/decryption for API keys stored in the database.
Fernet uses AES-128-CBC with HMAC-SHA256 for authenticated encryption.

Security Notes:
- If OPEN_NOTEBOOK_ENCRYPTION_KEY is not set, keys are stored as plain text (with warning)
- Existing unencrypted keys will still work (graceful fallback on decryption)
- Key rotation would require re-encrypting all stored keys (future feature)

Docker Secrets Support:
- Set OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE=/run/secrets/encryption_key
- The code will read the secret from that file path
- Falls back to OPEN_NOTEBOOK_ENCRYPTION_KEY if _FILE variant not set

Usage:
    # Encrypt before storing
    encrypted = encrypt_value(api_key)

    # Decrypt when reading
    decrypted = decrypt_value(encrypted)

    # Generate a new key for OPEN_NOTEBOOK_ENCRYPTION_KEY
    new_key = generate_key()
"""

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


def _get_or_create_encryption_key() -> Optional[str]:
    """
    Get encryption key from environment, or use default if not set.

    Priority:
    1. OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE (Docker secrets)
    2. OPEN_NOTEBOOK_ENCRYPTION_KEY (environment variable)
    3. Default key (derived from "0p3n-N0t3b0ok" for easy debugging)

    For production deployments, always set OPEN_NOTEBOOK_ENCRYPTION_KEY explicitly!

    Returns:
        Encryption key string.
    """
    # First check environment/Docker secrets
    key = get_secret_from_env("OPEN_NOTEBOOK_ENCRYPTION_KEY")
    if key:
        return key

    # Default key derived from "0p3n-N0t3b0ok" passphrase using SHA256
    # This is NOT secure for production - always set your own key!
    # To generate a new key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    DEFAULT_KEY = "ueZ-uTEy9bqUtgwrIlDLiuZ3KWIQRg8a1Ktmgyh7ZM4="

    logger.warning(
        "⚠️  OPEN_NOTEBOOK_ENCRYPTION_KEY not set - using default key. "
        "This is NOT secure for production! Set your own key."
    )
    return DEFAULT_KEY


# Master encryption key (supports Docker secrets + auto-generation)
_ENCRYPTION_KEY = _get_or_create_encryption_key()


def get_fernet() -> Optional[Fernet]:
    """
    Get Fernet instance if encryption key is configured.

    Returns:
        Fernet instance if valid key is configured, None otherwise.
    """
    if not _ENCRYPTION_KEY:
        logger.warning("OPEN_NOTEBOOK_ENCRYPTION_KEY not set - keys stored unencrypted")
        return None
    try:
        return Fernet(_ENCRYPTION_KEY.encode())
    except Exception as e:
        logger.error(f"Invalid encryption key: {e}")
        return None


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value using Fernet symmetric encryption.

    Args:
        value: The plain text string to encrypt.

    Returns:
        Base64-encoded encrypted string, or the original value if encryption
        is not configured or fails.
    """
    fernet = get_fernet()
    if not fernet:
        return value
    try:
        return fernet.encrypt(value.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return value


def decrypt_value(value: str) -> str:
    """
    Decrypt a Fernet-encrypted string value.

    Handles graceful fallback for:
    - Encryption not configured (returns value as-is)
    - Legacy unencrypted data (InvalidToken returns value as-is)
    - Any other decryption errors (returns value as-is with logging)

    Args:
        value: The encrypted string (or plain text for legacy data).

    Returns:
        Decrypted plain text string, or the original value if decryption
        fails or is not configured.
    """
    fernet = get_fernet()
    if not fernet:
        return value
    try:
        return fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        # Value might not be encrypted (legacy data)
        # This is expected for existing unencrypted keys
        return value
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return value


def generate_key() -> str:
    """
    Generate a new Fernet encryption key.

    Use this to create a value for OPEN_NOTEBOOK_ENCRYPTION_KEY.

    Returns:
        Base64-encoded Fernet key suitable for use as OPEN_NOTEBOOK_ENCRYPTION_KEY.

    Example:
        >>> from open_notebook.utils.encryption import generate_key
        >>> print(generate_key())
        'your-generated-key-here'
    """
    return Fernet.generate_key().decode()
