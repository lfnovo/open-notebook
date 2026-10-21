# Credentials UI Security Review (January 2026, historical)

> **Historical snapshot.** This is a point-in-time review of the API key management feature (the Manage → Models credentials UI), done on 2026-01-27/28. It is **not** a security assessment of Open Notebook as a whole, and it is not kept up to date. Rows that were wrong at the time or have since changed are annotated below (corrections verified against the code in October 2026, v1.15.0).
>
> For current guidance see [Security Configuration](5-CONFIGURATION/security.md) (operators) and [Developer security notes](7-DEVELOPMENT/security.md) plus the decision records in [docs/7-DEVELOPMENT/decisions/](7-DEVELOPMENT/decisions/) (contributors). To report a vulnerability, follow [SECURITY.md](../SECURITY.md).

---

## Scope

API key management: database-first credential storage with environment-variable fallback, the connection tester, and the frontend forms that create credentials. Authentication was reviewed only as far as it protects these endpoints.

---

## Encryption

| Item | Status (Jan 2026) | Notes |
|------|-------------------|-------|
| Fernet encryption implemented | PASS | `open_notebook/utils/encryption.py`, AES-128-CBC + HMAC-SHA256 |
| Keys encrypted before DB storage | PASS | `encrypt_value()` applied on save |
| Keys decrypted only when needed | PASS | `decrypt_value()` called when reading |
| Encryption key required | PASS | No default key; `ValueError` if not configured. **Gap not noted at the time:** the shipped `docker-compose.yml` sets the public placeholder `change-me-to-a-secret-string`, which passes the "is set" check without any warning |
| Key derivation | *(not reviewed)* | **Changed since.** In January the Fernet key was a bare SHA-256 of the passphrase. Since v1.15.0 it is PBKDF2-HMAC-SHA256 with 600k iterations and a fixed application salt, new values carry a `pbkdf2v1:` marker, and `POST /api/credentials/migrate-encryption` rewrites old values (#1317, ADR-009) |
| Docker secrets support | PASS | `_FILE` suffix pattern supported |
| Documented in .env.example | PASS | Encryption key documented |

---

## API Security

| Item | Status (Jan 2026) | Notes |
|------|-------------------|-------|
| Test endpoint implemented | PASS | `connection_tester.py` validates keys |
| Test doesn't expose keys | PASS | Only returns success/failure |
| Error messages don't leak info | PASS | Generic error messages |
| URL validation for SSRF | **PARTIAL** (corrected) | The original note, "Blocks private IPs (except Ollama)", was wrong. `url_validation.py` deliberately **allows** private IPs and localhost for every provider (self-hosted servers need them). It blocks non-http(s) schemes, link-local addresses (169.254.0.0/16, fe80::/10, including IPv4-mapped forms) and the AWS IPv6 metadata address `fd00:ec2::254`. Outbound calls to user-supplied hosts are pinned to the vetted IP to close DNS-rebinding gaps (`prepare_pinned_http_target`) |
| Rate limiting | NOT IMPL | Still not implemented |

---

## Frontend Security

| Item | Status (Jan 2026) | Notes |
|------|-------------------|-------|
| No keys in localStorage | PASS | Provider API keys live only in component state while typed. (The **instance password** is stored in `localStorage` after login; see [Security Configuration](5-CONFIGURATION/security.md#how-the-ui-handles-it)) |
| Keys masked in UI | PASS | Shows a placeholder; the API never returns stored keys |
| No keys in console.log | PASS | No logging of sensitive data |
| autocomplete attributes | PARTIAL | Only the API key input in `CredentialFormDialog.tsx` sets `autoComplete="off"`. The "Frontend forms … PASS" row in the files table below should be read with this caveat |

---

## Authentication

| Item | Status (Jan 2026) | Notes |
|------|-------------------|-------|
| Password protection | PASS | Bearer token authentication |
| Default password | PASS | No hardcoded default; auth is fully disabled when `OPEN_NOTEBOOK_PASSWORD` is unset |
| Docker secrets support | PASS | `_FILE` suffix for password |
| Security warnings | **PARTIAL** (corrected) | The original note, "Logged when using defaults", was wrong. The API warns only when the encryption key is missing and when `CORS_ORIGINS` is the default wildcard. Nothing is logged when `OPEN_NOTEBOOK_PASSWORD` is unset or when the placeholder encryption key is used |

---

## Not covered by this review

Topics outside the credentials UI that a whole-application review would need, several of which changed after January 2026: CORS configuration (`CORS_ORIGINS`), request body limits (`OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB`), the SurrealDB `root`/`root` default, source upload handling, and the password stored in browser `localStorage`.

---

## Files Reviewed

| Component | Path | Status (Jan 2026) |
|-----------|------|-------------------|
| Encryption | `open_notebook/utils/encryption.py` | PASS |
| Credential model | `open_notebook/domain/credential.py` | PASS |
| Credentials router | `api/routers/credentials.py` | PASS |
| Key provider | `open_notebook/ai/key_provider.py` | PASS |
| Connection tester | `open_notebook/ai/connection_tester.py` | PASS |
| Auth middleware | `api/auth.py` | PASS |
| Frontend forms | `frontend/src/components/settings/*.tsx` | PASS (see autocomplete caveat above) |
| Environment example | `.env.example` | PASS |

---

## Recommendations made at the time

1. **Rate limiting** on `/api/credentials/*` endpoints — not implemented.
2. **Autocomplete attributes** on all password inputs — partly done.
3. **Show the last 4 characters** of stored keys — not implemented.
4. **Audit logging** of API key changes — not implemented.

---

## Original conclusion (January 2026)

> The API Configuration UI implementation meets security requirements: API keys encrypted at rest using Fernet (key must be explicitly configured); keys never returned to frontend; URL validation prevents SSRF attacks; Docker secrets supported for production deployments. **Review Status: PASS**

With the corrections above, the accurate reading is: the credentials UI encrypts keys at rest and never returns them, SSRF protection targets cloud metadata endpoints only (private networks are intentionally reachable), and two rows were overstated. The verdict applied to that feature only.
