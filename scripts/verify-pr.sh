#!/bin/sh
# Run linting, tests, and type checking for PR verification.
# Usage: ./scripts/verify-pr.sh   (or: sh scripts/verify-pr.sh)
set -e
cd "$(dirname "$0")/.."
echo "=== Ruff ==="
uv run ruff check . --fix
echo "=== Pytest ==="
uv run pytest tests/ --tb=short -q
echo "=== Mypy ==="
uv run python -m mypy .
echo "=== All checks passed ==="
