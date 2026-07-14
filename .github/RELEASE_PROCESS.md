# Release Process

Open Notebook uses a flow-driven release process. Work moves from `ready`
issues into pull requests, pull requests merge to `main`, and maintainers cut a
version when the branch has enough validated change to ship.

This document covers both the **mechanics** (how to cut, build and publish) and
the **confidence process** (how we know a release is good before users get it).
It was redesigned during the v1.11.0 release ([ADR-005](../docs/7-DEVELOPMENT/decisions/ADR-005-release-confidence-process.md)).

## Release Model

- Patch releases ship backwards-compatible fixes.
- Minor releases ship backwards-compatible features and improvements.
- Major releases are planned with a milestone when they include breaking
  changes or migrations that need user coordination.
- Use the `in-dev-build` label for changes available in development images and
  `released` for shipped work. (The `released` label was recreated during
  v1.12.0 — it had been dropped from the curated label taxonomy while this
  document still required it. If a label this document references is missing,
  recreate it rather than skipping the step.)

## Normal Flow

1. Triage issues into `ready` once the scope and design are clear.
2. Implement each change in a focused pull request linked to the approved issue.
3. Merge the pull request after review and required checks pass.
4. Let the development build publish the `v1-dev` image from `main`.
5. Cut a stable release when `main` has a coherent set of changes ready for
   users — following the confidence process below.

## The Confidence Process

Releases keep getting bigger; ad-hoc verification does not scale. Before
cutting, run this sequence:

### 0. Changelog audit

Diff `git log <last-tag>..main` against the `[Unreleased]` section of the
CHANGELOG. Every merged PR must be represented (entries reference the issue
number when one exists, the PR number otherwise). The changelog is the input
for both the test plan and the release notes — close the gaps first, via PR.

### 1. Risk-based test matrix

Build a matrix from the actual release diff: each change → what it can break
and for whom → which bucket tests it. Pay special attention to
**"does the protection break legitimate use?"** for security changes (e.g. an
SSRF guard vs. self-hosted Ollama on localhost) and to anything a reverse
proxy, an upgrade, or a big upload would exercise.

Buckets:

- **A — automated, high confidence, run now**: full backend suite, frontend
  lint/tests/production build, the smoke-e2e agent (full API happy path + UI
  verification), targeted regression probes for the release's specific risks,
  dependency audit.
- **B — automatable with investment**: decide per item whether to build the
  muscle now (it compounds: the image gate below started as a bucket-B item)
  or verify manually this once.
- **C — needs the release owner**: real provider credentials, real TTS podcast
  generation, visual/UX judgment, and the final check of the pushed image.

### 2. The image gate — test the artifact, not the repo

A green suite on `main` is not a working image. Run:

```bash
make docker-build-local          # builds <version> + local tags
make release-test TAG=<new> OLD_TAG=<previous>
```

This runs two scenarios against real containers (`scripts/release-test/`):

- **Fresh install**: empty DB → migrations on boot → in-image worker processes
  a source → API/frontend/nginx-proxied checks.
- **Upgrade**: boot the *published* previous image, seed data, swap to the new
  image on the same volume → migrations apply, data survives.

Caveat: `docker-build-local` tags with the current `pyproject.toml` version —
`docker pull` the genuine previous tag before the upgrade test so you are not
comparing the new build against itself.

### 3. Fix loop with a re-test policy

Findings become focused PRs through the normal review flow. After each merge:
the cheap suite always re-runs; smoke/image gates re-run only if the fix
touches what they cover; manual verification is not repeated unless the fix
touches what was manually verified. Pre-existing bugs found along the way that
are not release regressions become backlog issues instead of scope creep.

## Cutting A Stable Release

1. Confirm `main` is green and the confidence process above has run.
2. Open the **cut PR**: bump `pyproject.toml`, date the `[Unreleased]` section
   as `[<version>] - <date>`.
3. After merge: `make tag`.
4. Build and push version images **via CI** (it holds the registry
   credentials): trigger the *Build and Release* workflow with
   `push_latest=false`. Local `make docker-push` also works but requires
   `docker login` on both registries.
5. **Verify the pushed image** (bucket C, final gate): run it locally with
   `make release-stack TAG=<version> [DUMP=<dev-data-dump>]` — a browsable,
   isolated stack, optionally with a copy of real data — and walk the core
   flows in the browser.
6. Publish the GitHub release. A non-prerelease publication triggers the
   workflow again and pushes the `v1-latest` tags automatically.
7. Verify the `v1-latest` manifests on Docker Hub and GHCR (both arches, both
   variants), and mark shipped issues with `released`.

## Communication

Release notes follow this structure (see v1.11.0 as the reference):

1. One-line verdict + upgrade recommendation.
2. Sections: Security, Features, Performance, Notable fixes.
3. **Behavior changes for self-hosters** — anything that can require a config
   tweak on upgrade gets an explicit callout.
4. **Thanks** — credit every contributor by handle with what they shipped
   (collect via `git log <last-tag>..<tag>` + `gh pr view` for handles), plus
   the issue reporters collectively. Never skip this section.

Announce on Discord after `v1-latest` is live.

## Retro

Close every release by asking: what should improve in this process? Apply the
accepted improvements immediately — update this document, the scripts under
`scripts/release-test/`, and the decision log while the context is fresh.

## Docker Image Publishing (reference)

| Command | What it does | Updates latest? |
|---------|--------------|-----------------|
| `make docker-build-local` | Build for current platform only (tags `<version>` + `local`) | No registry push |
| CI *Build and Release* (`push_latest=false`) | Push version tags via CI credentials | ❌ No |
| GitHub release published (non-prerelease) | CI pushes version + `v1-latest` | ✅ Yes |
| `make docker-push` / `docker-push-latest` | Local equivalents (need `docker login`) | ❌ / ✅ |
| `make tag` | Create and push a git tag matching `pyproject.toml` | — |

- **Platforms:** `linux/amd64`, `linux/arm64`
- **Registries:** Docker Hub + GitHub Container Registry
- **Image variants:** regular + single-container (`-single`). Both are built
  from the same `Dockerfile`: regular is the default/`runtime` target, single
  is `--target single`
- **Version source:** `pyproject.toml`
- Build issues: `docker builder prune`, then `make docker-buildx-reset`

## Known Gotchas

- **RC stack on non-default ports needs `API_URL`** or the browser talks to
  `host:5055` — on a dev machine that is the development API (data crossover).
  `rc-stack.sh` sets it; remember this for any custom setup.
- **Containerized app + host services**: credentials pointing at local
  services (Ollama, LM Studio) need `http://host.docker.internal:<port>`.
- **SurrealDB import**: `OVERWRITE` goes after the type keyword
  (`DEFINE FIELD OVERWRITE …`), and the exporter can leak a log line into the
  dump — `rc-stack.sh` handles both.
- **Multiple local SurrealDB instances**: check which one the dev `.env`
  actually points at (`SURREAL_URL`) before exporting data.
- **Dev-machine ports may belong to other projects**: check who owns
  3000/5055/8000 (`lsof -nP -iTCP:<port> -sTCP:LISTEN` + the process cwd)
  before starting or killing anything. The frontend runs fine on an alternate
  port for smoke testing (`PORT=3001 npm run dev`) — pass the URL to the
  smoke agent.
- **Manual error-path checklist items must be validated against the code
  first**: some "missing configuration" scenarios are deliberate fallbacks,
  not errors (e.g. transformation and tools defaults fall back to the chat
  default). Confirm the expected behavior in the provisioning code before
  putting "should show an error" on the bucket-C checklist.
- **The test suite runs against the live dev database** when a developer
  `.env` is loaded. During bucket A, snapshot record counts per table before
  and after the suite (e.g. credentials count) — a diff means a test is
  leaking writes (this caught 48 leaked `Test` credentials in v1.12.0).
- **A local `docker-build-local` tag shadows the pushed image.** Both are
  `lfnovo/open_notebook:<ver>`, so Phase 6 could verify your own local build
  instead of the registry artifact. `rc-stack.sh up` now `docker pull`s the tag
  by default; if you boot the image any other way, pull first (v1.13.0 lesson).
- **Judge opt-in runtime gating on a clean image, not the dev venv.** A dev
  venv may have `crawl4ai`/`docling` installed out-of-band (not via the opt-in
  flag), so `GET /api/capabilities` reports them available and the UI enables
  the engines — which does NOT reflect the lean default image. Verify the
  gating on the RC stack (fresh pushed image) where the runtimes are genuinely
  absent until enabled. To exercise the real install path with your data, use
  `make release-stack TAG=<ver> DUMP=<dump>` plus `rc-stack.sh ... --with-runtimes`
  (sets `OPEN_NOTEBOOK_ENABLE_DOCLING`/`_CRAWL4AI`; first boot is slow) (v1.13.0 lesson).
