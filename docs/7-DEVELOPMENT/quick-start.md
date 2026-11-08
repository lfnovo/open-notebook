# Quick Start (Development)

This page has been merged into **[Development Setup](development-setup.md)**, which is the single, maintained guide for running Open Notebook from source.

The short version:

```bash
uv sync && (cd frontend && npm install)
cp .env.example .env   # then set SURREAL_URL=ws://localhost:8000/rpc and OPEN_NOTEBOOK_ENCRYPTION_KEY
make start-all         # SurrealDB, API, worker, frontend
```

See [Development Setup](development-setup.md) for what each step does and how to troubleshoot it.
