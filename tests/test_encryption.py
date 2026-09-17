"""
Encryption contract for credential API keys (issue #1317).

Locks the versioned PBKDF2 derivation: new values carry a marker and
decrypt only under PBKDF2, legacy Fernet values and plaintext keep
reading, and a marked value under the wrong key raises instead of
leaking ciphertext shaped like a key.
"""

import base64
import hashlib

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from open_notebook.utils import encryption as enc
from open_notebook.utils.encryption import decrypt_value, encrypt_value


@pytest.fixture()
def enc_key(monkeypatch):
    """Isolate the module from ambient env and cached keys per test."""
    monkeypatch.setenv("OPEN_NOTEBOOK_ENCRYPTION_KEY", "test-passphrase")
    monkeypatch.delenv("OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE", raising=False)
    monkeypatch.setattr(enc, "_ENCRYPTION_KEY", None)
    monkeypatch.setattr(enc, "_FERNET", None)
    monkeypatch.setattr(enc, "_FERNET_LEGACY", None)
    return "test-passphrase"


@pytest.fixture()
def fast_kdf(monkeypatch, enc_key):
    """Lower the iteration count so the suite stays fast.

    One test asserts the production constant separately.
    """
    monkeypatch.setattr(enc, "PBKDF2_ITERATIONS", 1_000)
    return enc_key


def _legacy_token(secret: str, passphrase: str = "test-passphrase") -> str:
    """Ciphertext as written before #1317 (bare SHA-256 derivation)."""
    derived = hashlib.sha256(passphrase.encode()).digest()
    fernet = Fernet(base64.urlsafe_b64encode(derived))
    return fernet.encrypt(secret.encode()).decode()


def test_production_iteration_count():
    """The shipped cost parameter matches the agreed hardening level."""
    assert enc.PBKDF2_ITERATIONS == 600_000


def test_kdf_is_pbkdf2_not_sha256(enc_key):
    """The derived key equals PBKDF2-HMAC-SHA256 output, not bare SHA-256."""
    expected = base64.urlsafe_b64encode(
        hashlib.pbkdf2_hmac("sha256", enc_key.encode(), enc.PBKDF2_SALT, 600_000)
    ).decode()
    assert enc.derive_fernet_key(enc_key) == expected
    assert (
        enc.derive_fernet_key(enc_key)
        != base64.urlsafe_b64encode(hashlib.sha256(enc_key.encode()).digest()).decode()
    )


def test_round_trip_new_format(fast_kdf):
    """Encrypt then decrypt returns the original secret, marked at rest."""
    stored = encrypt_value("sk-live-secret")
    assert stored.startswith(enc.PBKDF2_MARKER)
    assert decrypt_value(stored) == "sk-live-secret"


def test_legacy_fernet_fallback(fast_kdf):
    """Ciphertext written by the old derivation still decrypts."""
    assert decrypt_value(_legacy_token("sk-legacy")) == "sk-legacy"


def test_legacy_plaintext_passthrough(fast_kdf):
    """Unencrypted legacy values pass through decryption unchanged."""
    assert decrypt_value("sk-plain-legacy") == "sk-plain-legacy"


def test_marked_value_wrong_key_raises(fast_kdf, monkeypatch):
    """A marked value under the wrong key raises, never returns ciphertext."""
    stored = encrypt_value("sk-live-secret")
    monkeypatch.setenv("OPEN_NOTEBOOK_ENCRYPTION_KEY", "wrong-passphrase")
    monkeypatch.setattr(enc, "_ENCRYPTION_KEY", None)
    monkeypatch.setattr(enc, "_FERNET", None)
    monkeypatch.setattr(enc, "_FERNET_LEGACY", None)
    with pytest.raises(ValueError):
        decrypt_value(stored)


def test_corrupt_marked_value_raises(fast_kdf):
    """Truncated or non-base64 marked payloads raise instead of passing through."""
    with pytest.raises(ValueError):
        decrypt_value(enc.PBKDF2_MARKER + "not-valid-base64!!!")
    with pytest.raises(ValueError):
        decrypt_value(enc.PBKDF2_MARKER + "aGk=")


def test_marker_like_plaintext_is_encrypted(fast_kdf):
    """Marker-like plaintext encrypts normally and round-trips losslessly."""
    plaintext = enc.PBKDF2_MARKER + "looks-like-a-key"
    stored = encrypt_value(plaintext)
    assert stored.startswith(enc.PBKDF2_MARKER)
    assert decrypt_value(stored) == plaintext


def test_corrupt_marked_input_is_not_passed_through(fast_kdf):
    """Corrupt marked input encrypts to a decryptable value, never passthrough."""
    corrupt = enc.PBKDF2_MARKER + "aGk="
    stored = encrypt_value(corrupt)
    assert decrypt_value(stored) == corrupt


def test_double_encrypt_guard(fast_kdf):
    """Encrypting an already-marked value does not double-wrap it."""
    stored = encrypt_value("sk-live-secret")
    assert encrypt_value(stored) == stored


def test_secretstr_shaped_value_round_trip(fast_kdf):
    """Values shaped like domain SecretStr payloads survive the round trip."""
    secret = SecretStr("sk-domain-shape").get_secret_value()
    assert decrypt_value(encrypt_value(secret)) == "sk-domain-shape"


class _FakeDB:
    """In-memory stand-in for the repository layer (no SurrealDB needed)."""

    def __init__(self, credentials, singleton):
        self.credentials = [dict(r) for r in credentials]
        self.singleton = dict(singleton) if singleton is not None else None
        self.updates = []
        self.upserts = []

    async def query(self, query_str, vars=None):
        if "FROM credential" in query_str:
            return [dict(r) for r in self.credentials]
        if "ONLY $record_id" in query_str:
            return [dict(self.singleton)] if self.singleton is not None else []
        raise AssertionError(f"unexpected query: {query_str}")

    async def update(self, table, record_id, data):
        self.updates.append((table, str(record_id), dict(data)))
        for row in self.credentials:
            if str(row.get("id")) == str(record_id):
                row.update(data)
        return []

    async def upsert(self, table, record_id, data):
        self.upserts.append((table, str(record_id), dict(data)))
        if self.singleton is not None:
            self.singleton.update(data)
        return []


@pytest.fixture()
def patch_repo(monkeypatch):
    """Patch the repository boundary; each test supplies its own fake."""
    import open_notebook.database.repository as repo

    def install(fake):
        monkeypatch.setattr(repo, "repo_query", fake.query)
        monkeypatch.setattr(repo, "repo_update", fake.update)
        monkeypatch.setattr(repo, "repo_upsert", fake.upsert)
        return fake

    return install


def _singleton(entries):
    """A raw provider_configs row holding nested credential entries."""
    return {"id": "open_notebook:provider_configs", "credentials": entries}


@pytest.mark.asyncio
async def test_pass_migrates_legacy_rows(patch_repo, fast_kdf):
    """Legacy rows are rewritten marked; verified rows are skipped."""
    from api.credentials_service import migrate_encryption_scheme

    legacy = _legacy_token("sk-legacy")
    marked = encrypt_value("sk-new")
    fake = patch_repo(
        _FakeDB(
            [
                {"id": "credential:one", "api_key": legacy},
                {"id": "credential:two", "api_key": marked},
                {"id": "credential:three", "api_key": None},
                {"id": "credential:four", "api_key": ""},
            ],
            _singleton({}),
        )
    )

    result = await migrate_encryption_scheme()

    assert result["migrated"] == ["credential:one"]
    assert sorted(result["skipped"]) == [
        "credential:four: empty",
        "credential:three: empty",
        "credential:two: already-migrated",
    ]
    assert result["errors"] == []
    rewritten = next(r for r in fake.credentials if r["id"] == "credential:one")
    assert rewritten["api_key"].startswith(enc.PBKDF2_MARKER)
    assert decrypt_value(rewritten["api_key"]) == "sk-legacy"


@pytest.mark.asyncio
async def test_pass_is_fail_closed_per_record(patch_repo, fast_kdf):
    """Corrupt rows are reported and left byte-identical; the pass continues."""
    from api.credentials_service import migrate_encryption_scheme

    corrupt = enc.PBKDF2_MARKER + "aGk="
    before = {"id": "credential:bad", "api_key": corrupt}
    fake = patch_repo(
        _FakeDB(
            [
                dict(before),
                {"id": "credential:good", "api_key": _legacy_token("sk-ok")},
            ],
            _singleton({}),
        )
    )

    result = await migrate_encryption_scheme()

    assert result["migrated"] == ["credential:good"]
    assert len(result["errors"]) == 1
    assert result["errors"][0].startswith("credential:bad:")
    assert "sk-" not in result["errors"][0]
    untouched = next(r for r in fake.credentials if r["id"] == "credential:bad")
    assert untouched["api_key"] == corrupt
    assert [u[1] for u in fake.updates] == ["credential:good"]


@pytest.mark.asyncio
async def test_pass_is_idempotent(patch_repo, fast_kdf):
    """A second run over a migrated corpus changes nothing and errors nothing."""
    from api.credentials_service import migrate_encryption_scheme

    patch_repo(
        _FakeDB(
            [{"id": "credential:one", "api_key": _legacy_token("sk-legacy")}],
            _singleton({}),
        )
    )
    first = await migrate_encryption_scheme()
    assert first["migrated"] == ["credential:one"]

    second = await migrate_encryption_scheme()
    assert second["migrated"] == []
    assert second["errors"] == []
    assert second["skipped"] == ["credential:one: already-migrated"]


@pytest.mark.asyncio
async def test_pass_migrates_singleton_entries(patch_repo, fast_kdf):
    """Nested provider_configs entries migrate in one rewrite; bad ones stay."""
    from api.credentials_service import migrate_encryption_scheme

    fake = patch_repo(
        _FakeDB(
            [],
            _singleton(
                {
                    "openai": [
                        {"name": "Default", "api_key": _legacy_token("sk-nested")},
                        {"name": "Broken", "api_key": enc.PBKDF2_MARKER + "aGk="},
                    ]
                }
            ),
        )
    )
    result = await migrate_encryption_scheme()

    assert result["migrated"] == ["provider_configs/openai/Default"]
    assert len(result["errors"]) == 1
    assert result["errors"][0].startswith("provider_configs/openai/Broken:")
    assert len(fake.upserts) == 1
    entries = fake.upserts[0][2]["credentials"]["openai"]
    assert decrypt_value(entries[0]["api_key"]) == "sk-nested"
    assert entries[1]["api_key"] == enc.PBKDF2_MARKER + "aGk="


@pytest.mark.asyncio
async def test_pass_requires_encryption_key(patch_repo, monkeypatch):
    """Without a configured key the pass fails closed before touching rows."""
    from api.credentials_service import migrate_encryption_scheme

    monkeypatch.delenv("OPEN_NOTEBOOK_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("OPEN_NOTEBOOK_ENCRYPTION_KEY_FILE", raising=False)
    monkeypatch.setattr(enc, "_ENCRYPTION_KEY", None)
    monkeypatch.setattr(enc, "_FERNET", None)
    monkeypatch.setattr(enc, "_FERNET_LEGACY", None)
    fake = patch_repo(_FakeDB([{"id": "credential:one", "api_key": "x"}], None))

    with pytest.raises(ValueError):
        await migrate_encryption_scheme()
    assert fake.updates == [] and fake.upserts == []


@pytest.fixture()
def client():
    """Test client mirroring tests/test_credentials_api.py."""
    from fastapi.testclient import TestClient

    from api.main import app

    return TestClient(app)


@pytest.mark.asyncio
async def test_pass_reports_placeholder_rows(patch_repo, fast_kdf):
    """UNDECRYPTABLE markers are reported, never re-encrypted into keys."""
    from api.credentials_service import migrate_encryption_scheme

    fake = patch_repo(
        _FakeDB(
            [{"id": "credential:one", "api_key": "UNDECRYPTABLE"}],
            _singleton({"openai": [{"name": "Default", "api_key": "UNDECRYPTABLE"}]}),
        )
    )
    result = await migrate_encryption_scheme()

    assert result["migrated"] == []
    assert result["errors"] == [
        "credential:one: decrypt-placeholder",
        "provider_configs/openai/Default: decrypt-placeholder",
    ]
    assert fake.credentials[0]["api_key"] == "UNDECRYPTABLE"
    assert fake.updates == [] and fake.upserts == []


@pytest.mark.asyncio
async def test_pass_reports_wrong_key_legacy_row(patch_repo, fast_kdf):
    """A legacy row encrypted under another key fails closed; others migrate."""
    from api.credentials_service import migrate_encryption_scheme

    foreign = _legacy_token("sk-foreign", passphrase="another-passphrase")
    fake = patch_repo(
        _FakeDB(
            [
                {"id": "credential:bad", "api_key": foreign},
                {"id": "credential:good", "api_key": _legacy_token("sk-ok")},
            ],
            _singleton({}),
        )
    )
    result = await migrate_encryption_scheme()

    assert result["migrated"] == ["credential:good"]
    assert result["errors"] == ["credential:bad: undecryptable-legacy"]
    untouched = next(r for r in fake.credentials if r["id"] == "credential:bad")
    assert untouched["api_key"] == foreign


def test_reencrypt_rejects_non_string_values():
    """Non-string stored values are errors, never migrated."""
    from api.credentials_service import _reencrypt_stored_value

    assert _reencrypt_stored_value(12345) == ("error", "unexpected-type")
    assert _reencrypt_stored_value(["sk-list"]) == ("error", "unexpected-type")


@pytest.mark.asyncio
async def test_pass_reports_malformed_singleton_entries(patch_repo, fast_kdf):
    """Non-list groups and non-dict entries are errors, never silent skips."""
    from api.credentials_service import migrate_encryption_scheme

    fake = patch_repo(
        _FakeDB(
            [],
            _singleton(
                {
                    "openai": "corrupt-group",
                    "anthropic": [
                        None,
                        {
                            "name": "Ok",
                            "api_key": _legacy_token("sk-ok"),
                        },
                    ],
                }
            ),
        )
    )
    result = await migrate_encryption_scheme()

    assert result["migrated"] == ["provider_configs/anthropic/Ok"]
    assert result["errors"] == [
        "provider_configs/openai: unexpected-group-type",
        "provider_configs/anthropic/0: unexpected-entry-type",
    ]
    assert len(fake.upserts) == 1


@pytest.mark.asyncio
async def test_pass_reports_write_failures(patch_repo, fast_kdf, monkeypatch):
    """Failed writes are errors, the pass continues, counts stay truthful."""
    import open_notebook.database.repository as repo
    from api.credentials_service import migrate_encryption_scheme

    patch_repo(
        _FakeDB(
            [{"id": "credential:one", "api_key": _legacy_token("sk-legacy")}],
            _singleton(
                {"openai": [{"name": "Default", "api_key": _legacy_token("sk-n")}]}
            ),
        )
    )

    async def boom_update(table, record_id, data):
        raise RuntimeError("db down")

    async def boom_upsert(table, record_id, data):
        raise RuntimeError("db down")

    monkeypatch.setattr(repo, "repo_update", boom_update)
    monkeypatch.setattr(repo, "repo_upsert", boom_upsert)

    result = await migrate_encryption_scheme()

    assert result["migrated"] == []
    assert result["errors"] == [
        "credential:one: write-failed",
        "provider_configs/openai/Default: write-failed",
    ]


def test_migrate_endpoint_returns_summary(client):
    """POST /api/credentials/migrate-encryption surfaces the service summary."""
    from unittest.mock import AsyncMock, patch

    summary = {"message": "done", "migrated": ["a"], "skipped": [], "errors": []}
    with patch(
        "api.routers.credentials.svc_migrate_encryption_scheme",
        AsyncMock(return_value=summary),
    ):
        response = client.post("/api/credentials/migrate-encryption")

    assert response.status_code == 200
    assert response.json() == summary


def test_migrate_endpoint_missing_key_is_bad_request(client):
    """A missing encryption key surfaces as 400, not 500."""
    from unittest.mock import AsyncMock, patch

    with patch(
        "api.routers.credentials.svc_migrate_encryption_scheme",
        AsyncMock(side_effect=ValueError("Encryption key not configured.")),
    ):
        response = client.post("/api/credentials/migrate-encryption")

    assert response.status_code == 400
