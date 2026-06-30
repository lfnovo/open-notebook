#!/usr/bin/env bash
# Backup Open Notebook data volumes to a timestamped .tar.gz archive.
#
# Required env (sourced from .env.server if not exported):
#   BACKUP_DIR           Destination directory on the host (will be created).
#   BACKUP_KEEP_DAYS     Prune archives older than N days (default: 7).
#
# Usage:
#   ./scripts/backup.sh
#   BACKUP_KEEP_DAYS=30 ./scripts/backup.sh
#
# Cron suggestion (run daily at 02:17 server-local time):
#   17 2 * * * /opt/open-notebook/scripts/backup.sh \
#       >> /var/log/open-notebook-backup.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# Prefer inline env vars; fall back to sourcing .env.server if it exists.
if [[ -z "${BACKUP_DIR:-}" && -f "${REPO_ROOT}/.env.server" ]]; then
    # shellcheck disable=SC1091
    set -a; source "${REPO_ROOT}/.env.server"; set +a
fi

BACKUP_DIR="${BACKUP_DIR:-/var/backups/open-notebook}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"

# Project name comes from `name:` field in docker-compose.server.yml.
PROJECT_NAME="open-notebook"
VOL_SURREAL="${PROJECT_NAME}_notebook_surreal_data"
VOL_APP="${PROJECT_NAME}_notebook_app_data"

mkdir -p "${BACKUP_DIR}"

# UTC timestamp so archives sort cleanly across timezones.
STAMP="$(date -u +%Y-%m-%d-%H%MZ)"
ARCHIVE_NAME="open-notebook-${STAMP}.tar.gz"
ARCHIVE_PATH="${BACKUP_DIR}/${ARCHIVE_NAME}"

echo "[backup] target:  ${ARCHIVE_PATH}"
echo "[backup] volumes: ${VOL_SURREAL}, ${VOL_APP}"

# One-shot alpine container mounts BOTH volumes (read-only) and the
# backup directory, then tar's them into a single archive. alpine ships
# with tar + gzip so no extra packages are needed.
docker run --rm \
    -v "${VOL_SURREAL}:/src/surreal:ro" \
    -v "${VOL_APP}:/src/notebook:ro" \
    -v "${BACKUP_DIR}:/dst" \
    alpine:3.20 \
    sh -c "
        set -e
        tar -czf /dst/${ARCHIVE_NAME} -C /src surreal notebook
        echo '[backup] archive size:' \$(stat -c%s /dst/${ARCHIVE_NAME}) bytes
    "

# Prune archives older than BACKUP_KEEP_DAYS.
if [[ -d "${BACKUP_DIR}" ]]; then
    while IFS= read -r old; do
        echo "[backup] pruning: ${old}"
        rm -f -- "${old}"
    done < <(find "${BACKUP_DIR}" -maxdepth 1 -type f \
                -name 'open-notebook-*.tar.gz' \
                -mtime "+${BACKUP_KEEP_DAYS}")
fi

echo "[backup] done. Remaining archives:"
ls -lh "${BACKUP_DIR}"/open-notebook-*.tar.gz 2>/dev/null || echo "  (none)"
