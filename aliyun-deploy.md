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
2. Verify the intended changes before committing:

   ```bash
   git status --short
   git diff --check
   bash -n deploy/non-docker/deploy-from-github-online.sh
   ```

3. Run the targeted tests or build for the changed area. For frontend changes,
   include at least the affected test file and `npm --prefix frontend run build`
   when the change can affect production rendering.
4. Commit locally.
5. Push the branch:

   ```bash
   git push origin online
   ```

6. Confirm local and remote commits match:

   ```bash
   git rev-parse HEAD
   git ls-remote origin refs/heads/online
   ```

7. Run the deployment dry-run after the working tree is clean and `origin/online`
   matches the local commit:

   ```bash
   deploy/non-docker/deploy-from-github-online.sh --dry-run
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

If upstream downloads are slow or time out, do not switch to a mirror by
default. Use the temporary proxy already running on the server for that deploy
session:

```bash
ssh lumina 'HTTP_PROXY=http://127.0.0.1:8080 HTTPS_PROXY=http://127.0.0.1:8080 ALL_PROXY=socks5://127.0.0.1:1080 NO_PROXY=127.0.0.1,localhost,::1 bash -s -- --server' \
  < deploy/non-docker/deploy-from-github-online.sh
```

This keeps proxy settings out of Git and out of systemd unit files.

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
git diff --check
git add <files>
git commit -m "<message>"
git status --short
git push origin online
deploy/non-docker/deploy-from-github-online.sh
```

If SMTP, WeChat login, or AI provider keys are needed, stop and request direct
confirmation before editing `/opt/lumina/shared/.env`.

## 2026-05-13 rollout closeout

The initial Aliyun online test deployment was completed and verified on
2026-05-13. The final deployed commit for that rollout was `fca4b81`.

Completed work:

- Created the GitHub-origin deployment workflow and one-command deploy script.
- Switched the database layer to SurrealDB Docker Compose while keeping the API,
  worker, and frontend as host systemd services.
- Opened only the public ingress needed for the site: `80/443` for Nginx and
  SSH for administration. App ports remain bound to loopback.
- Enabled temporary public registration for testing with
  `ALLOW_PUBLIC_REGISTRATION=true`.
- Preserved `/opt/lumina/shared/.env` across redeploys so generated passwords
  and future SMTP/WeChat/AI secrets are not overwritten.
- Added the command queue database migration required by the deployed worker.
- Fixed frontend standalone startup so `.next/static` and `public` assets are
  available to the Next.js standalone server, resolving `_next/static` chunk
  `404` errors.
- Added the homepage compliance footer copied from the YinHour site footer:
  copyright, privacy policy, legal notice, ICP filing, and public-security
  filing links.

Verification used during closeout:

```bash
git rev-parse HEAD
git ls-remote origin refs/heads/online
ssh lumina 'sudo -u lumina git -C /opt/lumina/repo rev-parse --short HEAD'
ssh lumina 'systemctl is-active lumina-api lumina-worker lumina-frontend nginx docker'
ssh lumina 'sudo docker ps --filter name=lumina-surrealdb'
ssh lumina 'curl -fsS http://127.0.0.1:5055/health'
curl -I https://lumina.yinhour.com/login
```

## Operational notes

- The deployment source of truth is GitHub `origin/online`; do not patch server
  source files directly except for emergency diagnosis that will be copied back
  into Git immediately.
- The script uses `git reset --hard origin/online` inside `/opt/lumina/repo`.
  Keep persistent state in `/opt/lumina/shared/.env` and
  `/var/lib/lumina/surrealdb`, not in the checkout.
- The first deployment creates secrets only when `/opt/lumina/shared/.env` is
  missing or contains `CHANGE_ME` placeholders. Later deploys must not reset the
  admin password automatically.
- If Certbot is skipped, compare DNS and public IP first, then verify Aliyun
  security group rules before rerunning
  `sudo certbot --nginx -d lumina.yinhour.com`.
- If the page shell loads but browser console shows `_next/static/... 404`,
  rebuild the frontend and restart `lumina-frontend`; the standalone server
  must see `.next/standalone/.next/static` and `.next/standalone/public`.
- If API startup fails after a schema change, check `journalctl -u lumina-api`
  for migration errors before restarting worker jobs.
- Keep `EMAIL_PROVIDER=debug` until SMTP or Resend is directly confirmed.
  Verification codes for test registration can be read from
  `journalctl -u lumina-api`.
