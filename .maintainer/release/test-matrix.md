# Coverage table

The risks this repository's releases keep checking, as a starting point for each release's
coverage table. The `release` skill instantiates it against the actual diff, keeps the
canonical validator and mandatory checks, and adds the risk-selected probes. The unit of
planning is the **risk**, not the feature: for each change ask *what can this break, and for
whom?* Use commands and selectors the repository supports; no secret values belong here.

The rows are the release's **Bucket A** (agent-run, automated now) and **Bucket C** (the
release owner, with real credentials); **Bucket B** (automatable with investment) follows the
table.

| Check | Change / risk | Real probe | Observable success | Prerequisites | Who / paid scope | Stage | Mandatory |
|---|---|---|---|---|---|---|---|
| Backend suite | any backend change | `[commands.validator]` | pytest, ruff and mypy exit 0 | `uv sync --extra dev`, `.env` | agent / free | pre-GO | yes |
| Frontend | any frontend change | `[commands.frontend]` | lint, tests and production build pass | `npm ci` in `frontend/` | agent / free | pre-GO | yes |
| Dev-DB leak | new or changed tests | per-table counts before and after the suite | no diff (at least `credential`) | live dev DB reachable | agent / free | pre-GO | yes |
| Smoke journey | any change to sources, chat, ask, transformations, podcasts, search | `smoke-e2e` skill on the dev stack, `[smoke].journey` | GO with every mandatory surface run | stack up, default chat + embedding models | agent / small paid (one chat, one embed, one podcast) | pre-GO | yes |
| Image gate | Dockerfile, deps, migrations, startup, nginx | `[artifacts.docker].gate` | fresh install and upgrade scenarios pass | Docker, previous tag pulled | agent / free | pre-GO | yes |
| Dependency audit | any dependency bump | Dependabot alerts + `npm audit` | no open highs, or explicit acceptance | — | agent / free | pre-GO | yes |
| Provider matrix | provider or Esperanto changes | connection test + discover-models + one chat per main provider | responses from every configured provider | real credentials | owner / paid | pre-GO | yes |
| Real podcast | podcast, TTS or prompt changes | one episode on a dense notebook | audio plays, transcript in the selected language | TTS credential | owner / paid | pre-GO | yes |
| UX tour | any UI change | ~10 min walk of every changed screen, light and dark | nothing broken or off-theme | dev stack | owner / free | pre-GO | yes |
| Pushed image | every release | `make release-stack TAG=<ver> [DUMP=…]` on the registry artifact | core flows work; credentials decrypt; opt-in runtimes gated | images pushed, dev-data copy | owner / free | post-trigger, pre-promotion | yes |
| Manifests | every release | `docker manifest inspect` per registry × variant | `['amd64','arm64']` for all four, then for `v1-latest*` | images pushed | agent / free | post-trigger | yes |

## Probe library (extend per release)

Regression-of-legitimate-use probes proven in v1.11.0 — adapt endpoints and values:

- Upload just under / just over the body cap → accepted / 413.
- Source ingestion of a `localhost` URL → accepted (self-hosted is legitimate);
  link-local or metadata URL → rejected with a clear 4xx.
- Frontend `/config` with clean vs. malformed `Host` → sane URL or fallback, never 5xx.
- SSE endpoints stream progressively (first byte ≪ total time via `curl -N -w`).
- CORS preflight with and without `CORS_ORIGINS` set.
- Every enum or allowlisted query param exercised with **each** valid value plus one
  invalid (`sort_by=title` 500'd while its siblings passed — test the whole surface).
- Oversized array inputs and unknown-provider payloads → clean 422, not 500.
- Anything an LLM or the UI writes through: verify the full path in a real browser, not just
  the API (the frontend dropped a field AND the API ignored null — only end-to-end caught it).

## Bucket B — automatable with investment

Decide per item with the owner: build it if it compounds for future releases and costs less
than the manual verification it replaces; otherwise verify manually this once and note it
here. The image gate graduated from here to `make release-test`. Standing candidates: new
end-to-end scenarios for the release's features; CI-ification of any probe that proved
valuable twice; anything the owner keeps verifying by hand.

## The project's inverse questions, checked on every release

- Does a protection break legitimate use? (SSRF guard vs. self-hosted Ollama on localhost;
  body-size cap vs. big uploads; Host validation vs. reverse proxies.)
- Does the abstraction hold parity across the provider matrix? (A feature that works only on
  one provider is a PDR-002 question, not a release note.)
- Does an upgrade on an existing volume survive? (Migrations, encrypted credentials, data.)
