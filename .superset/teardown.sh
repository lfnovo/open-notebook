#!/usr/bin/env bash
# Superset teardown for Open Notebook. Stops THIS app's local processes only.
# It deliberately leaves the SurrealDB container running so your data stays put
# (and other Superset apps / a later official-app restart are unaffected).
set -euo pipefail

WORKSPACE_DIR="${SUPERSET_WORKSPACE_PATH:-$(pwd)}"
cd "$WORKSPACE_DIR" 2>/dev/null || true

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

for port in "$WEB_PORT" "$API_PORT"; do
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "Stopping listener on port $port"
    kill $pids 2>/dev/null || true
  fi
done

pkill -f "surreal-commands-worker" 2>/dev/null || true
pkill -f "run_api.py" 2>/dev/null || true

echo "Stopped Open Notebook app processes. SurrealDB (:8000) left running."
echo "To bring the official app back: docker start open-notebook-open_notebook-1"
