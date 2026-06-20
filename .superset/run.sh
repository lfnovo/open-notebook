#!/usr/bin/env bash
# Superset one-click run for Open Notebook (this repo's API + worker + new UI),
# pointed at the EXISTING official SurrealDB so all current data carries over.
#
# What it does:
#   1. Kills any prior instances of THIS app (by port + process name).
#   2. Stops the official app container (open-notebook-open_notebook-1) so only this
#      app talks to the DB — but KEEPS the SurrealDB container (the data) running.
#   3. Starts API (FastAPI), worker (surreal-commands), and Web (Next.js) on unique ports.
set -euo pipefail

WORKSPACE_DIR="${SUPERSET_WORKSPACE_PATH:-$(pwd)}"
cd "$WORKSPACE_DIR"

# --- ports (unique, well outside the common ranges this machine already uses) ---
read_env_value() {
  local key="$1" file value
  for file in .env .env.local; do
    [[ -f "$file" ]] || continue
    value="$(awk -F= -v key="$key" '
      $0 !~ /^[[:space:]]*#/ && $1 ~ "^[[:space:]]*" key "[[:space:]]*$" {
        v=$0; sub(/^[^=]*=/, "", v); gsub(/^[[:space:]]+|[[:space:]]+$/, "", v);
        gsub(/^["'"'"']|["'"'"']$/, "", v); if (v != "") print v
      }' "$file" | tail -n 1)"
    [[ -n "$value" ]] && { echo "$value"; return; }
  done
}

API_PORT="${API_PORT:-$(read_env_value API_PORT)}"; API_PORT="${API_PORT:-47355}"
WEB_PORT="${WEB_PORT:-47300}"
SURREAL_CONTAINER="${SURREAL_CONTAINER:-open-notebook-surrealdb-1}"
OFFICIAL_APP_CONTAINER="${OFFICIAL_APP_CONTAINER:-open-notebook-open_notebook-1}"

kill_port() {
  local port="$1" pids
  [[ -z "$port" ]] && return
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "Stopping existing listener on port $port"
    kill $pids 2>/dev/null || true
    sleep 1
  fi
}

cleanup() { jobs -p | xargs -r kill 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# 1. Kill previous instances of THIS app (ports + stray processes).
kill_port "$API_PORT"
kill_port "$WEB_PORT"
pkill -f "surreal-commands-worker" 2>/dev/null || true
pkill -f "run_api.py" 2>/dev/null || true

# 2. Keep the data DB up; retire the official app so only this code serves the data.
if command -v docker >/dev/null 2>&1; then
  docker start "$SURREAL_CONTAINER" >/dev/null 2>&1 || true
  if docker ps --format '{{.Names}}' | grep -qx "$OFFICIAL_APP_CONTAINER"; then
    echo "Stopping official app container '$OFFICIAL_APP_CONTAINER' (keeping SurrealDB)..."
    docker stop "$OFFICIAL_APP_CONTAINER" >/dev/null 2>&1 || true
  fi
fi

# Wait for SurrealDB on :8000 (it holds all the data; nothing works without it).
echo "Waiting for SurrealDB on :8000..."
for _ in $(seq 1 30); do
  if (exec 3<>/dev/tcp/127.0.0.1/8000) 2>/dev/null; then exec 3>&- 3<&-; echo "SurrealDB is up."; break; fi
  sleep 1
done

# 3. Start the stack. The browser hits the API directly (CORS is open in dev).
export API_HOST="127.0.0.1"
export API_PORT
export NEXT_PUBLIC_API_URL="http://localhost:${API_PORT}"
export INTERNAL_API_URL="http://localhost:${API_PORT}"

echo "Starting API on :$API_PORT ..."
uv run --env-file .env run_api.py &

echo "Starting background worker ..."
uv run --env-file .env surreal-commands-worker --import-modules commands &

echo "Starting Web on :$WEB_PORT ..."
( cd frontend && PORT="$WEB_PORT" npm run dev ) &

echo ""
echo "Open Notebook is starting:"
echo "  Web      : http://localhost:$WEB_PORT"
echo "  API      : http://localhost:$API_PORT"
echo "  API docs : http://localhost:$API_PORT/docs"
echo "  Database : SurrealDB :8000 (shared — your existing data)"
echo ""

wait
