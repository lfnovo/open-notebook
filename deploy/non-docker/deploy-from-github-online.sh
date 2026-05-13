#!/usr/bin/env bash
set -euo pipefail

DOMAIN="lumina.yinhour.com"
REPO_URL="https://github.com/YinHour/lumina.git"
BRANCH="online"
SSH_TARGET="${SSH_TARGET:-lumina}"
APP_ROOT="/opt/lumina"
REPO_DIR="${APP_ROOT}/repo"
SHARED_DIR="${APP_ROOT}/shared"
ENV_FILE="${SHARED_DIR}/.env"
DATA_DIR="/var/lib/lumina/surrealdb"
NODE_MAJOR="20"

MODE="local"
DRY_RUN=0
SKIP_LOCAL_CHECKS=0

usage() {
  cat <<'USAGE'
Usage:
  deploy/non-docker/deploy-from-github-online.sh [--dry-run]
  deploy/non-docker/deploy-from-github-online.sh [--skip-local-checks]
  deploy/non-docker/deploy-from-github-online.sh --server [--dry-run]

Default mode streams this script to SSH target "lumina" and runs the server
deployment there. Use --server when executing directly on the server.

Environment:
  SSH_TARGET=lumina  Override the SSH alias/target used in default mode.

Security:
  This script never prints /opt/lumina/shared/.env and never writes third-party
  credentials to Git. SurrealDB runs in Docker Compose, while API/frontend/worker
  run as host systemd services. Configure SMTP, WeChat, AI provider keys, or
  cloud access keys only after direct confirmation from the operator.
USAGE
}

while (($#)); do
  case "$1" in
    --server)
      MODE="server"
      ;;
    --dry-run)
      DRY_RUN=1
      ;;
    --skip-local-checks)
      SKIP_LOCAL_CHECKS=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

log() {
  printf '[lumina-deploy] %s\n' "$*"
}

run() {
  log "$*"
  if ((DRY_RUN)); then
    return 0
  fi
  "$@"
}

run_shell() {
  if ((DRY_RUN)); then
    log "Dry-run: would run shell block."
    return 0
  fi
  log "Running shell block."
  bash -lc "$*"
}

require_sudo() {
  if ! sudo -n true >/dev/null 2>&1; then
    echo "Passwordless sudo is required for deployment." >&2
    exit 1
  fi
}

local_secret_scan() {
  log "Scanning tracked deployment files for obvious secret values."
  local scan_paths=(
    "aliyun-deploy.md"
    "deploy/non-docker"
    "docs/1-INSTALLATION/non-docker-online-dev.md"
  )
  local pattern
  pattern='(AccessKey Secret|LTAI[0-9A-Za-z]{16,}|ALIYUN_ACCESS_KEY_SECRET|ALIBABA_CLOUD_ACCESS_KEY_SECRET|OPEN_NOTEBOOK_ENCRYPTION_KEY=[^[:space:]#]*(sk-|AKIA|LTAI|[A-Za-z0-9+/]{32,}={0,2})|SURREAL_PASSWORD=[^[:space:]#]*(sk-|AKIA|LTAI|[A-Za-z0-9+/]{24,}={0,2})|LUMINA_ADMIN_PASSWORD=[^[:space:]#]*(sk-|AKIA|LTAI|[A-Za-z0-9+/]{16,}={0,2})|SMTP_PASSWORD=[^[:space:]#]+|WECHAT_OPEN_APP_SECRET=[^[:space:]#]+)'

  if git grep -n -E "$pattern" -- "${scan_paths[@]}" \
    ':!deploy/non-docker/env.online-dev.example' \
    ':!deploy/non-docker/deploy-from-github-online.sh' \
    ':!aliyun-deploy.md' >/tmp/lumina-secret-scan.$$ 2>/dev/null; then
    cat /tmp/lumina-secret-scan.$$ >&2
    rm -f /tmp/lumina-secret-scan.$$
    echo "Potential secret-like value found in deployment files. Refusing to deploy." >&2
    exit 1
  fi
  rm -f /tmp/lumina-secret-scan.$$
}

local_preflight() {
  if ((SKIP_LOCAL_CHECKS)); then
    log "Skipping local checks by request."
    return
  fi

  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Run this script from the Lumina git repository, or use --server on the server." >&2
    exit 1
  fi

  local branch
  branch="$(git branch --show-current)"
  if [ "$branch" != "$BRANCH" ]; then
    echo "Current branch is '$branch'; expected '$BRANCH'." >&2
    exit 1
  fi

  if [ -n "$(git status --porcelain)" ]; then
    echo "Working tree is not clean. Commit and push before deploying from GitHub." >&2
    git status --short >&2
    exit 1
  fi

  local local_sha remote_sha
  local_sha="$(git rev-parse "$BRANCH")"
  remote_sha="$(git ls-remote origin "refs/heads/${BRANCH}" | awk '{print $1}')"
  if [ -z "$remote_sha" ]; then
    echo "Could not resolve origin/${BRANCH}." >&2
    exit 1
  fi
  if [ "$local_sha" != "$remote_sha" ]; then
    echo "Local ${BRANCH} is not synchronized with origin/${BRANCH}." >&2
    echo "local:  $local_sha" >&2
    echo "remote: $remote_sha" >&2
    echo "Run: git push origin ${BRANCH}" >&2
    exit 1
  fi

  local_secret_scan
}

ensure_lumina_user_and_dirs() {
  if ! id lumina >/dev/null 2>&1; then
    run sudo useradd --system --home-dir "$APP_ROOT" --create-home --shell /usr/sbin/nologin lumina
  fi
  run sudo mkdir -p "$APP_ROOT" "$SHARED_DIR" "$DATA_DIR"
  run sudo chown -R lumina:lumina "$APP_ROOT" /var/lib/lumina
}

install_base_packages() {
  run sudo apt-get update
  run sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl git build-essential ffmpeg nginx certbot \
    python3 python3-certbot-nginx openssl tar xz-utils
}

install_docker() {
  if command -v docker >/dev/null 2>&1 && sudo docker compose version >/dev/null 2>&1; then
    log "Docker and Compose already installed."
    run sudo systemctl enable --now docker
    return
  fi

  log "Installing Docker and Docker Compose plugin."
  if ((DRY_RUN)); then
    log "Dry-run: would install docker.io and a compose plugin."
    return
  fi

  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-v2 \
    || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-plugin \
    || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose
  sudo systemctl enable --now docker
  sudo docker compose version >/dev/null
}

node_major_version() {
  if ! command -v node >/dev/null 2>&1; then
    echo 0
    return
  fi
  node -p 'Number(process.versions.node.split(".")[0])' 2>/dev/null || echo 0
}

install_node() {
  if [ "$(node_major_version)" -ge "$NODE_MAJOR" ] && command -v npm >/dev/null 2>&1; then
    log "Node.js $(node --version) already installed."
    return
  fi

  log "Installing Node.js ${NODE_MAJOR}."
  if ! ((DRY_RUN)); then
    if curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | sudo -E bash -; then
      sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs || true
    fi
  else
    log "Dry-run: would run NodeSource installer."
  fi

  if [ "$(node_major_version)" -ge "$NODE_MAJOR" ] && command -v npm >/dev/null 2>&1; then
    log "Node.js $(node --version) installed via package manager."
    return
  fi

  run_shell '
    set -euo pipefail
    arch="$(uname -m)"
    case "$arch" in
      x86_64) node_arch="x64" ;;
      aarch64|arm64) node_arch="arm64" ;;
      *) echo "Unsupported Node.js architecture: $arch" >&2; exit 1 ;;
    esac
    version="$(python3 - <<PY
import json, urllib.request
with urllib.request.urlopen("https://nodejs.org/dist/index.json", timeout=30) as response:
    versions = json.load(response)
for item in versions:
    if item["version"].startswith("v20."):
        print(item["version"])
        break
PY
)"
    base="node-${version}-linux-${node_arch}"
    tmp="$(mktemp -d)"
    curl -fsSL "https://nodejs.org/dist/${version}/${base}.tar.xz" -o "${tmp}/${base}.tar.xz"
    sudo mkdir -p /usr/local/lib/nodejs
    sudo tar -xJf "${tmp}/${base}.tar.xz" -C /usr/local/lib/nodejs
    sudo ln -sfn "/usr/local/lib/nodejs/${base}/bin/node" /usr/local/bin/node
    sudo ln -sfn "/usr/local/lib/nodejs/${base}/bin/npm" /usr/local/bin/npm
    sudo ln -sfn "/usr/local/lib/nodejs/${base}/bin/npx" /usr/local/bin/npx
    rm -rf "$tmp"
  '
}

install_uv() {
  if command -v uv >/dev/null 2>&1; then
    log "uv $(uv --version | awk '{print $2}') already installed."
    return
  fi
  log "Installing uv."
  if ((DRY_RUN)); then
    log "Dry-run: would install uv to /usr/local/bin."
    return
  fi
  curl -LsSf https://astral.sh/uv/install.sh | sudo env UV_INSTALL_DIR=/usr/local/bin sh
}

sync_repo() {
  if ! sudo -u lumina test -d "$REPO_DIR/.git"; then
    run sudo -u lumina git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
  else
    run sudo -u lumina git -C "$REPO_DIR" fetch origin "$BRANCH"
    run sudo -u lumina git -C "$REPO_DIR" checkout -B "$BRANCH" "origin/$BRANCH"
    run sudo -u lumina git -C "$REPO_DIR" reset --hard "origin/$BRANCH"
  fi
  run sudo ln -sfn "$REPO_DIR" "${APP_ROOT}/current"
}

configure_env() {
  run sudo mkdir -p "$SHARED_DIR"
  local created=0
  if [ ! -f "$ENV_FILE" ]; then
    created=1
    run sudo cp "${REPO_DIR}/deploy/non-docker/env.online-dev.example" "$ENV_FILE"
  fi

  if ((DRY_RUN)); then
    log "Dry-run: would normalize ${ENV_FILE} without printing secrets."
    return 0
  fi

  sudo ENV_FILE="$ENV_FILE" ENV_CREATED="$created" python3 - <<'PY'
import base64
import os
from pathlib import Path

env_path = Path(os.environ["ENV_FILE"])
created = os.environ.get("ENV_CREATED") == "1"

def secret(n: int) -> str:
    return base64.b64encode(os.urandom(n)).decode("ascii")

lines = env_path.read_text().splitlines()
keys: dict[str, str] = {}
for line in lines:
    if not line or line.lstrip().startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    keys[key] = value

updates = {
    "API_URL": "https://lumina.yinhour.com",
    "INTERNAL_API_URL": "http://127.0.0.1:5055",
    "OPEN_NOTEBOOK_CORS_ORIGINS": "https://lumina.yinhour.com",
    "OPEN_NOTEBOOK_AUTH_MODE": "jwt",
    "ALLOW_PUBLIC_REGISTRATION": "true",
    "API_HOST": "127.0.0.1",
    "API_PORT": "5055",
    "API_RELOAD": "false",
    "HOSTNAME": "127.0.0.1",
    "PORT": "8502",
    "SURREAL_URL": "ws://127.0.0.1:8000/rpc",
    "SURREAL_USER": "root",
    "SURREAL_NAMESPACE": "open_notebook",
    "SURREAL_DATABASE": "open_notebook",
    "EMAIL_PROVIDER": keys.get("EMAIL_PROVIDER") or "debug",
}

if created or keys.get("OPEN_NOTEBOOK_ENCRYPTION_KEY", "").startswith("CHANGE_ME_"):
    updates["OPEN_NOTEBOOK_ENCRYPTION_KEY"] = secret(48)
if created or keys.get("SURREAL_PASSWORD", "").startswith("CHANGE_ME_"):
    updates["SURREAL_PASSWORD"] = secret(32)
if created or keys.get("LUMINA_ADMIN_PASSWORD", "").startswith("CHANGE_ME_"):
    updates["LUMINA_ADMIN_PASSWORD"] = secret(24)
if not keys.get("LUMINA_ADMIN_USERNAME"):
    updates["LUMINA_ADMIN_USERNAME"] = "admin"

def replace_or_append(key: str, value: str) -> None:
    prefix = key + "="
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = prefix + value
            return
    lines.append(prefix + value)

for key, value in updates.items():
    replace_or_append(key, value)

env_path.write_text("\n".join(lines) + "\n")
PY
  run sudo chown lumina:lumina "$ENV_FILE"
  run sudo chmod 600 "$ENV_FILE"
}

install_services() {
  run sudo cp "${REPO_DIR}/deploy/non-docker/lumina-api.service" /etc/systemd/system/lumina-api.service
  run sudo cp "${REPO_DIR}/deploy/non-docker/lumina-worker.service" /etc/systemd/system/lumina-worker.service
  run sudo cp "${REPO_DIR}/deploy/non-docker/lumina-frontend.service" /etc/systemd/system/lumina-frontend.service
  run sudo systemctl daemon-reload
}

start_surrealdb() {
  run sudo mkdir -p "$DATA_DIR"
  run sudo chown -R 0:0 "$DATA_DIR"
  run sudo docker compose --env-file "$ENV_FILE" -f "${REPO_DIR}/deploy/non-docker/surrealdb-compose.yml" up -d

  if ((DRY_RUN)); then
    log "Dry-run: would wait for SurrealDB container to listen on 127.0.0.1:8000."
    return 0
  fi

  for _ in $(seq 1 60); do
    if python3 - <<'PY' >/dev/null 2>&1
import socket
with socket.create_connection(("127.0.0.1", 8000), timeout=1):
    pass
PY
    then
      return 0
    fi
    sleep 2
  done

  echo "SurrealDB container did not become reachable in time." >&2
  sudo docker logs lumina-surrealdb --tail 80 || true
  exit 1
}

build_app() {
  run sudo -u lumina env HOME="$APP_ROOT" bash -lc "cd '$REPO_DIR' && uv sync --frozen"
  run sudo -u lumina env HOME="$APP_ROOT" npm --prefix "${REPO_DIR}/frontend" ci
  run sudo -u lumina env HOME="$APP_ROOT" npm --prefix "${REPO_DIR}/frontend" run build
}

wait_for_api() {
  if ((DRY_RUN)); then
    log "Dry-run: would wait for API health."
    return 0
  fi
  for _ in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:5055/health >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "API did not become healthy in time." >&2
  sudo journalctl -u lumina-api -n 80 --no-pager || true
  exit 1
}

start_services() {
  local env_created="$1"
  start_surrealdb
  run sudo systemctl enable --now lumina-api
  wait_for_api
  if [ "$env_created" = "1" ]; then
    run sudo -u lumina env HOME="$APP_ROOT" bash -lc "cd '$REPO_DIR' && uv run --env-file '$ENV_FILE' python3 scripts/init-admin.py --force"
  else
    log "Existing environment detected; admin password will not be reset."
  fi
  run sudo systemctl enable --now lumina-worker
  run sudo systemctl enable --now lumina-frontend
}

configure_nginx_and_tls() {
  run sudo cp "${REPO_DIR}/deploy/non-docker/nginx-lumina.conf" /etc/nginx/sites-available/lumina
  run sudo ln -sfn /etc/nginx/sites-available/lumina /etc/nginx/sites-enabled/lumina
  run sudo nginx -t
  run sudo systemctl enable --now nginx
  run sudo systemctl reload nginx

  if ((DRY_RUN)); then
    log "Dry-run: would check DNS and request/renew certificate for ${DOMAIN}."
    return 0
  fi

  local dns_ip public_ip
  dns_ip="$(python3 - <<PY
import socket
try:
    print(socket.gethostbyname("${DOMAIN}"))
except Exception:
    print("")
PY
)"
  public_ip="$(curl -4fsS https://ifconfig.me 2>/dev/null || curl -4fsS https://ipinfo.io/ip 2>/dev/null || true)"

  if [ -z "$dns_ip" ] || [ -z "$public_ip" ] || [ "$dns_ip" != "$public_ip" ]; then
    log "Skipping Certbot: ${DOMAIN} resolves to '${dns_ip:-unknown}', server public IP is '${public_ip:-unknown}'."
    log "Fix DNS/security group, then run: sudo certbot --nginx -d ${DOMAIN}"
    return 0
  fi

  if [ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]; then
    run sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --redirect --register-unsafely-without-email
  else
    log "Certificate for ${DOMAIN} already exists."
  fi
}

verify_deploy() {
  run curl -fsS http://127.0.0.1:5055/health
  run curl -fsSI http://127.0.0.1:8502
  run sudo docker ps --filter name=lumina-surrealdb --format '{{.Names}} {{.Status}}'
  if ! ((DRY_RUN)); then
    log "Deployed commit: $(git -C "$REPO_DIR" rev-parse --short HEAD)"
    log "Open https://${DOMAIN}/login or /register for testing."
  fi
}

server_main() {
  require_sudo
  local env_created=0
  [ ! -f "$ENV_FILE" ] && env_created=1
  ensure_lumina_user_and_dirs
  install_base_packages
  install_docker
  install_node
  install_uv
  sync_repo
  configure_env
  install_services
  build_app
  start_services "$env_created"
  configure_nginx_and_tls
  verify_deploy
}

local_main() {
  local_preflight
  local args=(--server)
  if ((DRY_RUN)); then
    args+=(--dry-run)
  fi
  log "Streaming deployment script to ${SSH_TARGET}."
  ssh "$SSH_TARGET" "bash -s -- ${args[*]}" < "$0"
}

if [ "$MODE" = "server" ]; then
  server_main
else
  local_main
fi
