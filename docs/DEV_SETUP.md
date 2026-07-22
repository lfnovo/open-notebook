# Development setup (verified build)

The exact, reproducible steps to get a clean build of this fork running from
scratch, plus the baseline numbers and known-failing tests recorded at the
`upstream-base` fork point.

Every command below was executed and verified on 2026-07-21. Where a step
differs on Windows, that is called out — it is not theoretical, it was hit.

> This document is the WP0 build-reproducibility deliverable. For deeper
> background on *why* the stack is shaped this way, see
> [docs/7-DEVELOPMENT/development-setup.md](7-DEVELOPMENT/development-setup.md)
> and [architecture.md](7-DEVELOPMENT/architecture.md). This file is the
> "make it run" checklist.

---

## 1. Prerequisites

| Tool | Verified version | Notes |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | 0.8.22 | Manages the Python toolchain; you do **not** need a matching system Python |
| Python | 3.12.11 (installed by uv) | `pyproject.toml` requires `>=3.11,<3.13`. A system Python 3.13 is fine — uv installs and pins 3.12 itself |
| Node.js | 24.18.0 | CI uses 22; both build |
| npm | 11.16.0 | |
| Docker | 29.6.1 | Only used to run SurrealDB |

Verify:

```bash
uv --version && node --version && npm --version && docker --version
```

---

## 2. Ports and startup order

Three tiers plus a worker. **Start them in this order** — each depends on the
one below it.

| Order | Tier | Port | Consequence if skipped |
|---|---|---|---|
| 1 | SurrealDB | 8000 | API fails to start |
| 2 | FastAPI | 5055 | Frontend has no data; migrations run here on startup |
| 3 | Worker | — | Podcasts, embeddings and source processing queue **silently forever** |
| 4 | Frontend | 3000 | No UI |

---

## 3. Install dependencies

```bash
# Backend (from repo root) — creates .venv and installs the dev group too
uv sync

# Frontend
cd frontend && npm ci && cd ..
```

---

## 4. Create the `.env` file

**Required.** `make api` and the worker both run with `--env-file .env` and
fail outright if it does not exist. `.env` is gitignored — never commit it.

```bash
cat > .env <<'EOF'
SURREAL_URL=ws://127.0.0.1:8000/rpc
SURREAL_USER=root
SURREAL_PASSWORD=root
SURREAL_NAMESPACE=open_notebook
SURREAL_DATABASE=open_notebook
OPEN_NOTEBOOK_ENCRYPTION_KEY=dev-only-local-key-not-for-production
EOF
```

**Use `127.0.0.1`, not `localhost`, in `SURREAL_URL`.** The compose file binds
SurrealDB to `127.0.0.1:8000` (IPv4). On Windows, `localhost` resolves to IPv6
`::1` first, which nothing is listening on, so every DB connection wastes ~2s
failing over to IPv4 before it succeeds. The app still runs, but the 2-second
database health check in `/api/config` times out and the UI reports "database
offline" even though it isn't — and every query silently pays the tax.
`127.0.0.1` forces IPv4 and connects in ~50 ms. It is also correct on Linux, so
there is no reason to prefer `localhost` here.

`OPEN_NOTEBOOK_ENCRYPTION_KEY` is required for credential storage and has no
default. The value above is fine for local development only — production keys
are generated per deployment (see WP1).

No AI provider keys are needed to boot the stack. They are only required to
actually run models, and are configured in the UI (encrypted at rest).

---

## 5. Start the stack

Run each in its own terminal.

```bash
# 1. SurrealDB (data persists in ./surreal_data)
docker compose up -d surrealdb

# 2. API — schema migrations run automatically on startup
uv run --env-file .env run_api.py

# 3. Worker
#    On Windows, PYTHONIOENCODING=utf-8 is REQUIRED — see Troubleshooting.
uv run --env-file .env surreal-commands-worker --import-modules commands --max-tasks 5

# 4. Frontend
cd frontend && npm run dev
```

Then open http://localhost:3000. API docs are at http://localhost:5055/docs.

> **Do not use `make start-all`.** It references `docker-compose.dev.yml`,
> which does not exist in this repo, so its database step fails. Its
> `stop-all` counterpart also relies on `pkill`, which is not available on
> Windows. Use the individual commands above. (`make database`, `make api`
> and `make worker-start` individually are fine.)

### Verify it is actually up

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5055/health   # expect 200
curl -s http://localhost:5055/api/notebooks                             # expect [] on a fresh DB
```

A `200` plus a valid JSON body from `/api/notebooks` confirms the API booted,
connected to SurrealDB, and ran its migrations.

---

## 6. Build, lint, test

```bash
# Backend
uv run pytest tests/                      # test suite
uv run ruff check .                       # lint
uv run python -m mypy .                   # typecheck
uv run python scripts/check_licenses.py   # GPL/AGPL drift guard

# Frontend (inside frontend/)
npm run test        # vitest
npm run lint        # eslint
npm run build       # production build
```

---

## 7. Baseline at the fork point

Recorded on 2026-07-21 at tag `upstream-base` (+ the WP0 test additions), so
later work packages can be compared against it.

### Coverage

| Suite | Metric | Baseline |
|---|---|---|
| Backend (`open_notebook` + `api`), upstream tests only | statements | 55% (4388/8018 covered) |
| Backend, **including the WP0 characterization tests** | statements | **56%** (4487/8018 covered) |
| Frontend | statements | **35.79%** (615/1718) |
| Frontend | lines | **36.46%** (601/1648) |
| Frontend | branches | **43.42%** (578/1331) |
| Frontend | functions | **31.29%** (169/540) |

Reproduce:

```bash
uv run pytest tests/ --cov=open_notebook --cov=api --cov-report=term
cd frontend && npm run test:coverage
```

**Ratchet rule:** coverage may only go up. The number to beat is the
**56% / 35.79%** row — a work package that lowers either needs an explicit
justification in its PR.

> Frontend coverage must be measured with `src/lib/locales/index.test.ts`
> excluded on Windows, because that test fails on a timeout there (below) and
> vitest suppresses the coverage report when any test fails:
> `npx vitest run --coverage --exclude "**/locales/index.test.ts"`.
> On Linux CI the plain `npm run test:coverage` reports fine.

### Test counts

| Suite | Result at baseline |
|---|---|
| Backend | 632 passed, 5 failed (Windows-only, see below) |
| Backend + WP0 additions | 732 passed, 5 failed (Windows-only) |
| Frontend | 139 passed, 1 failed (Windows-only, see below) |

---

## 8. Known-failing tests on Windows

These **six** failures are pre-existing at `upstream-base` and are caused by
the tests' own platform assumptions, not by broken application code. **They
were deliberately not "fixed"** — WP0 forbids changing application behavior.

All six are **confirmed passing on Linux CI**, not merely assumed to: the
first CI run of this branch reported `737 passed` for the backend (the 732
that pass on Windows, plus these 5) and `23 passed (23)` test files for the
frontend (the 22 that pass on Windows, plus the locale test).

| Test | Why it fails on Windows |
|---|---|
| `test_podcast_path.py::test_path_structure` | Asserts POSIX `/`-separated path parts |
| `test_podcast_path.py::test_path_works_on_posix` | Same — the name says it |
| `test_podcast_audio_paths.py::test_file_uri_under_root_becomes_relative` | `file://` URI parsing does not round-trip with a `C:\` drive letter |
| `test_podcast_audio_containment.py::test_symlink_escape_is_rejected` | Symlink creation needs elevated privileges |
| `test_proxy.py::test_merges_both_case_variants` | Windows environment variables are case-**insensitive**, so `no_proxy` and `NO_PROXY` are literally the same variable — the test's premise cannot hold |
| `frontend: locales/index.test.ts` (unused-key detection) | Recursively walks and greps the whole `src/` tree; takes ~50s on NTFS against a hard-coded 30s timeout |

To run the backend suite excluding them:

```bash
uv run pytest tests/ --deselect tests/test_podcast_path.py --deselect tests/test_proxy.py::test_merges_both_case_variants --deselect tests/test_podcast_audio_paths.py::TestToRelativeAudioPath::test_file_uri_under_root_becomes_relative --deselect tests/test_podcast_audio_containment.py::TestResolveContainedAudioPath::test_symlink_escape_is_rejected
```

---

## 9. Troubleshooting

**Worker exits immediately on Windows with `'charmap' codec can't encode character '✅'`**

`surreal-commands` prints an emoji to stdout, which the default cp1252 console
codepage cannot encode. Without this the worker dies at startup and every
background job queues forever with no visible error. Fix:

```bash
PYTHONIOENCODING=utf-8 uv run --env-file .env surreal-commands-worker --import-modules commands --max-tasks 5
```

Set `PYTHONIOENCODING=utf-8` in your shell profile to avoid repeating it.

**`make api` / worker fails with a missing `.env`**

Both run with `--env-file .env`. Create it (step 4). It is gitignored.

**API starts but every request 500s on the database**

SurrealDB is not up, or `SURREAL_URL` points at the wrong host. From the host
machine use `ws://127.0.0.1:8000/rpc`; from inside a compose service use
`ws://surrealdb:8000/rpc`.

**UI says "database offline" but the DB is up and migrations ran**

The classic symptom of `SURREAL_URL=ws://localhost:8000/rpc` on Windows. The API
connects at startup (slowly — watch for a multi-second gap before "Current
database version"), but the 2-second health check in `/api/config` times out on
the IPv6→IPv4 failover and reports the database offline. Change `localhost` to
`127.0.0.1` in `.env` (step 4) and restart the API and worker. Verify with:

```bash
# ~50 ms healthy; ~2000 ms means you are still on localhost
uv run --env-file .env python -c "import asyncio,time; from open_notebook.database.repository import repo_query; t=time.perf_counter(); asyncio.run(repo_query('RETURN 1')); print(f'{(time.perf_counter()-t)*1000:.0f} ms')"
```

**Background jobs never finish**

The worker is not running. This is the single most common local-setup mistake
— the API accepts the job and returns success either way.

---

## 10. Fork hygiene

```
origin    https://github.com/HariHaranDFX/open-notebook.git   (this fork)
upstream  https://github.com/lfnovo/open-notebook.git         (upstream)
```

The tag **`upstream-base`** marks the fork point — upstream `main` at
`30c7e2a` (v1.14.0). Everything at or below that tag is unmodified upstream
code; commercialization work begins above it.

```bash
git fetch upstream          # pull upstream history
git diff upstream-base      # everything this fork has changed
```

> The master plan names v1.10.0 as the base; the actual fork point is v1.14.0.
> Treat this file and the tag as ground truth.
