# From Source Installation

Clone the repository and run the full stack locally. **For developers and contributors.**

The fastest path is the cross-platform **dev launcher** ([`dev.py`](../../dev.py)), which brings up the database, API, background worker, and frontend in one command with combined logs — the from-source equivalent of `docker compose up`.

## Prerequisites

- **uv** (Python package manager) — install: <https://docs.astral.sh/uv/getting-started/installation/>
  - uv automatically provisions a compatible Python (the project requires **3.11 or 3.12**, *not* 3.13), so you don't need a system Python in that range.
- **Node.js 18+** — [Download](https://nodejs.org/) (ships with `npm`)
- **Docker** (for SurrealDB) — [Download](https://docker.com/)
- **Git** — [Download](https://git-scm.com/)

> **`make` is not required.** This fork is driven by the `dev.*` launcher scripts, not the Makefile. (Several Makefile targets such as `make start-all` / `make dev` reference compose files that don't exist in this fork.)

---

## Quick Start — one command (recommended)

### 1. Clone

```bash
git clone https://github.com/stefanini-applications/sai-notebook.git
cd sai-notebook
```

### 2. Run the launcher

| Platform | Command |
|----------|---------|
| **Windows** | `dev.bat`  (or `.\dev.ps1`, or `uv run python dev.py`) |
| **Linux / macOS** | `./dev.sh`  (or `uv run python dev.py`) |

That's it. The launcher will:

1. Create `.env` from `.env.example` on first run (pointing `SURREAL_URL` at `localhost`).
2. `uv sync` and ensure the `libmagic` binding for file uploads (`python-magic-bin` on Windows, `python-magic` elsewhere).
3. Install frontend dependencies if `frontend/node_modules` is missing.
4. Start **SurrealDB** (Docker), then the **API**, **worker**, and **frontend**.
5. Stream every service's logs into one terminal, prefixed `[db]` / `[api]` / `[worker]` / `[frontend]`.

When it prints the **"SAI Notebook is up"** banner, open <http://localhost:3000>.

**Press `Ctrl+C` once** to stop everything (processes + the SurrealDB container).

### Useful flags

```bash
# Skip the uv sync / npm install dependency checks (faster restarts)
dev.bat --skip-sync          # Windows
./dev.sh --skip-sync         # Linux/macOS

# Force-stop anything left running (e.g. after an unclean exit)
dev.bat stop                 # Windows
./dev.sh stop                # Linux/macOS
```

> Per-service logs are also written to `.dev-logs/` (git-ignored).

---

## Access

- **Frontend**: <http://localhost:3000>
- **API Docs**: <http://localhost:5055/docs>
- **Database**: SurrealDB on `localhost:8000`

---

## Hot reload

The launcher is configured for fast iteration:

| Service | Hot reload | Watches |
|---------|-----------|---------|
| **Frontend** | ✅ Turbopack HMR | `frontend/` |
| **API** | ✅ uvicorn `--reload` | `api/`, `open_notebook/` |
| **Worker** | ✅ via `watchfiles` | `commands/`, `open_notebook/` |

Editing a React component, an API route, or a command/embedding module restarts only the affected service. (API reload is intentionally scoped to backend dirs so frontend rebuilds don't bounce it.)

---

## Configure an AI provider

The stack runs without a provider, but you need one to generate notes, embeddings, or podcasts:

1. Open <http://localhost:3000> → **Settings** → **API Keys**
2. **Add Credential** → select your provider → paste API key
3. **Save** → **Test Connection**
4. **Discover Models** → **Register Models**

---

## Manual setup (what the launcher does)

Prefer separate terminals, or want to understand the moving parts? Run these by hand.

### 1. Install Python dependencies

```bash
uv sync
```

### 2. Install the libmagic binding (file-type detection on uploads)

`content-core` needs `libmagic`. This is **not** a project dependency, so `uv sync` removes it on every run — reinstall it after syncing.

```bash
# Windows (bundles the libmagic DLL)
uv pip install python-magic-bin

# Linux
uv pip install python-magic && sudo apt-get install -y libmagic1

# macOS
uv pip install python-magic && brew install libmagic
```

#### Optional: Conda

If you manage environments with Conda:

```bash
conda create -n sai-notebook python=3.12 -y
conda activate sai-notebook
conda install -c conda-forge uv nodejs -y
uv sync
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```bash
OPEN_NOTEBOOK_ENCRYPTION_KEY=my-secret-key

# IMPORTANT: running the API on the host (not in Docker) means SurrealDB is
# reached via localhost, NOT the docker-compose service hostname "surrealdb".
SURREAL_URL=ws://localhost:8000/rpc
```

### 4. Start SurrealDB (Terminal 1)

```bash
docker compose up -d surrealdb
```

### 5. Start the API (Terminal 2)

```bash
uv run --env-file .env uvicorn api.main:app \
  --host 127.0.0.1 --port 5055 \
  --reload --reload-dir api --reload-dir open_notebook
```

Migrations run automatically on startup — watch for `Migrations completed successfully`.

### 6. Start the worker (Terminal 3)

**Don't skip this** — the worker processes embeddings (semantic search) and podcast jobs. Without it those features silently never complete.

```bash
# With hot reload (restarts on .py changes):
uv run --env-file .env watchfiles --filter python \
  'surreal-commands-worker --import-modules commands' commands open_notebook

# Or plain (no reload):
uv run --env-file .env surreal-commands-worker --import-modules commands
```

### 7. Start the frontend (Terminal 4)

```bash
cd frontend && npm install && npm run dev
```

---

## Development Workflow

### Code Quality

```bash
# Format and lint Python
ruff check . --fix

# Type checking
uv run python -m mypy .
```

### Run Tests

```bash
uv run pytest tests/
```

---

## Troubleshooting

### Port 5055 / 3000 / 8000 already in use

You likely have services still running. Stop them:

```bash
dev.bat stop      # Windows
./dev.sh stop     # Linux/macOS
```

### Database connection errors / "Connection refused"

- Confirm SurrealDB is up: `docker compose ps surrealdb`
- Confirm `.env` has `SURREAL_URL=ws://localhost:8000/rpc` (the `surrealdb` hostname only resolves *inside* the Docker network).
- View logs: `docker logs sai-notebook-surrealdb-1`

### File uploads fail with a `libmagic` / `magic` error

The `libmagic` binding wasn't installed (or `uv sync` stripped it). Reinstall per [step 2](#2-install-the-libmagic-binding-file-type-detection-on-uploads). The launcher does this automatically.

### Wrong Python version

The project requires **3.11–3.12**. Let uv provide it:

```bash
uv sync --python 3.12
```

### npm: command not found

Install Node.js 18+ from <https://nodejs.org/>.

---

## Next Steps

1. [Development Setup](../7-DEVELOPMENT/development-setup.md)
2. [Contributing Guide](../7-DEVELOPMENT/contributing.md)

---

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/stefanini-applications/sai-notebook/issues)
- **Discord**: [Community](https://discord.gg/37XJPXfz2w)
