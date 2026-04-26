# CLAUDE.md

> Engineering guide for working in this repository with Claude Code.
>
> The canonical deep-dive guide (architecture, three-tier diagram, quirks,
> common tasks, error handling, podcast pipeline, etc.) lives at
> **[`open_notebook/CLAUDE.md`](open_notebook/CLAUDE.md)** — auto-imported below
> so this file always reflects the single source of truth.

@open_notebook/CLAUDE.md

---

## Repo-Root Quickstart

These commands are scoped to the repository root and are **not** duplicated in
the imported guide.

### Install

```bash
uv sync --all-extras                  # Python backend deps
cd frontend && npm install            # Frontend deps
```

### Run

```bash
# API server
uv run uvicorn api.main:app --host 0.0.0.0 --port 5055 --reload

# Frontend dev server
cd frontend && npm run dev

# Background command worker (surreal-commands)
uv run surreal-commands worker
```

### Test

```bash
uv run pytest tests/                  # All Python tests
cd frontend && npm run test           # Frontend tests
```

---

## Top-Level Documentation

- **[README.md](README.md)** — project overview, features, quick start
- **[CONFIGURATION.md](CONFIGURATION.md)** — environment variables & model configuration
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — contribution guidelines
- **[MAINTAINER_GUIDE.md](MAINTAINER_GUIDE.md)** — release & maintenance procedures
- **<https://open-notebook.ai>** — full user & deployment documentation
