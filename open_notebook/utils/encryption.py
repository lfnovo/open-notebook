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

    Args:
        value: The encrypted string (or plain text for legacy data).

    Returns:
        Decrypted plain text string.

    Raises:
        ValueError: If decryption fails or encryption is not configured.
        InvalidToken: If the value is not valid encrypted data.
    """
    fernet = get_fernet()
    if not fernet:
        raise ValueError("Encryption is not configured. Set OPEN_NOTEBOOK_ENCRYPTION_KEY.")
    try:
        return fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        # Value might not be encrypted (legacy data)
        # This is expected for existing unencrypted keys
        raise ValueError(
            "Decryption failed: value is not encrypted or uses a different key. "
            "If this is legacy unencrypted data, you may need to manually migrate it."
        )
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError(f"Decryption failed: {str(e)}")


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
