#!/usr/bin/env bash
# Restore Open Notebook data from a backup archive.
#
# DANGER: this stops the stack and REPLACES the current data volumes.
# You will be asked to type 'yes' to confirm.
#
# Usage:
#   ./scripts/restore.sh
#   ./scripts/restore.sh /var/backups/open-notebook/open-notebook-2026-07-01-0217Z.tar.gz
#
# If no archive path is given, the newest archive in BACKUP_DIR is used.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [[ -z "${BACKUP_DIR:-}" && -f "${REPO_ROOT}/.env.server" ]]; then
    # shellcheck disable=SC1091
    set -a; source "${REPO_ROOT}/.env.server"; set +a
fi
BACKUP_DIR="${BACKUP_DIR:-/var/backups/open-notebook}"

PROJECT_NAME="open-notebook"
VOL_SURREAL="${PROJECT_NAME}_notebook_surreal_data"
VOL_APP="${PROJECT_NAME}_notebook_app_data"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.server.yml"
ENV_FILE="${REPO_ROOT}/.env.server"

# Pick archive: explicit arg > newest in BACKUP_DIR.
if [[ $# -ge 1 ]]; then
    ARCHIVE="$1"
else
    ARCHIVE="$(ls -1t "${BACKUP_DIR}"/open-notebook-*.tar.gz 2>/dev/null | head -1 || true)"
    if [[ -z "${ARCHIVE}" ]]; then
        echo "ERROR: no archive found in ${BACKUP_DIR}" >&2
        echo "Hint: run scripts/backup.sh first, or pass an explicit path." >&2
        exit 1
    fi
    echo "[restore] no archive specified; using newest: ${ARCHIVE}"
fi

if [[ ! -f "${ARCHIVE}" ]]; then
    echo "ERROR: archive not found: ${ARCHIVE}" >&2
    exit 1
fi

echo "[restore] verifying archive contents..."
if ! tar -tzf "${ARCHIVE}" | grep -Eq '(^|/)surreal(/|$)' ; then
    echo "ERROR: archive missing a 'surreal/' top-level entry" >&2
    exit 1
fi
if ! tar -tzf "${ARCHIVE}" | grep -Eq '(^|/)notebook(/|$)' ; then
    echo "ERROR: archive missing a 'notebook/' top-level entry" >&2
    exit 1
fi

echo "[restore] WARNING: this will STOP the stack and REPLACE all data."
read -r -p "Type 'yes' to continue: " CONFIRM
if [[ "${CONFIRM}" != "yes" ]]; then
    echo "aborted."
    exit 1
fi

echo "[restore] stopping stack..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
    --project-name "${PROJECT_NAME}" down

echo "[restore] clearing existing volume contents..."
docker run --rm \
    -v "${VOL_SURREAL}:/dst/surreal" \
    -v "${VOL_APP}:/dst/notebook" \
    alpine:3.20 \
    sh -c "shopt -s dotglob && rm -rf /dst/surreal/* /dst/notebook/*"

echo "[restore] extracting $(basename "${ARCHIVE}")..."
docker run --rm \
    -v "${VOL_SURREAL}:/dst/surreal" \
    -v "${VOL_APP}:/dst/notebook" \
    -v "$(dirname "${ARCHIVE}"):/src:ro" \
    alpine:3.20 \
    sh -c "tar -xzf /src/$(basename "${ARCHIVE}") -C /dst"

echo "[restore] restarting stack..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
    --project-name "${PROJECT_NAME}" up -d

echo "[restore] waiting for open_notebook healthcheck..."
CONTAINER_NAME="${PROJECT_NAME}-open_notebook-1"
for i in $(seq 1 30); do
    STATUS="$(docker inspect --format='{{.State.Health.Status}}' \
        "${CONTAINER_NAME}" 2>/dev/null || echo 'starting')"
    echo "  attempt ${i}/30: ${STATUS}"
    if [[ "${STATUS}" == "healthy" ]]; then
        echo "[restore] done. Verify at: https://${DOMAIN:-your-domain}/"
        exit 0
    fi
    sleep 5
done

echo "[restore] WARNING: container did not become healthy within timeout."
echo "Check logs with: docker compose -f ${COMPOSE_FILE} logs open_notebook"
exit 1
