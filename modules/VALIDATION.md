# Module migration validation

Validated on 2026-09-21 with the original repository at `3127f14`.

| Check | Result |
|---|---|
| Module registry/proxy/auth/persistence/disable leases | 17 tests passed |
| Research sidecar, including real local DOM fixtures and portable extension installer | 102 tests passed |
| Account adapter | 15 tests passed |
| Frontend with selected modules | 181 tests passed |
| Core-only frontend | 164 tests passed |
| TypeScript, both frontend configurations | Passed |
| ESLint, new module UI and changed navigation | No errors |
| Linux production frontend build, selected modules | Passed |
| Linux production frontend build, core only | Passed |
| Browser UI, synthetic failure fixture | Desktop/mobile, Markdown dialog, focus return, timer, all failure reasons; no model requests |
| Browser UI, live local deployment | Research feedback and module settings rendered without page errors; read-only inspection |
| Data preservation across application update | All 15 existing completed report fingerprints unchanged |

The research/account/audio services and the source worker were left running in
place. Only the notebook API and frontend processes were restarted. No data mounts
or database schemas were changed. A previous-image tag and an application-code
backup were retained privately by the operator.

These checks do not claim the browser providers will always accept future jobs,
that model agreement proves accuracy, or that the final research packet fits every
model's context limit. No billable eight-stage research was started for this module
migration. Runtime toggling gates application access; it does not uninstall native
services, remove reports or undo compiled build customizations.

## Module settings and MVVM update — 2026-09-21

The settings host now has General (default) and Modules settings tabs, per-module
preferences, optional disablement, independent edit revisions and explicit
requested/applied build state. See ADR-009 for architecture and current adapter
boundaries; this does not claim every legacy service runs inside one process.

| Check | Result |
|---|---|
| Module contracts, settings, migration, auth, dependencies, real model/podcast entry points, audio denial and real plain-text extraction | 36 passed |
| Existing model/provider/podcast regression tests | 69 passed |
| Export-to-build selection and policy-aware backup tests | 5 passed |
| Selected-module frontend | 194 passed |
| Core-only frontend | 177 passed |
| Final targeted settings/model/view tests | 16 passed |
| TypeScript / production build, selected modules and core only | Passed |
| ESLint, module framework UI and settings host | No errors |
| Real Chrome DOM, isolated API fixture | Toggles, saved drafts, independent module edits, requested/applied state, mobile control bounds; no provider calls |
| Live local UI | General default, all eight enabled, own preferences, legacy settings link, desktop/mobile; no mutations |
| Deployment data integrity | All 16 existing completed report fingerprints retained |

The broad provider regressions caught over-broad podcast normalization and a
premature timeout default that would suppress compatible-provider environment
resolution. The final adapter normalizes only managed local models; other
providers retain their existing configuration. No test was weakened to hide this.

API, frontend and the idle source worker were restarted so request admission is
consistent in both API and worker processes. Research/account/audio processes,
credentials, volumes and databases were retained. A previous-image tag and code
backup provide rollback. Runtime preferences apply on subsequent notebook
requests; build adapters require a new build, and maintenance tools consume a
fresh exported policy. No live research or audio generation was started by these
checks. Existing dependency deprecation warnings are unrelated to this change.

## 2026-09-21 — research context budget

- Lossless Markdown presentation with full report/evidence byte preservation, provenance,
  reversible claim history and exact URL attribution; canonical archive unchanged.
- Explicit raw/CLI/count/margin/ceiling fields and round-2 context forecast, with a strict
  pre-submission guard and no automatic retry for `context_limit`.
- New transport is opt-in and refuses an older bridge instead of silently re-escaping.
- Real two-run/six-packet comparison validates all report and attachment bytes and claim
  register reconstruction. The large final packet remains above the conservative budget:
  160738 raw / 189089 counted / 180000 limit. Do not claim the 5% headroom criterion passed.
- Frontend: 196 tests; type check and changed-module ESLint clean; production build passed.
- Research service: 115 tests covering lossless/budget/forecast/compatibility behavior;
  account bridge: 16 tests. Operator validation artifact records final counts and hashes.
- Real Chrome against an isolated frontend/API fixture: forecast and budget disclosure
  visible, no page errors, no mutation requests, no mobile horizontal overflow.

## Research ECA follow-up — 2026-09-21

The large final packet now counts 170325 under the unchanged 180000 limit (5.375% headroom), using a fenced-block parser fix plus actual account calibration. Full report/evidence bytes and claim-register inverse expansion verified over six real stage packets. Six live calibration probes (three per provider) request only a short acknowledgment; no existing completed research report is replaced. See ADR-011 for measurements, 18 named rules/guards and the separately measured Claude 240000 budget (default/ChatGPT 180000 unchanged).

Research tests: 140; account bridge tests: 18; frontend tests: 200. TypeScript and changed-module ESLint pass.

## Local hybrid retrieval — 2026-09-21

- New optional `hybrid-search` module: Turkish/English BM25, semantic retrieval,
  RRF, document diversity, authenticated local BGE reranking, and shared Ask retrieval.
- Ranking invariants: 9 tests. Module/search/Ask/parent regressions: 103 tests.
  Frontend: 201 tests. TypeScript, changed-file ESLint and production build pass.
- Real SurrealDB 2.6.5 + Ollama + pinned BGE integration: 30 synthetic multilingual
  queries, recall@10 30/30, top-1 29/30, MRR@10 0.9708. Fusion alone has top-1
  26/30 on the same set. These diagnostic fixtures informed tuning; they are not
  a held-out benchmark or a guarantee for real questions.
- Actual BM25/HNSW EXPLAIN plans checked. Notebook isolation, identical content
  in another notebook, edited/deleted exclusion and incremental updates checked.
- Production rollout: 20 original document hashes, 21 original source-vector hashes
  and 16 completed research-report hashes retained. Additive index: 1376 passages.
- Live browser checks: hybrid default, neural feedback, weak-match warning,
  original-document modal, per-module settings, all nine enabled, mobile bounds,
  no page errors. Only two read-only search POSTs; no live answer-generation run.
- Full Ask factual correctness and representative PDF/OCR ingestion are not
  claimed by these retrieval tests. Graph tests verify scope, shared retrieval,
  diagnostic forwarding and rejection of unknown local-document citations.
- Only API/frontend processes restarted. Database, worker, account/research/audio
  services and originals preserved. Prior image, code, module state and native
  database export retained for rollback; persistent build inputs updated.
