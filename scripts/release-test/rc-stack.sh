#!/bin/bash
# Browsable release-candidate stack on the local machine: runs a pushed (or
# local) image, optionally with a COPY of your dev data, for manual release
# verification without touching the dev environment.
#
# Usage:
#   rc-stack.sh up <tag> [dump.surql] [--with-runtimes]   # start (imports the dump if given)
#   rc-stack.sh down <tag>                                 # stop and remove everything
#
# --with-runtimes enables the opt-in heavy engines (Docling + Crawl4AI) so the
# published image installs them on first boot — lets you exercise the real
# opt-in path with real data (the first boot then takes several minutes).
#
# `up` docker-pulls the pushed image by default, so you always verify the
# registry artifact and not a same-named local build shadowing it. A local-only
# tag (no registry push) still works — the pull failure is a warning, not fatal.
#
# To produce a data copy from a running dev SurrealDB (originals untouched):
#   docker exec <surreal-container> /surreal export \
#     --conn http://localhost:8000 --user root --pass root \
#     --ns open_notebook --db <your-db> /dev/stdout > /tmp/dev-dump.surql
#
# Ports: UI http://localhost:18502 · via nginx http://localhost:18080 · API 15055
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$DIR/../.." && pwd)"
TAG="${2:?usage: rc-stack.sh <up|down> <tag> [dump.surql] [--with-runtimes]}"

# Optional flag can appear anywhere after the tag; the remaining positional is the dump.
WITH_RUNTIMES=""
DUMP=""
for arg in "${@:3}"; do
  if [ "$arg" = "--with-runtimes" ]; then WITH_RUNTIMES="true"; else DUMP="$arg"; fi
done
RC_DATA=/tmp/onrel-rc-data

# Reuse the dev encryption key so copied credentials decrypt; the DB name must
# match the one the dump came from (defaults to the dev .env's database).
KEY=$(grep '^OPEN_NOTEBOOK_ENCRYPTION_KEY' "$REPO/.env" 2>/dev/null | cut -d= -f2- | tr -d '"' || true)
DB=$(grep '^SURREAL_DATABASE' "$REPO/.env" 2>/dev/null | cut -d= -f2- | tr -d '"' || true)

compose() {
  APP_IMAGE="lfnovo/open_notebook:$TAG" DATA_DIR="$RC_DATA" \
  API_PORT=15055 FE_PORT=18502 PROXY_PORT=18080 \
  RC_API_URL="http://localhost:15055" \
  RC_ENCRYPTION_KEY="${KEY:-release-test-key}" RC_SURREAL_DB="${DB:-open_notebook}" \
  RC_ENABLE_DOCLING="${WITH_RUNTIMES:+true}" RC_ENABLE_CRAWL4AI="${WITH_RUNTIMES:+true}" \
  docker compose -p onrelrc -f "$DIR/docker-compose.release-test.yml" "$@"
}

case "$1" in
  down)
    compose down -v
    rm -rf "$RC_DATA"
    echo "RC stack removed."
    ;;
  up)
    # Pull the pushed image so a same-named local build can't shadow the
    # registry artifact we mean to verify (non-fatal for local-only tags).
    docker pull "lfnovo/open_notebook:$TAG" || \
      echo "WARNING: could not pull lfnovo/open_notebook:$TAG — using the local image if present."
    [ -n "$WITH_RUNTIMES" ] && echo "Opt-in runtimes ENABLED (Docling + Crawl4AI) — first boot will be slow."
    compose down -v >/dev/null 2>&1 || true
    rm -rf "$RC_DATA"; mkdir -p "$RC_DATA/surreal" "$RC_DATA/notebook"
    if [ -n "$DUMP" ]; then
      # SurrealDB import quirks, learned in production:
      # - OVERWRITE goes AFTER the type keyword (DEFINE FIELD OVERWRITE ...),
      #   needed because RELATION tables auto-define in/out fields
      # - the exporter can leak its own log line into the dump (starts with ESC)
      sed -E $'/^\x1b/d; s/^DEFINE (TABLE|FIELD|INDEX|ANALYZER|FUNCTION|EVENT|PARAM|ACCESS) /DEFINE \\1 OVERWRITE /' "$DUMP" > "$RC_DATA/surreal/dump.surql"
    fi
    compose up -d surrealdb
    sleep 4
    if [ -n "$DUMP" ]; then
      docker exec onrelrc-surrealdb-1 /surreal import --conn http://localhost:8000 \
        --user root --pass root --ns open_notebook --db "${DB:-open_notebook}" \
        /mydata/dump.surql
    fi
    compose up -d
    echo "Waiting for API..."
    for i in $(seq 1 30); do
      curl -sf -m 5 -o /dev/null http://localhost:15055/docs && break
      sleep 5
    done
    NB=$(curl -s http://localhost:15055/api/notebooks | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "?")
    echo "RC stack up — image lfnovo/open_notebook:$TAG"
    echo "  UI:        http://localhost:18502"
    echo "  via nginx: http://localhost:18080"
    echo "  API:       http://localhost:15055"
    echo "  notebooks: $NB"
    echo
    echo "NOTE: credentials pointing at host services (e.g. Ollama) need"
    echo "      base_url http://host.docker.internal:<port> inside the container."
    ;;
esac
