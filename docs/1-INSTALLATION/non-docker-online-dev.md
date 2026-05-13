# Non-Docker Online Development/Test Deployment

This guide deploys Lumina from source on a public VPS without Docker. It is meant for an online development or test website: easy to update, protected by login, and close to production behavior.

## Target Topology

```text
Browser -> Nginx + HTTPS -> Next.js frontend :8502
                         -> Next.js rewrite /api/* -> FastAPI :5055
FastAPI + worker -> SurrealDB Docker container :8000
```

Only Nginx should be reachable from the Internet. SurrealDB, the API, and the frontend bind to `127.0.0.1`.

## 1. Server Requirements

- Ubuntu 22.04/24.04 or another modern Linux server
- 2 CPU cores, 8 GB RAM recommended
- Python 3.11 or 3.12
- Node.js 20+
- uv
- Docker and Docker Compose for SurrealDB, pinned image: `surrealdb/surrealdb:v3.0.5`
- Nginx and Certbot
- Domain: `lumina.yinhour.com`

## 2. Create User and Directories

```bash
sudo adduser --system --group --home /opt/lumina lumina
sudo mkdir -p /opt/lumina/repo /opt/lumina/shared /var/lib/lumina/surrealdb
sudo chown -R lumina:lumina /opt/lumina /var/lib/lumina
```

## 3. Install System Dependencies

```bash
sudo apt update
sudo apt install -y git curl build-essential ffmpeg nginx certbot python3-certbot-nginx docker.io docker-compose-v2
```

Install Node.js 20 and uv using your server's preferred package source. Then verify:

```bash
node --version
npm --version
uv --version
python3 --version
```

Enable Docker and verify Compose:

```bash
sudo systemctl enable --now docker
sudo docker compose version
```

## 4. Clone the Project

```bash
sudo -u lumina git clone --branch online https://github.com/YinHour/lumina.git /opt/lumina/repo
cd /opt/lumina/repo
```

If you are deploying a private fork, replace the Git URL with your repository URL.

## 5. Configure Environment

```bash
sudo -u lumina cp deploy/non-docker/env.online-dev.example /opt/lumina/shared/.env
sudo -u lumina nano /opt/lumina/shared/.env
```

Update at least these values:

```bash
API_URL=https://lumina.yinhour.com
OPEN_NOTEBOOK_CORS_ORIGINS=https://lumina.yinhour.com
OPEN_NOTEBOOK_ENCRYPTION_KEY=...
LUMINA_ADMIN_PASSWORD=...
SURREAL_PASSWORD=...
```

Generate strong values:

```bash
openssl rand -base64 48
openssl rand -base64 32
```

Keep `OPEN_NOTEBOOK_AUTH_MODE=jwt` for any Internet-facing site. This online test deployment temporarily uses `ALLOW_PUBLIC_REGISTRATION=true`; disable it before production launch unless you intentionally want public signups.

Optional WeChat QR-code login uses a WeChat Open Platform website application:

```bash
WECHAT_OPEN_APP_ID=...
WECHAT_OPEN_APP_SECRET=
WECHAT_OPEN_REDIRECT_URI=https://lumina.yinhour.com/login/wechat/callback
```

Register the same redirect URI in WeChat Open Platform. With `ALLOW_PUBLIC_REGISTRATION=false`, WeChat sign-in is limited to existing bound users; set it to `true` only if first-time WeChat users should be able to create accounts.

## 6. Install App Dependencies and Build Frontend

```bash
cd /opt/lumina/repo
sudo -u lumina uv sync --frozen

cd /opt/lumina/repo/frontend
sudo -u lumina npm ci
sudo -u lumina npm run build
```

## 7. Install systemd Services

```bash
sudo cp /opt/lumina/repo/deploy/non-docker/lumina-api.service /etc/systemd/system/lumina-api.service
sudo cp /opt/lumina/repo/deploy/non-docker/lumina-worker.service /etc/systemd/system/lumina-worker.service
sudo cp /opt/lumina/repo/deploy/non-docker/lumina-frontend.service /etc/systemd/system/lumina-frontend.service

sudo systemctl daemon-reload
sudo docker compose --env-file /opt/lumina/shared/.env -f /opt/lumina/repo/deploy/non-docker/surrealdb-compose.yml up -d
sudo systemctl enable --now lumina-api
```

Initialize the admin account after the API has run migrations:

```bash
cd /opt/lumina/repo
sudo -u lumina uv run --env-file /opt/lumina/shared/.env python3 scripts/init-admin.py --force
```

Then start the worker and frontend:

```bash
sudo systemctl enable --now lumina-worker
sudo systemctl enable --now lumina-frontend
```

Check status:

```bash
sudo docker ps --filter name=lumina-surrealdb
systemctl status lumina-api lumina-worker lumina-frontend
curl http://127.0.0.1:5055/health
curl -I http://127.0.0.1:8502
```

## 8. Configure Nginx and HTTPS

```bash
sudo cp /opt/lumina/repo/deploy/non-docker/nginx-lumina.conf /etc/nginx/sites-available/lumina
sudo ln -sf /etc/nginx/sites-available/lumina /etc/nginx/sites-enabled/lumina
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d lumina.yinhour.com
```

Now open:

```text
https://lumina.yinhour.com/login
```

Use `LUMINA_ADMIN_USERNAME` and `LUMINA_ADMIN_PASSWORD` from `/opt/lumina/shared/.env`.

## 9. Update the Test Site

```bash
cd /opt/lumina/repo
sudo -u lumina git pull
sudo -u lumina uv sync --frozen

cd /opt/lumina/repo/frontend
sudo -u lumina npm ci
sudo -u lumina npm run build

sudo systemctl restart lumina-api lumina-worker lumina-frontend
```

## 10. Logs

```bash
sudo docker logs -f lumina-surrealdb
journalctl -u lumina-api -f
journalctl -u lumina-worker -f
journalctl -u lumina-frontend -f
```

## Notes

- Do not expose port `8000`, `5055`, or `8502` in the firewall.
- SurrealDB is managed by Docker Compose so database upgrades are image tag changes in `deploy/non-docker/surrealdb-compose.yml`.
- The first API startup runs database migrations automatically.
- The worker is required for long-running command jobs such as podcast generation.
- If registration or password reset emails are needed, replace `EMAIL_PROVIDER=debug` with SMTP or Resend settings.
