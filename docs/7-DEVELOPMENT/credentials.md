# Credential System

How Open Notebook stores, encrypts and provisions AI provider credentials — from the settings UI down to Esperanto model instantiation. This is the single reference for the subsystem; the frontend and backend halves are documented together on purpose.

## Overview

Users can configure provider credentials through the UI instead of environment variables. Keys are stored as individual `Credential` records in SurrealDB, encrypted with Fernet, and resolved at model-provisioning time with a database-first, environment-variable-fallback strategy.

```
Settings UI ──► /credentials API ──► Credential record (encrypted, SurrealDB)
                                          │
                Model record ──credential─┘        (preferred: direct link)
                     │
        ModelManager.get_model()
                     │
        credential.to_esperanto_config()  ──►  Esperanto AIFactory
                     │
        (no linked credential?)
                     └──► key_provider.provision_provider_keys()  ──►  env vars ──► Esperanto
```

## The `Credential` domain model (`open_notebook/domain/credential.py`)

- One record per credential (e.g. "My OpenAI Key", "Work Anthropic") — multiple credentials per provider are supported.
- Fields: `name`, `provider`, `modalities`, `api_key` (Pydantic `SecretStr`, masked in logs), plus provider-specific config (`base_url`, `endpoint`, `api_version`, mode-specific endpoints, `project`, `location`, `credentials_path`).
- `api_key` is encrypted with `encrypt_value()` before save and decrypted on read (`get()` / `get_all()` are overridden). Encryption requires `OPEN_NOTEBOOK_ENCRYPTION_KEY` (see [content-processing.md](content-processing.md#encryption) for the encryption utility itself).
- `to_esperanto_config()` builds the config dict passed to Esperanto's `AIFactory.create_*`.
- `provider_config.py` still exists only to migrate legacy `ProviderConfig` records.

## Provisioning: two paths

1. **Credential-linked model (preferred).** A `Model` record has a `credential` field pointing at a Credential. `ModelManager.get_model()` calls `credential.to_esperanto_config()` and passes the config directly — no env var mutation, multiple credentials per provider work naturally.
2. **Env-var fallback (`open_notebook/ai/key_provider.py`).** When a model has no linked credential, `provision_provider_keys(provider)` copies DB-stored keys into `os.environ` so Esperanto can read them; pre-existing env vars are left untouched when no DB config exists. Config maps (`PROVIDER_CONFIG`, `VERTEX_CONFIG`, `AZURE_CONFIG`, `OPENAI_COMPATIBLE_CONFIG` in `key_provider.py`) define the env-var ↔ config-field mapping per provider.

## The API surface (`api/routers/credentials.py`)

CRUD plus lifecycle operations: `POST /credentials/{id}/test` (connection check), `/discover` (list available models), `/register-models` (create Model records from discovery), and two migration endpoints (`/migrate-from-env`, `/migrate-from-provider-config`). Swagger at `/docs` documents the shapes.

**Supported providers (17)** are enforced by the `SupportedProvider` Literal in `api/models.py`, kept in sync with three other locations (frontend `ALL_PROVIDERS`, `connection_tester.TEST_MODELS`, `credentials_service.PROVIDER_ENV_CONFIG`):

- Simple API key: openai, anthropic, google, groq, mistral, deepseek, xai, openrouter, voyage, elevenlabs, deepgram, dashscope, minimax
- URL-based: ollama
- Multi-field: azure, vertex, openai_compatible

**Security properties**:

- API key values are never returned by any endpoint — only metadata (`has_api_key`, counts).
- Every URL field passes `validate_url()` (SSRF protection); private IPs/localhost are allowed by design for self-hosted services (Ollama, LM Studio). Hostname resolution runs in `asyncio.to_thread` to avoid blocking the event loop.
- Connection testing of Vertex credentials collapses "file missing / not JSON / wrong shape" errors into one generic message so the tester can't be used as a filesystem oracle.

## Connection testing (`open_notebook/ai/connection_tester.py`)

`test_provider_connection()` makes a minimal API call using the cheapest model per provider (`TEST_MODELS` map). URL-based providers get a server ping instead (`/api/tags` for Ollama, `/models` for OpenAI-compatible). Error messages are normalized for the UI: 401 → "Invalid API key", rate-limit → success ("connection works"), model-not-found → success ("key valid").

## Frontend half

- `src/lib/api/credentials.ts` — typed client mirroring the endpoints above. The `Credential` interface never carries the key value, only `has_api_key`.
- `src/lib/hooks/use-credentials.ts` — TanStack Query hooks (`useCredentials`, `useCreateCredential`, `useTestCredential`, …) with toast feedback. Mutations invalidate `CREDENTIAL_QUERY_KEYS.all` + provider/model keys; test results are kept in local state, not the query cache.

## Migration paths

Both migration endpoints are idempotent summaries (`migrated` / `skipped` / `errors`):

- **From env vars**: creates Credential records for providers whose env vars are set.
- **From legacy ProviderConfig**: converts old singleton records into individual Credentials.
