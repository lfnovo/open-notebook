# ADR-012: Provider endpoint overrides are declared in the registry

- **Status**: Accepted
- **Date**: 2026-10
- **Related**: #1409 (SiliconFlow), #1437 (Z.ai), #1438 (MiniMax), PR #1443

## Context

Some providers serve the same API from regional endpoints whose keys aren't interchangeable. SiliconFlow's mainland-China accounts only work against `api.siliconflow.cn`, and MiniMax keys are region-specific too. esperanto's profiles already read a `*_BASE_URL` override at runtime, and the credential form has a Base URL field, but discovery only honored a base URL for OpenAI, and env migration only copied the API key. Applying any stored base URL to every registry provider's discovery was considered and rejected: it silently changed behavior for providers whose registry URL carries provider-specific query params (ppq's `?type=all`).

## Decision

**A provider supports an endpoint override only if its `ProviderSpec` declares one: a `*_BASE_URL` entry in `optional_env`, exposed as `ProviderSpec.base_url_env`.** For those providers (and OpenAI, as before):

- Env migration copies the override into the credential's `base_url`, after the same `validate_url()` check the API applies.
- Credential-based discovery lists models at `<base_url>/models`. Env-based discovery does the same with the env value. Both go through `prepare_pinned_http_target` (validation and DNS pinning), like every user-supplied URL.
- Every other provider keeps its registry discovery URL, even if a credential has a base URL.

## Alternatives considered

- **Honor a base URL for every registry provider**: rejected because it changes existing providers' discovery and drops their URL quirks.
- **Credential form only, no env var**: rejected. Env-based setups and the env-to-credential migration would keep hitting the global endpoint, and esperanto reads the env var at runtime anyway.
- **A separate per-provider override table**: rejected. The registry is the single source of truth for provider metadata (see its module docstring), and `optional_env` already models "read during migration, not required".

## Consequences

- Adding a regional endpoint to a provider is a one-line registry change (`optional_env=("X_BASE_URL",)`). Discovery, migration and the docs contract follow.
- Overrides are always validated and DNS-pinned before Open Notebook fetches from them.
- A provider without a declared override ignores a credential's Base URL for discovery. Runtime calls still pass it to esperanto, so declare the override whenever the provider supports one.
