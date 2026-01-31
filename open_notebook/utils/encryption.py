"""
Field-level encryption for sensitive data using API keys.

This module provides encryption/decryption for API keys stored in the database.
Fernet uses AES-128-CBC with HMAC-SHA256 for authenticated encryption.

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
        "For security reasons, you must set a unique encryption key. "
        "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )


# Master encryption key (supports Docker secrets + auto-generation)
_ENCRYPTION_KEY = _get_or_create_encryption_key()


def get_fernet() -> Fernet:
    """
    Get Fernet instance with the configured encryption key.

    Returns:
        Fernet instance.

    Raises:
        ValueError: If encryption key is not configured.
    """
    return Fernet(_ENCRYPTION_KEY.encode())


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value using Fernet symmetric encryption.

    Args:
        value: The plain text string to encrypt.

    Returns:
        Base64-encoded encrypted string.

    Raises:
        ValueError: If encryption is not configured.
    """
    fernet = get_fernet()
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    """
    Decrypt a Fernet-encrypted string value.

    Handles graceful fallback for legacy unencrypted data.

    Args:
        value: The encrypted string (or plain text for legacy data).

    Returns:
        Decrypted plain text string, or original value if not encrypted.

    Raises:
        ValueError: If encryption is not configured or if decryption fails
            for what appears to be encrypted data (wrong key).
    """
    fernet = get_fernet()
    if not fernet:
        raise ValueError("Encryption is not configured. Set OPEN_NOTEBOOK_ENCRYPTION_KEY.")

    # Check if value appears to be encrypted (Fernet token format)
    # Fernet tokens are URL-safe base64, 56 bytes after decoding
    # They contain only URL-safe base64 chars: A-Za-z0-9_-
    import base64

    def looks_like_fernet_token(s: str) -> bool:
        """Check if string looks like a Fernet encrypted token."""
        if len(s) < 40:  # Minimum length for Fernet token
            return False
        # Fernet tokens use URL-safe base64
        try:
            decoded = base64.urlsafe_b64decode(s)
            return len(decoded) == 56  # Fernet token is always 56 bytes
        except Exception:
            return False

    try:
        return fernet.decrypt(value.encode()).decode()
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
        raise ValueError(f"Decryption failed: {str(e)}")
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
