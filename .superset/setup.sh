#!/usr/bin/env bash
# Superset setup for Open Notebook (this repo's code/UI, reusing the existing data).
# Idempotent: copies env files (for worktrees), wires ./data to the existing
# notebook_data, ensures the shared SurrealDB is running, and installs deps.
set -euo pipefail

ROOT_DIR="${SUPERSET_ROOT_PATH:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
WORKSPACE_DIR="${SUPERSET_WORKSPACE_PATH:-$(pwd)}"

# The official compose project keeps persistent data one level above the checkout:
#   <parent>/notebook_data  -> uploads + langgraph sqlite checkpoints (chat history)
#   <parent>/surreal_data   -> SurrealDB rocksdb files (the real database)
NOTEBOOK_DATA_DIR="${OPEN_NOTEBOOK_DATA_DIR:-$ROOT_DIR/../notebook_data}"
SURREAL_CONTAINER="${SURREAL_CONTAINER:-open-notebook-surrealdb-1}"

copy_env_file() {
  local name="$1"
  if [[ -f "$ROOT_DIR/$name" && "$ROOT_DIR" != "$WORKSPACE_DIR" ]]; then
    mkdir -p "$(dirname "$WORKSPACE_DIR/$name")"
    cp -f "$ROOT_DIR/$name" "$WORKSPACE_DIR/$name"
    echo "Copied $name into workspace"
  fi
}

# 1. Env files (root -> worktree). Required: .env (backend), frontend/.env.local.
copy_env_file ".env"
copy_env_file ".env.local"
copy_env_file "frontend/.env.local"

if [[ ! -f "$WORKSPACE_DIR/.env" ]]; then
  echo "WARNING: $WORKSPACE_DIR/.env is missing. The app cannot reach SurrealDB without it." >&2
fi

# 2. Reuse the existing notebook_data (chat checkpoints + uploaded files).
if [[ -d "$NOTEBOOK_DATA_DIR" ]]; then
  if [[ -L "$WORKSPACE_DIR/data" || ! -e "$WORKSPACE_DIR/data" ]]; then
    ln -sfn "$NOTEBOOK_DATA_DIR" "$WORKSPACE_DIR/data"
    echo "Linked ./data -> $NOTEBOOK_DATA_DIR"
  else
    echo "Note: ./data already exists as a real directory; leaving it as-is."
  fi
else
  echo "Note: $NOTEBOOK_DATA_DIR not found; the app will create a fresh ./data."
fi

# 3. Make sure the shared SurrealDB (the real data) is up. We never recreate it.
if command -v docker >/dev/null 2>&1; then
  docker start "$SURREAL_CONTAINER" >/dev/null 2>&1 || true
fi

# 4. Install dependencies (backend via uv, frontend via npm — this project uses npm).
echo "Installing backend dependencies (uv sync)..."
uv sync

echo "Installing frontend dependencies (npm ci)..."
( cd "$WORKSPACE_DIR/frontend" && npm ci )

echo "Superset setup complete for Open Notebook."
echo "  Web : http://localhost:47300"
echo "  API : http://localhost:47355"
echo "  DB  : SurrealDB on :8000 (shared container '$SURREAL_CONTAINER')"
