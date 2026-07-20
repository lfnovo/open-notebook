# Test Matrix Template — change → risk → bucket

Instantiate against the real release diff. The unit of planning is the
**risk**, not the feature: for each change ask *what can this break, and for
whom?* Security hardening gets the inverse question too: *does the protection
break legitimate use?* (v1.11.0 examples: SSRF guard vs. self-hosted Ollama on
localhost; body-size cap vs. big uploads; Host validation vs. reverse proxies).

## Bucket A — automated now (run all of it)

Checklist design rule (v1.12.0 retro): before putting an error-path item on
the bucket-C checklist ("X unconfigured should show an error"), verify in the
provisioning code that it IS an error — transformation and tools defaults
deliberately fall back to the chat default (`open_notebook/ai/models.py`).

| Check | Command / tool |
|---|---|
| Backend suite | `uv run pytest tests/` |
| Lint & types | `ruff check .` · `uv run python -m mypy .` (both are required CI gates; mypy runs at 0 errors — `uv sync --extra dev` first if mypy is missing locally) |
| Frontend | `npm run lint` · `npm run test` · `npm run build` (run `npm ci` first if deps changed) |
| Full happy path | smoke-e2e agent on the local dev stack (API + Playwright UI) |
| Dependency audit | Dependabot alerts + `npm audit` |
| Targeted probes | see below — pick per matrix |

### Probe library (extend per release)

Regression-of-legitimate-use probes proven in v1.11.0 — adapt endpoints/values:

- Upload just under / just over the body cap → accepted / 413
- Source ingestion of a `localhost` URL → ACCEPTED (self-hosted is legitimate);
  link-local/metadata URL → rejected with a clear 4xx
- Frontend `/config` with clean vs. malformed `Host` → sane URL / fallback, never 5xx
- SSE endpoints stream progressively (first byte ≪ total time via `curl -N -w`)
- CORS preflight with and without `CORS_ORIGINS` set
- Every enum/allowlisted query param exercised with **each** valid value +
  one invalid (v1.11.0: `sort_by=title` 500'd while all siblings passed —
  test the whole surface, not one sample)
- Oversized array inputs and unknown-provider payloads → clean 422, not 500
- Anything an LLM or UI writes through: verify the full path in a real
  browser, not just the API (mirror-bug lesson: frontend dropped the field
  AND the API ignored null — only end-to-end caught it)

## Bucket B — automatable with investment (decide with the owner)

Standing candidates; the image gate graduated from here to `make release-test`:

- New end-to-end scenarios for this release's features
- CI-ification of any probe that proved valuable twice
- Anything the owner keeps having to verify by hand

Decision rule: build it if it compounds for future releases and costs < the
manual verification it replaces; otherwise verify manually this once and note
it here for next time.

## Bucket C — the release owner (start EARLY, in parallel)

- Provider connection tests with **real credentials** (prioritize providers
  whose code changed); one discover-models; one chat per main provider
- One podcast with real TTS on a dense notebook
- Visual/UX tour (~10 min) of every UI change in the release, plus dark mode
  sampling
- Phase 6: the pushed image via `make release-stack`

Deliver this as a concrete checklist with expected outcomes, tailored to what
the release actually touched and to the credentials the owner actually has
(`GET /api/credentials` tells you).
