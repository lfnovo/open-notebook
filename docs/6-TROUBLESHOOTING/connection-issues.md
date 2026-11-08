# Connection Issues - UI, API & Database

When the pieces of Open Notebook can't reach each other. There are three hops:

```
Browser ──> Web UI (8502) ──> API (5055) ──> SurrealDB (8000)
```

With the shipped `docker-compose.yml` there are two services: `surrealdb`, and `open_notebook`, which runs the UI, the API and the background worker together. Commands on this page use those names.

---

## The page doesn't load at all

The browser shows its own error ("This site can't be reached", "connection refused") for `http://localhost:8502`.

```bash
docker compose ps                      # is open_notebook "Up"?
docker compose logs --tail 50 open_notebook
```

- **Not running or restarting:** read the log. The API waits for the database before the UI starts, so a database problem can keep the UI down too (see [Database Connection Failed](#database-connection-failed)).
- **Running, but the port isn't published:** `docker compose ps` must show `0.0.0.0:8502->8502/tcp`. If you changed the mapping, use the host port you chose.
- **"Bind for 0.0.0.0:8502 failed: port is already allocated"** when starting: another program uses the port. Find it with `lsof -i :8502` (or `sudo ss -ltnp | grep 8502`), or map a different host port (`"8503:8502"`) and run `docker compose up -d`.
- **From another machine:** the server's firewall must allow 8502 (and 5055, see below).

The first start after enabling `OPEN_NOTEBOOK_ENABLE_DOCLING` or `OPEN_NOTEBOOK_ENABLE_CRAWL4AI` installs large packages before anything else starts; the log shows `[entrypoint] Installing ...`. Wait for it to finish.

---

## "Unable to Connect to API Server"

Full overlay text: **Unable to Connect to API Server** — "The Open Notebook API server could not be reached". On the login page the same problem reads "Unable to connect to server. Please check if the API is running."

The UI loaded, but the browser can't reach the API. Click **Show Technical Details** in the overlay: **Attempted URL** is the API address the browser used.

**1. Is the API up?**

```bash
curl http://localhost:5055/health
# {"status":"healthy"}
```

No answer: check `docker compose logs open_notebook` for API errors. A database problem stops the API from starting (see below).

**2. Can the browser reach the Attempted URL?**

When `API_URL` is not set, the browser uses the host from the address bar plus port 5055. Opening `http://192.168.1.50:8502` makes it call `http://192.168.1.50:5055`. So:

- Port 5055 must be published (`"5055:5055"` in the shipped file) and allowed by the server's firewall.
- Behind a reverse proxy, the auto-detected `https://your-domain:5055` usually doesn't exist. Set `API_URL=https://your-domain` (no `/api`) in the `open_notebook` environment and run `docker compose up -d`. See [Reverse Proxy](../5-CONFIGURATION/reverse-proxy.md#how-the-browser-finds-the-api).
- If you published the API on another host port, set `API_URL` to match (`http://<host>:<port>`).

Check what the container received with `docker compose exec open_notebook printenv API_URL`. Changes need `docker compose up -d`; `docker compose restart` keeps the old environment.

**3. HTTPS page, HTTP API?** The browser blocks it as mixed content. `API_URL` must start with `https://` when the UI is served over HTTPS.

---

## "Database Connection Failed"

Full overlay text: **Database Connection Failed** — "The API server is running, but the database is not accessible". You see it when the database becomes unreachable while the API is running.

If the database is unreachable when the API **starts**, the API doesn't come up at all: its log shows `Database is not reachable yet (attempt n/12)` while it waits, then `Database did not become reachable after 12 attempts` and `CRITICAL: Database migration failed`. The browser then can't reach the API (**Unable to Connect to API Server**), or in the Docker image the UI doesn't load at all, because it waits for the API. The causes and fixes are the same.

```bash
docker compose ps surrealdb
docker compose logs --tail 50 surrealdb
docker compose exec open_notebook printenv SURREAL_URL SURREAL_USER SURREAL_NAMESPACE SURREAL_DATABASE   # no passwords
```

| Cause | Fix |
|-------|-----|
| `surrealdb` isn't running, or crashed (often a permissions error on `./surreal_data`) | Read its log. The shipped service runs as `user: root` so it can write the bind mount |
| `SURREAL_URL` uses `localhost` inside Docker | Use the service name: `ws://surrealdb:8000/rpc` |
| Wrong user or password | `SURREAL_USER`/`SURREAL_PASSWORD` must match the `--user`/`--pass` SurrealDB started with. With the shipped file, set both in `.env` so the two services agree |
| Running from source with the Docker URL | Use `ws://localhost:8000/rpc` in `.env` |
| Corporate proxy, API log shows HTTP 403 on the database websocket | Add `surrealdb` and `localhost` to `NO_PROXY` ([Environment Reference → Outbound proxy](../5-CONFIGURATION/environment-reference.md#outbound-proxy)) |

More: [Database](../5-CONFIGURATION/database.md).

---

## Background jobs never run

Sources stay **Queued**, podcasts stay **Pending**, embeddings never finish. The worker isn't running or uses a different database namespace. See [Processing Issues → Sources stay "Queued"](processing-issues.md#sources-stay-queued-waiting-to-be-processed).

---

## Slow pages, 502 or 504 behind a proxy

- `502 Bad Gateway`: the proxy can't reach port 8502 (container down, or not on the proxy's network).
- `504 Gateway Timeout` or `socket hang up` on long chats and transformations: the proxy's read timeout is shorter than the request. Set it to at least 600 seconds.

See [Reverse Proxy → Troubleshooting](../5-CONFIGURATION/reverse-proxy.md#troubleshooting).

---

## CORS errors in the browser console

`Cross-Origin Request Blocked` or `has been blocked by CORS policy`. With default settings the API accepts every origin, so on a default install a CORS error almost always hides another problem:

- **Status 413:** an upload hit a size limit in your reverse proxy ([Upload size](../5-CONFIGURATION/reverse-proxy.md#upload-size-413-errors)).
- **502/504 or no status:** the proxy returned its own error page, which has no CORS headers. Fix the underlying error.
- **You set `CORS_ORIGINS`:** the origin in the browser's address bar (scheme, host and port) must be in the list exactly. See [Security → CORS Origins](../5-CONFIGURATION/security.md#cors-origins).

---

## Login problems

- **"Invalid password"**: the password doesn't match `OPEN_NOTEBOOK_PASSWORD`. If you just changed it in `docker-compose.yml`, apply it with `docker compose up -d`.
- **Logged out, or "Unauthorized access, please check your password"** after changing the password: the browser still holds the old one. Sign out and log in again.

See [Security](../5-CONFIGURATION/security.md#password-protection).

---

## Provider connections (Test Connection)

"Cannot connect to server. Check the URL is correct." and "Cannot connect to Ollama. Check if Ollama server is running." come from the **Test** button in Manage → Models. They are about the AI provider's address, not about Open Notebook's own API. See [AI & Chat Issues → Test fails](ai-chat-issues.md#test-fails).

### SSL errors with a provider

`[SSL: CERTIFICATE_VERIFY_FAILED]` in the log, or Test failing only on an `https://` Base URL: the provider uses a certificate the container doesn't trust. Mount the CA bundle and set `ESPERANTO_SSL_CA_BUNDLE`; this covers model calls, Test and model discovery. See [Advanced → SSL](../5-CONFIGURATION/advanced.md#ssl-for-self-signed-providers).

---

## Full check

```bash
docker compose ps                                  # both services Up
curl -s http://localhost:5055/health               # {"status":"healthy"}
curl -s http://localhost:5055/api/config           # "dbStatus": "online"
docker compose logs --since 10m open_notebook | grep -iE "error|warning|critical"
```

---

## Related

- [Reverse Proxy](../5-CONFIGURATION/reverse-proxy.md)
- [Database](../5-CONFIGURATION/database.md)
- [Processing Issues](processing-issues.md)
- [AI & Chat Issues](ai-chat-issues.md)
