# Gotchas

Fragile areas and lessons learned. Retros append here; a gotcha that holds up three times
graduates to the process document or to a test.

Release-specific gotchas (version bump hygiene, re-cut after a post-tag fix, RC stack ports,
local tags shadowing pushed images, opt-in runtime gating) have their home in
[`.github/RELEASE_PROCESS.md` → Known Gotchas](../.github/RELEASE_PROCESS.md#known-gotchas);
do not duplicate them here.

- **The backend suite runs against the live dev database** when a developer `.env` is loaded.
  Snapshot per-table counts (at least `credential`) before and after; a diff means a test
  leaks writes (48 leaked credentials caught in v1.12.0).
- **Search and Ask are global by design**: `POST /api/search` and `/api/search/ask/simple`
  have no `notebook_id`; Pydantic silently drops unknown fields, so a scoped-looking call
  is an unscoped one. Scoping to selected notebooks landed in #1331 — check the request
  models before assuming either behavior.
- **Provider aliases are mapped in more than one place.** `anthropic_compatible` is mapped to
  Esperanto's `anthropic` in `open_notebook/ai/models.py`; any resolver that bypasses
  `ModelManager.get_model()` (podcasts did, #1347) must use the shared helper or it breaks.
- **Async jobs need the worker.** Podcasts, embeddings and source processing queue forever
  without `make worker-start`; a "hangs" report with no worker log is usually this.
- **Containerized app + host services**: credentials pointing at Ollama or LM Studio on the
  host need `http://host.docker.internal:<port>`, not `localhost`.
- **Dev-machine ports may belong to other projects**: check who owns 3000/5055/8000 before
  starting or killing anything; the frontend runs fine on `PORT=3001 npm run dev`.
