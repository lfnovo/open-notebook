# Mypy and Ruff Cleanup Summary

- Strengthened API client typings, normalizing JSON responses and request params.
- Added guardrails across routers/services for optional identifiers and literal-constrained settings payloads.
- Tightened domain models to avoid missing embedding models and enforce typed search helpers.
- Added package markers and scoped mypy ignores to UI/graph surfaces for manageable coverage.
- Verified with `uv run ruff check .` and `make lint` (mypy).
