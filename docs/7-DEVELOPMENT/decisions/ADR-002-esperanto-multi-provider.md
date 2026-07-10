# ADR-002: Esperanto for multi-provider AI

- **Status**: Accepted
- **Date**: 2026-07 (retroactive record — decision dates from project inception)
- **Related**: [PDR-002](PDR-002-provider-agnostic-core.md), [credentials.md](../credentials.md)

## Context

Multi-provider support is a core product promise ([VISION.md](../../../VISION.md)): users must be
able to run any AI provider, or fully local models, without the application caring. Coding
directly against each provider's SDK would spread provider-specific logic across every feature
and make adding providers a cross-cutting change.

## Decision

All model access (LLM, embeddings, TTS, STT) goes through the
[Esperanto](https://github.com/lfnovo/esperanto) library: one `AIFactory` interface, provider
differences abstracted below it. Application code selects models via the `Model` registry and
`ModelManager` / `provision_langchain_model()` — never by instantiating provider clients directly.

## Alternatives considered

- **LangChain provider classes directly** — workable, but couples every callsite to per-provider
  packages and configuration quirks; Esperanto normalizes config (and we control the library).
- **Per-provider adapters in-repo** — reinventing an abstraction that would drift; better
  maintained as a standalone reusable library.
- **Single provider (OpenAI) + "compatible" endpoints** — simplest, but breaks the no-lock-in
  promise and excludes local-first users.

## Consequences

- Adding a provider is mostly an Esperanto change plus registry/config sync in this repo
  (the four `SupportedProvider` locations — see `open_notebook/AGENTS.md`).
- 17 providers supported today through one interface.
- Provider-specific *capabilities* (not just models) are deliberately constrained by
  [PDR-002](PDR-002-provider-agnostic-core.md).
- Debugging sometimes spans two repos (open-notebook ↔ esperanto); upstream issues are labeled
  `esperanto`.
