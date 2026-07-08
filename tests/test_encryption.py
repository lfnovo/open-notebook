"""
Unit tests for open_notebook.utils.encryption.

Covers the PBKDF2 key derivation and, most importantly, the backward-compat
fallback that lets ciphertext written under the older unsalted-SHA-256
derivation keep decrypting after the upgrade.
"""

import base64
import hashlib

import pytest
from cryptography.fernet import Fernet

from open_notebook.utils import encryption


@pytest.fixture(autouse=True)
def reset_encryption_state(monkeypatch):
    """Each test gets its own key and a clean set of lazily-cached globals."""
    monkeypatch.setenv("OPEN_NOTEBOOK_ENCRYPTION_KEY", "test-passphrase")
    monkeypatch.delenv("OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE", raising=False)
    encryption._ENCRYPTION_KEY = None
    encryption._FERNET_KEY = None
    encryption._LEGACY_FERNET_KEY = None
    yield
    encryption._ENCRYPTION_KEY = None
    encryption._FERNET_KEY = None
    encryption._LEGACY_FERNET_KEY = None


def legacy_encrypt(passphrase: str, value: str) -> str:
    """Reproduce the pre-PBKDF2 encryption scheme (unsalted single-round SHA-256)."""
    derived = hashlib.sha256(passphrase.encode()).digest()
    key = base64.urlsafe_b64encode(derived)
    return Fernet(key).encrypt(value.encode()).decode()


class TestKeyDerivation:
    def test_current_derivation_is_salted_pbkdf2_not_plain_sha256(self):
        current = encryption._derive_fernet_key("test-passphrase")
        legacy = encryption._derive_legacy_fernet_key("test-passphrase")
        assert current != legacy

    def test_derivation_is_deterministic(self):
        assert encryption._derive_fernet_key("abc") == encryption._derive_fernet_key(
            "abc"
        )

    def test_fernet_key_is_cached_across_calls(self):
        f1 = encryption.get_fernet()
        cached_key = encryption._FERNET_KEY
        f2 = encryption.get_fernet()
        assert encryption._FERNET_KEY == cached_key
        # Both instances must still decrypt each other's ciphertext.
        assert f2.decrypt(f1.encrypt(b"x")) == b"x"


class TestEncryptDecryptRoundTrip:
    def test_round_trip(self):
        encrypted = encryption.encrypt_value("sk-my-secret-api-key")
        assert encryption.decrypt_value(encrypted) == "sk-my-secret-api-key"

    def test_new_ciphertext_uses_current_scheme_directly(self):
        encrypted = encryption.encrypt_value("sk-another-key")
        # Should decrypt under the *current* Fernet without needing fallback.
        assert encryption.get_fernet().decrypt(encrypted.encode()).decode() == (
            "sk-another-key"
        )


class TestLegacyFallback:
    def test_legacy_sha256_ciphertext_still_decrypts(self):
        legacy_ciphertext = legacy_encrypt("test-passphrase", "sk-old-key")
        assert encryption.decrypt_value(legacy_ciphertext) == "sk-old-key"

    def test_legacy_ciphertext_does_not_decrypt_under_current_scheme_directly(self):
        """Sanity check that the fallback path is actually being exercised."""
        legacy_ciphertext = legacy_encrypt("test-passphrase", "sk-old-key")
        with pytest.raises(Exception):
            encryption.get_fernet().decrypt(legacy_ciphertext.encode())

    def test_legacy_plaintext_passes_through_unchanged(self):
        assert encryption.decrypt_value("plain-unencrypted-value") == (
            "plain-unencrypted-value"
        )

    def test_wrong_key_raises_for_current_scheme_ciphertext(self, monkeypatch):
        encrypted = encryption.encrypt_value("sk-secret")
        monkeypatch.setenv("OPEN_NOTEBOOK_ENCRYPTION_KEY", "a-different-passphrase")
        encryption._ENCRYPTION_KEY = None
        encryption._FERNET_KEY = None
        encryption._LEGACY_FERNET_KEY = None
        with pytest.raises(ValueError, match="key is incorrect"):
            encryption.decrypt_value(encrypted)

    def test_wrong_key_raises_for_legacy_scheme_ciphertext(self, monkeypatch):
        legacy_ciphertext = legacy_encrypt("test-passphrase", "sk-old-key")
        monkeypatch.setenv("OPEN_NOTEBOOK_ENCRYPTION_KEY", "a-different-passphrase")
        encryption._ENCRYPTION_KEY = None
        encryption._FERNET_KEY = None
        encryption._LEGACY_FERNET_KEY = None
        with pytest.raises(ValueError, match="key is incorrect"):
            encryption.decrypt_value(legacy_ciphertext)

    def test_reencrypting_a_legacy_value_upgrades_it_to_current_scheme(self):
        """Simulates a record being loaded (legacy ciphertext) then re-saved."""
        legacy_ciphertext = legacy_encrypt("test-passphrase", "sk-old-key")
        decrypted = encryption.decrypt_value(legacy_ciphertext)
        re_encrypted = encryption.encrypt_value(decrypted)

        assert re_encrypted != legacy_ciphertext
        # New ciphertext must decrypt directly under the current scheme -
        # no fallback needed anymore.
        assert (
            encryption.get_fernet().decrypt(re_encrypted.encode()).decode()
            == "sk-old-key"
        )
        assert encryption.decrypt_value(re_encrypted) == "sk-old-key"
