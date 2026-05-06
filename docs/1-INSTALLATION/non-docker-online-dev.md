# Non-Docker Online Development/Test Deployment

This guide deploys Lumina from source on a public VPS without Docker. It is meant for an online development or test website: easy to update, protected by login, and close to production behavior.

## Target Topology

```text
Browser -> Nginx + HTTPS -> Next.js frontend :8502
                         -> Next.js rewrite /api/* -> FastAPI :5055
FastAPI + worker -> SurrealDB :8000
```

Only Nginx should be reachable from the Internet. SurrealDB, the API, and the frontend bind to `127.0.0.1`.

## 1. Server Requirements

- Ubuntu 22.04/24.04 or another modern Linux server
- 2 CPU cores, 8 GB RAM recommended
- Python 3.11 or 3.12
- Node.js 20+
- uv
- SurrealDB 3.0.x, pinned target: `v3.0.5`
- Nginx and Certbot
- Domain: `lumina.yinhour.com`

## 2. Create User and Directories

```bash
sudo adduser --system --group --home /opt/lumina lumina
sudo mkdir -p /opt/lumina /var/lib/lumina/surrealdb
sudo chown -R lumina:lumina /opt/lumina /var/lib/lumina
```

## 3. Install System Dependencies

```bash
sudo apt update
sudo apt install -y git curl build-essential ffmpeg nginx certbot python3-certbot-nginx
```

Install Node.js 20 and uv using your server's preferred package source. Then verify:

```bash
node --version
npm --version
uv --version
python3 --version
```

Install the SurrealDB `v3.0.5` binary to `/usr/local/bin/surreal` and verify:

```bash
surreal version
```

## 4. Clone the Project

```bash
sudo -u lumina git clone https://github.com/YinHour/lumina.git /opt/lumina
cd /opt/lumina
```

If you are deploying a private fork, replace the Git URL with your repository URL.

## 5. Configure Environment

```bash
sudo -u lumina cp deploy/non-docker/env.online-dev.example /opt/lumina/.env
sudo -u lumina nano /opt/lumina/.env
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

Keep `OPEN_NOTEBOOK_AUTH_MODE=jwt` for any Internet-facing site. Keep `ALLOW_PUBLIC_REGISTRATION=false` unless you intentionally want public signups.

## 6. Install App Dependencies and Build Frontend

```bash
cd /opt/lumina
sudo -u lumina uv sync --frozen

cd /opt/lumina/frontend
sudo -u lumina npm ci
sudo -u lumina npm run build
```

## 7. Install systemd Services

```bash
sudo cp /opt/lumina/deploy/non-docker/surrealdb.service /etc/systemd/system/surrealdb.service
sudo cp /opt/lumina/deploy/non-docker/lumina-api.service /etc/systemd/system/lumina-api.service
sudo cp /opt/lumina/deploy/non-docker/lumina-worker.service /etc/systemd/system/lumina-worker.service
sudo cp /opt/lumina/deploy/non-docker/lumina-frontend.service /etc/systemd/system/lumina-frontend.service

sudo systemctl daemon-reload
sudo systemctl enable --now surrealdb
sudo systemctl enable --now lumina-api
```

Initialize the admin account after the API has run migrations:

```bash
cd /opt/lumina
sudo -u lumina uv run --env-file /opt/lumina/.env python3 scripts/init-admin.py --force
```

Then start the worker and frontend:

```bash
sudo systemctl enable --now lumina-worker
sudo systemctl enable --now lumina-frontend
```

Check status:

```bash
systemctl status surrealdb lumina-api lumina-worker lumina-frontend
curl http://127.0.0.1:5055/health
curl -I http://127.0.0.1:8502
```

## 8. Configure Nginx and HTTPS

```bash
sudo cp /opt/lumina/deploy/non-docker/nginx-lumina.conf /etc/nginx/sites-available/lumina
sudo ln -sf /etc/nginx/sites-available/lumina /etc/nginx/sites-enabled/lumina
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d lumina.yinhour.com
```

Now open:

```text
https://lumina.yinhour.com/login
```

Use `LUMINA_ADMIN_USERNAME` and `LUMINA_ADMIN_PASSWORD` from `/opt/lumina/.env`.

## 9. Update the Test Site

```bash
cd /opt/lumina
sudo -u lumina git pull
sudo -u lumina uv sync --frozen

cd /opt/lumina/frontend
sudo -u lumina npm ci
sudo -u lumina npm run build

sudo systemctl restart lumina-api lumina-worker lumina-frontend
```

## 10. Logs

```bash
journalctl -u surrealdb -f
journalctl -u lumina-api -f
journalctl -u lumina-worker -f
journalctl -u lumina-frontend -f
```

## Notes

- Do not expose port `8000`, `5055`, or `8502` in the firewall.
- The first API startup runs database migrations automatically.
- The worker is required for long-running command jobs such as podcast generation.
- If registration or password reset emails are needed, replace `EMAIL_PROVIDER=debug` with SMTP or Resend settings.
