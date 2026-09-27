# Module system, feature additions and UX improvements

This document summarizes the `feat/module-system` branch relative to
`lfnovo/open-notebook`. The contribution is authored by `karacaismail`, with
implementation assistance from Codex and Claude. The existing implementation
commits remain in the branch history.

## Module system

A module system was created to separate local extensions from the upstream
notebook. It provides versioned manifests, dependency resolution, a registry,
authenticated service routing, navigation and page contributions, and persistent
module settings.

The frontend follows MVVM contracts with separate settings models, repositories,
view models and views. Module integration uses typed public contracts instead of
cross-module internal imports. Native AI services remain separately managed
infrastructure; this is not a claim that every service runs in one process.

Settings opens on **General** and provides a second **Modules settings** tab.
Installed modules have their own preferences and enable/disable controls. Runtime,
external-service and build-time activation have explicit semantics. Build-time
changes require a rebuild; toggles do not silently terminate running research or
erase its data.

Selected modules are prepared in an isolated build directory. Overlay base hashes
detect upstream drift before applying customizations. An upstream-only build
remains available. Existing URLs, evidence, service credentials and data volumes
are preserved during migration.

## Developed modules

| Module | Purpose and changes |
|---|---|
| `multi-model-research` | Multi-provider research, preliminary reports, a combined brief, web Deep Research, cross-checks, independent syntheses, final decisions, evidence preservation and run/stage controls. |
| `account-models` | Authenticated ChatGPT, Claude and Gemini CLI adapters, account-based preliminary research, available-model discovery, supported reasoning-effort selection and request cancellation. |
| `hybrid-search` | Multilingual lexical and vector retrieval, reciprocal rank fusion, document diversity, local neural reranking and shared Search/Ask retrieval. |
| `local-files` | Incremental local file catalog, file watching, filename/content/extension search, multilingual vectors, duplicate grouping, Office readers, local OCR and automatic orphan cleanup. |
| `local-embeddings` | Local Ollama embedding setup and model policy configuration. |
| `local-audio` | Local Whisper transcription and macOS fallback speech adapters. |
| `natural-voice` | Local neural speech and configuration for operator-supplied voice references. |
| `local-processing` | Source, provider and podcast compatibility adapters, plus CPU dependency constraints. |
| `local-workspace` | Optional interface, theme, density and compatibility customizations. |
| `local-deployment` | Sidecar setup, policy-aware launch tools, backup utilities and legacy launcher migration templates. |

Some modules package and isolate previously developed local functionality; others
introduce new capabilities. External dependencies, model weights, private reports,
credentials and voice reference recordings are not included in the repository.

## Additional features and correctness improvements

- Add an optional preliminary phase before the original eight tasks: three
  providers research through account connections, then ChatGPT combines their
  reports into a Markdown brief. This produces twelve tasks across five phases.
  The preliminary phase requires no Chrome window; later web research still uses
  the browser extension.
- Preserve original reports, attachments, sources, claim identifiers, dissent and
  review history through a shared evidence file for each round. Models receive
  the same evidence; provider-specific context budgets do not truncate it.
- Replace unnecessary JSON transport overhead with lossless Markdown, add explicit
  context-budget checks, and apply event-condition-action rules for duplicates,
  evidence preservation and submission safety.
- Prepare oversized account inputs with reversible in-band references and
  deterministic source partitions shared by same-round peers. Preserve the full
  claim register in consolidation, checkpoint each subrequest, and distinguish
  verified byte coverage from the semantic limitations of generated findings.
- Add retry intervals of 1, 5, 30, 90 and 250 minutes, measured from each failure.
  Retry eligibility distinguishes transient errors from authentication, context
  limits and uncertain submissions. Uncertain research is not blindly resent.
- Add independent controls for the entire run and for a selected stage. Preserve
  completed reports, isolate cancellation to the selected request, retain stage
  holds across restarts and block dependent work until required reports exist.
- Discover available account models for preliminary research and select the
  highest supported effort according to an explicit family/version policy.
  Limited model-unavailable fallback keeps identical evidence. Quota, partial
  output and timeout errors do not trigger blind model replacement.
- Keep large-packet synthesis tied to measured model/runtime calibration. Record
  selected models, effort and provider-reported identity in execution metadata.
- Apply file-type filters before lexical candidate limits and semantic top-k
  selection. Prioritize matching Office filenames for document-oriented queries,
  cache query/reranking work and avoid rebuilding PDF indexes for unrelated edits.
- Add XLSX cells/formulas, PPTX slides/notes, local image/scanned-PDF OCR and a
  configurable 256 MiB input limit. Requeue previously unsupported formats after
  parser upgrades and report extraction failures explicitly.
- Clean unreferenced chunks, full-text records and vectors automatically while
  preserving shared content still referenced by another file. Recheck references
  before committing embedding results.
- Preserve configured scope, exclusions and credentials during reinstallation;
  synchronize native service, startup and deployment copies.

## UX and visual improvements

The new features received UX and visual-design improvements:

- Redesign default model assignments with readable model/provider selections,
  purpose-specific cards, an accessible advanced disclosure, clear optional-field
  actions, automatic-save feedback and preserved embedding-change confirmation.
  The Models page uses the responsive settings shell; feedback is localized in
  all fourteen languages. Visual styling belongs to `local-workspace`.
- Replace the oversized research question with a compact document card that opens
  a styled Markdown modal.
- Improve action visibility with distinct toolbar placement, icons, clear labels,
  state-dependent actions and stronger visual hierarchy.
- Present research phases as a provider-aware timeline with progress, saved
  reports, source counts and the current phase.
- Explain why a stage stopped and show the next available action.
- Show retry countdowns, attempt counts and the current backoff interval.
- Separate whole-run controls from a selected stage's control card.
- Require two-step impact/risk confirmation for disruptive actions, including a
  risk acknowledgement checkbox and server-side stale-state checks.
- Explain when account work may restart and consume quota, or when provider-side
  web research may continue after local monitoring stops.
- Display context budgets, evidence checks, model execution details and partial
  search-index status. Provide English and Turkish interface text.
- Show evidence-preparation status, planned part counts, additional account-call
  costs and preserved checkpoint progress before continuing oversized synthesis.

## Validation and current boundaries

The earlier implementation validation passed 470 tests: 17 local-file tests,
31 account-adapter tests, 157 research-service tests, 56 hybrid-search tests and
209 frontend tests. TypeScript checks and the production build passed. These are
recorded implementation results, not a claim that documentation publication reran
the full suite. Live checks compared deployed code hashes, exercised the control
dialogs without submitting research mutations, and verified preserved report
hashes.

The evidence-preparation update passed 202 research-service tests, two startup-copy
tests and 34 focused
frontend tests, TypeScript and the production Docker build. Seven targeted fault
injections were detected by regression tests. Live read-only validation confirmed
identical source/part identities for both synthesis peers and the responsive
preparation panel. The full large research was not restarted. A small ChatGPT
paired fixture preserved the checked facts; Claude refused the referenced fixture,
leaving its paired quality comparison incomplete. These tests do not establish
lossless LLM summarization.

Initial content and vector indexing can remain incomplete after deployment;
results expose partial coverage. OCR depends on image quality. Legacy binary
DOC/XLS/PPT files and OCR of images embedded in Office documents are not supported
by these readers. External volumes need explicit scope configuration.

Provider quotas and web interfaces remain external constraints. Claude and Gemini
do not expose comparable remaining-credit data through these discovery interfaces.
Web Deep Research does not silently fall back to ordinary account research. A
maintained model-ranking policy does not guarantee the objectively best model for
every task or recognize all future model families automatically.

See the [module architecture](module-system.md),
[module guide](../../modules/README.md),
[stage-control contract](../../modules/multi-model-research/STAGE-CONTROLS.md),
[evidence-preparation guide](../../modules/multi-model-research/EVIDENCE-PREPARATION.md),
[account selection policy](../../modules/account-models/MODEL-SELECTION.md), and
[local-file guide](../../modules/local-files/README.md) for operational details.
