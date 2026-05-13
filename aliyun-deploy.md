# Aliyun deployment workflow

This plan deploys the `online` branch to the dedicated Aliyun server reachable
with `ssh lumina`. The server pulls from GitHub `origin/online`; source code is
not copied directly from the local working tree.

## Target

- Domain: `https://lumina.yinhour.com`
- Repository: `https://github.com/YinHour/lumina.git`
- Branch: `online`
- App user: `lumina`
- App checkout: `/opt/lumina/repo`
- Persistent environment: `/opt/lumina/shared/.env`
- SurrealDB data: `/var/lib/lumina/surrealdb`

Public traffic goes to Nginx on `80/443`. Internal services bind to loopback:

- Next.js frontend: `127.0.0.1:8502`
- FastAPI: `127.0.0.1:5055`
- SurrealDB Docker container: `127.0.0.1:8000`

## Security rules

- Do not commit cloud access keys, SMTP passwords, WeChat secrets, AI provider
  keys, admin passwords, SurrealDB passwords, or encryption keys.
- Do not print `/opt/lumina/shared/.env` in terminal output.
- Aliyun AccessKeys are deployment-time only and must stay in temporary shell
  environment variables if used.
- SMTP and WeChat login are not configured automatically. Add those values only
  after direct operator confirmation.
- Test registration is temporarily open with `ALLOW_PUBLIC_REGISTRATION=true`.
  Disable it before production launch unless public signup is intended.

## Local release flow

1. Work locally on the `online` branch.
2. Verify the deployment files:

   ```bash
   git diff --check
   bash -n deploy/non-docker/deploy-from-github-online.sh
   deploy/non-docker/deploy-from-github-online.sh --dry-run
   ```

3. Commit locally.
4. Push the branch:

   ```bash
   git push origin online
   ```

5. Confirm local and remote commits match:

   ```bash
   git rev-parse HEAD
   git ls-remote origin refs/heads/online
   ```

## One-command deploy

Run from the local repository after pushing `online`:

```bash
deploy/non-docker/deploy-from-github-online.sh
```

The script streams itself over SSH to `lumina`, then the server:

1. Installs or verifies Git, Python, uv, Node.js 20, npm, ffmpeg, Docker,
   Docker Compose, Nginx, and Certbot.
2. Creates `/opt/lumina/repo`, `/opt/lumina/shared`, and
   `/var/lib/lumina/surrealdb`.
3. Clones or resets `/opt/lumina/repo` to `origin/online`.
4. Creates `/opt/lumina/shared/.env` on first deploy and generates required
   local secrets without printing them.
5. Starts SurrealDB with `deploy/non-docker/surrealdb-compose.yml`, pinned to
   `surrealdb/surrealdb:v3.0.5`, bound only to `127.0.0.1:8000`.
6. Runs `uv sync --frozen`, `npm ci`, and `npm run build`.
7. Installs and starts API, worker, and frontend systemd services plus Nginx.
8. Requests a Let's Encrypt certificate when DNS points at the server.

Dry run:

```bash
deploy/non-docker/deploy-from-github-online.sh --dry-run
```

The local dry run checks that the current branch is `online`, the working tree
is clean, `origin/online` matches the local commit, and deployment files do not
contain obvious secret values.

Run directly on the server:

```bash
cd /opt/lumina/repo
deploy/non-docker/deploy-from-github-online.sh --server
```

## Verification

Local:

```bash
git diff --check
bash -n deploy/non-docker/deploy-from-github-online.sh
deploy/non-docker/deploy-from-github-online.sh --dry-run
```

Server:

```bash
ssh lumina 'git -C /opt/lumina/repo rev-parse --abbrev-ref HEAD'
ssh lumina 'git -C /opt/lumina/repo rev-parse --short HEAD'
ssh lumina 'sudo docker ps --filter name=lumina-surrealdb'
ssh lumina 'systemctl status lumina-api lumina-worker lumina-frontend --no-pager'
ssh lumina 'curl -fsS http://127.0.0.1:5055/health'
curl -I https://lumina.yinhour.com/login
```

Functional smoke test:

1. Visit `https://lumina.yinhour.com/register`.
2. Register a test account.
3. Read the debug verification code from `journalctl -u lumina-api`.
4. Log in, create a notebook, and add a small source.

## Follow-up updates

After the initial deploy, every update follows the same path:

```bash
git checkout online
git status --short
git push origin online
deploy/non-docker/deploy-from-github-online.sh
```

If SMTP, WeChat login, or AI provider keys are needed, stop and request direct
confirmation before editing `/opt/lumina/shared/.env`.
