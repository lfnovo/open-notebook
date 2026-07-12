# ADR-002: Delegate platform/media support to focused external libraries

- **Status**: Accepted
- **Date**: 2026-07 (retroactive record — decision dates from project inception)
- **Related**: [PDR-002](PDR-002-provider-agnostic-core.md), [credentials.md](../credentials.md), [content-processing.md](../content-processing.md)

## Context

Open Notebook's value is the knowledge layer: organizing, understanding and generating from research content. But delivering it requires two areas of heavy, ever-changing integration code: AI provider APIs (17 providers across LLM/embedding/TTS/STT) and content extraction (50+ file types, URLs, video/audio platforms). Building that in-repo would bloat the codebase and pull maintenance attention away from the product core.

## Decision

**If a capability is about platform/media support and will require heavy integration coding, it doesn't belong in this repository.** It lives in a focused external library, keeping this project centered on the knowledge layer — and keeping those parts replaceable by other frameworks if we ever decide to swap them.

Applied today:

- **[Esperanto](https://github.com/lfnovo/esperanto)** — all model access (LLM, embeddings, TTS, STT) through one `AIFactory` interface. Application code selects models via the `Model` registry and `provision_langchain_model()`, never by instantiating provider clients directly.
- **[Content Core](https://github.com/lfnovo/content-core)** — all content extraction (files, URLs, media) through `extract_content()`.
- The same rule covers **[podcast-creator](https://github.com/lfnovo/podcast-creator)** for audio generation.

## Alternatives considered

- **Provider SDKs / extraction logic in-repo** — spreads platform-specific code across every feature and makes each new provider/format a cross-cutting change.
- **LangChain provider classes directly** — workable for models, but couples every callsite to per-provider packages and quirks; Esperanto normalizes config (and we control the library).
- **Single provider + "compatible" endpoints** — simplest, but breaks the no-lock-in promise and excludes local-first users.

## Consequences

- Adding a provider or content format is mostly an upstream change, plus registry/config sync here (e.g. the four `SupportedProvider` locations — see `open_notebook/AGENTS.md`).
- The libraries are independently versioned, testable and swappable; the boundary keeps this repo's scope honest.
- Debugging sometimes spans two repos; issues whose root cause is upstream get the `upstream` + library labels (`esperanto`, `content-core`, `podcast-creator`).
- Provider-specific *capabilities* (not just plumbing) remain constrained by [PDR-002](PDR-002-provider-agnostic-core.md).

## Addendum (2026-07): Content Core 2.x

The upgrade to Content Core 2.x (2.0.4) validated the "swappable external library" thesis in practice. New capabilities came straight from upstream — new formats (EPUB, Reddit posts, YouTube `/live/` and `/shorts/`), selectable URL/document engines (`auto`, `firecrawl`, `jina`, `crawl4ai`, `simple` / `docling`), and better licensing — while the only Open Notebook-side work was adapting our single `extract_content()` call site to 2.x's new keyword-only API. Upstream swapped PDF extraction from PyMuPDF (AGPL) to pdfplumber (MIT) and dropped moviepy in favour of direct ffmpeg, so Open Notebook inherited a cleaner license posture and fixed audio bugs for free. Concentrating all extraction behind that one boundary is what kept the blast radius so small.
