# ADR-007: Heavy extraction runtimes are opt-in, installed at container startup

- **Status**: Accepted
- **Date**: 2026-07
- **Related**: #1122 (this decision), #432/#1118 (Crawl4AI engine), #1104/#1120 (OCR toggle), #975 (pre-flight file support), #374 (offline install), [ADR-002](ADR-002-external-libraries.md) (external libraries), [Content Processing Engines](../../3-USER-GUIDE/content-processing-engines.md)

## Context

The Content Core 2.x upgrade (#939) exposed two selectable extraction runtimes that are far heavier than the rest of the stack:

- **Docling** (`content-core[docling]`) — layout-aware document parsing and OCR. Pulls a large machine-learning stack (torch/transformers and models), from several hundred MB to multiple GB.
- **Crawl4AI local** (`content-core[crawl4ai]`) — JavaScript rendering via a bundled Chromium browser (~300 MB plus system libraries).

The initial 2.x work bundled Crawl4AI into every image (#1118) and shipped an OCR toggle (#1120) that depended on Docling — which was never actually installed, making the toggle a silent no-op and image sources unsupported. So the default image was simultaneously **too heavy** (Chromium for everyone) and **missing** a runtime its own UI advertised.

Baking both into the default image would push it into the multi-GB range and contradict Open Notebook's lean, privacy-first, self-hostable posture (ADR-002 keeps this repo focused on the knowledge layer, delegating extraction to Content Core). Most users need neither runtime.

## Decision

**Keep a single lean default image. Make Docling and local Crawl4AI opt-in via environment variables; when enabled, install them at container startup and cache the downloads on the data volume.**

- Two booleans gate them: `OPEN_NOTEBOOK_ENABLE_DOCLING` and `OPEN_NOTEBOOK_ENABLE_CRAWL4AI`. A remote Crawl4AI server (`CRAWL4AI_API_URL`) needs no local install.
- The container **entrypoint** (`scripts/docker-entrypoint.sh`) runs the install **before** api/worker/frontend start (blocking), pinning each extra to the base image's `content-core` version for dependency compatibility.
- **Degrade, don't die:** a failed install (e.g. no network) logs loudly and boot continues; the runtime is reported unavailable rather than crashing the app.
- **Persist caches, not the venv.** `UV_CACHE_DIR`, `PLAYWRIGHT_BROWSERS_PATH` and `HF_HOME` live under `/app/data` (the user's volume), so a second boot reinstalls from cache without re-downloading. The virtualenv stays in the image layer and is repopulated from the cache each boot — immune to Python-version bumps in the base image. Chromium's apt system libraries live in the container filesystem and are reinstalled once per container.
- A backend **capability probe** (`GET /api/capabilities`) reports *actual* importability, and the Settings UI disables unavailable engines/OCR with an env-var hint — so the UI never advertises a runtime that isn't there (including mid-install).

## Alternatives considered

- **Bundle both into the default image** — rejected: multi-GB image for a feature most users don't use; wrong for a self-hostable, privacy-first product.
- **Publish a separate "full" image tag** — rejected for now: doubles the release/registry matrix and forces users to pick an image up front. Revisit if startup-install friction proves too high.
- **Persist the whole virtualenv on the volume** (the ComfyUI/Automatic1111 pattern) — rejected: couples the venv to the image's Python version and breaks on upgrades. Persisting only the download caches gets the "no re-download" benefit without that fragility.
- **Keep Crawl4AI bundled, add only Docling opt-in** — rejected: leaves ~300 MB of Chromium in every image for an engine that is itself optional. Treating both the same way is simpler and leaner.

## Consequences

- The default image is small again; base extraction (text PDFs, Office, EPUB, URLs via bs4/Jina/Firecrawl, audio, YouTube) is unchanged.
- **First boot with a flag set is slow** (minutes for Docling's ML stack); this is logged. Later boots are fast thanks to the volume cache.
- **Offline / air-gapped:** first-boot install needs network. Air-gapped operators leave the flags off. A build-arg to pre-bake the extras is possible future work (#374).
- Reproducibility depends on pinning the extra to the locked `content-core` version, done in the entrypoint.
- This validates ADR-002 in practice: because all extraction sits behind Content Core's single `extract_content()` boundary, adding an opt-in install path touched infra + one probe endpoint, not the extraction code.
