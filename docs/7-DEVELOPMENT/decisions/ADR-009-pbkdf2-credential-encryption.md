# ADR-009: PBKDF2 credential key derivation with versioned ciphertext

- **Status**: Accepted
- **Date**: 2026-09-17
- **Related**: #1317 (supersedes stale #1020), [security.md](../security.md), [content-processing.md](../content-processing.md)

## Context

Stored provider API keys were encrypted under a Fernet key derived with a single unsalted SHA-256 round — fast to compute, which makes offline brute force of a weak `OPEN_NOTEBOOK_ENCRYPTION_KEY` passphrase cheap. The module had no tests and no upgrade path.

## Decision

**Derive with PBKDF2-HMAC-SHA256 (600k iterations, fixed application salt) and mark new ciphertext with a `pbkdf2v1:` prefix, keeping a legacy decrypt path for unmarked values.** The salt is shared by all deployments by design: the threat model assumes a high-entropy key, so the salt provides domain separation and brute-force slowdown, not per-install uniqueness. A per-install random salt would complicate the done-marker and the downgrade story for no modeled gain. Lazy re-encrypt-on-save was rejected as the migration mechanism because API keys are set once and would never upgrade — a one-shot `POST /credentials/migrate-encryption` pass (idempotent, fail-closed per record) does the upgrade instead.

## Alternatives considered

- **argon2/scrypt** — stronger memory-hardness, but a new dependency for unsettled gain; PBKDF2 is stdlib and matches the agreed hardening level.
- **Re-encryption as a `commands/` worker job** — wrong shape: worker jobs are async background work, while the pass is an admin one-shot with a request/response summary. A migration endpoint mirroring the existing credentials migrations fits.
- **Opportunistic re-encrypt on read** — deferred: it turns every read into a potential write and was not asked for; the explicit pass plus always-new-format writes converge the corpus.

## Consequences

- New values are forward-breaking: pre-migration code cannot use marked values — depending on token bytes it either raises a decryption error or mis-presents the ciphertext as a plaintext key (verified against the pre-change decrypt path) — so rollback after partial migration requires a database backup (CHANGELOG warning).
- PBKDF2 cost (~50ms+ per fresh derivation) is cached per process; the iteration count is a module constant so a future guidance change needs a new marker version.
- Changing `OPEN_NOTEBOOK_ENCRYPTION_KEY` still orphans stored values — key rotation remains unimplemented.
