# Reverse Proxy Configuration

Run Open Notebook behind nginx, Caddy, Traefik or a hosting platform, with your own domain and HTTPS.

---

## How It Works

The `lfnovo/open_notebook` image runs three processes in one container: the Next.js frontend on port 8502, the API on port 5055 and the background worker. The Next.js server forwards every `/api/*` request it receives to the API (`INTERNAL_API_URL`, default `http://localhost:5055`).

So a reverse proxy only needs to reach **port 8502**:

```
Browser ──HTTPS──> Reverse proxy ──> :8502 Next.js ──/api/*──> :5055 API
```

For this to work, the browser must send its API calls to your public URL too. That is what `API_URL` does.

### How the browser finds the API

When the UI loads, it asks the Next.js server (`GET /config`) where the API is:

1. If `API_URL` is set, that value is used. (`NEXT_PUBLIC_API_URL` is accepted as an older name.)
2. Otherwise the server builds it from the request: the `X-Forwarded-Proto` header (or the request's own scheme), the hostname from the `Host` header, and **port 5055**. A page loaded from `http://192.168.1.50:8502` calls the API at `http://192.168.1.50:5055`.

Auto-detection is fine when the browser can reach port 5055 directly (localhost, a LAN). Behind a reverse proxy it produces `https://notebook.example.com:5055`, which usually doesn't exist. **Behind a reverse proxy, set `API_URL` to your public URL**, without `/api`:

```yaml
services:
  open_notebook:
    environment:
      - API_URL=https://notebook.example.com
```

Apply it with `docker compose up -d`. When auto-detection is used, the container log shows `[runtime-config] Auto-detected API URL: ...`, which tells you what the browser was given.

All variables mentioned here are listed in the [Environment Reference](environment-reference.md#network-ports-and-urls).

---

## Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name notebook.example.com;

    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # Uploads: match OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB (default 100)
    client_max_body_size 100M;

    location / {
        proxy_pass http://open_notebook:8502;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';

        # Long-running requests (chat with slow models, transformations)
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}

server {
    listen 80;
    server_name notebook.example.com;
    return 301 https://$server_name$request_uri;
}
```

`open_notebook` is the compose service name; use `127.0.0.1` if nginx runs on the host instead of in the same compose project.

### Compose example with nginx

Add an `nginx` service next to the `surrealdb` and `open_notebook` services of the [shipped docker-compose.yml](https://github.com/lfnovo/open-notebook/blob/main/docker-compose.yml), and stop publishing the app ports to the outside:

```yaml
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    environment:
      - API_URL=https://notebook.example.com
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=a-long-random-string
      - OPEN_NOTEBOOK_PASSWORD=another-long-random-string
      # plus the SURREAL_* variables from the shipped file
    ports:
      - "127.0.0.1:8502:8502"   # local access only; nginx uses the compose network
    volumes:
      - ./notebook_data:/app/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - open_notebook
```

---

## Caddy

```caddy
notebook.example.com {
    request_body {
        max_size 100MB
    }
    reverse_proxy open_notebook:8502 {
        transport http {
            read_timeout 600s
            write_timeout 600s
        }
    }
}
```

Caddy obtains and renews certificates automatically.

---

## Traefik

```yaml
services:
  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    environment:
      - API_URL=https://notebook.example.com
      # plus the variables from the shipped docker-compose.yml
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.notebook.rule=Host(`notebook.example.com`)"
      - "traefik.http.routers.notebook.entrypoints=websecure"
      - "traefik.http.routers.notebook.tls.certresolver=myresolver"
      - "traefik.http.services.notebook.loadbalancer.server.port=8502"
    networks:
      - traefik-network
```

Raise the response timeout in Traefik's static configuration so long requests aren't cut off:

```yaml
# traefik.yml
serversTransport:
  forwardingTimeouts:
    responseHeaderTimeout: 600s
```

---

## Coolify and similar platforms

1. Deploy the [Docker Compose](../1-INSTALLATION/docker-compose.md) setup.
2. Point the platform's domain at port **8502** of the `open_notebook` service.
3. Add `API_URL=https://your-domain.com` to the service's environment.
4. Enable HTTPS in the platform.

---

## Exposing the API to other clients

Browser traffic only needs port 8502. Scripts and integrations can use the same public URL (`https://notebook.example.com/api/...`), which goes through Next.js. To route API calls straight to the API instead, add a location for `/api/`:

```nginx
location /api/ {
    proxy_pass http://open_notebook:5055/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 600s;
}

location / {
    proxy_pass http://open_notebook:8502;
    # ... same headers as above
}
```

Routing `/api/` directly also avoids the 100 MB upload cap of the Next.js proxy (see [Upload size](#upload-size-413-errors)).

### API on its own subdomain

Serve the UI at `notebook.example.com` and the API at `api.notebook.example.com`: proxy the first to port 8502 and the second to port 5055, and set `API_URL=https://api.notebook.example.com`. The browser then calls a different origin, so if you restrict `CORS_ORIGINS`, include `https://notebook.example.com`.

---

## Access from other machines without a proxy

On a LAN you can skip the proxy. Publish both ports (the shipped compose file does) and open `http://<server-ip>:8502`. Auto-detection sends API calls to `http://<server-ip>:5055`, so port 5055 must be reachable from the client:

```bash
# On the server, if a firewall is active
sudo ufw allow 8502
sudo ufw allow 5055
```

If you changed the host side of the API port mapping (for example `"5056:5055"`), auto-detection still assumes 5055: set `API_URL=http://<server-ip>:5056`.

---

## Timeouts

The web UI waits up to 10 minutes for an API response, and each model call is limited by `ESPERANTO_LLM_TIMEOUT` (180 seconds by default). Set proxy read timeouts to at least 600 seconds so the proxy is never the first to give up. Common proxy defaults (60 seconds for nginx) cut off slow chat answers and transformations with `502`/`504` errors or `socket hang up` in the browser.

For slow models, raise `ESPERANTO_LLM_TIMEOUT` (keep it below 600). See [Environment Reference → Timeouts](environment-reference.md#timeouts).

---

## Upload size (413 errors)

Three limits apply to uploads from the UI, and the smallest wins:

| Limit | Default | Where to change it |
|-------|---------|--------------------|
| Your reverse proxy | nginx: 1 MB | `client_max_body_size`, Caddy `request_body max_size`, Traefik buffering middleware |
| Next.js proxy for `/api/*` | 100 MB | Fixed in the frontend build |
| API | 100 MB | `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` |

When the proxy rejects a file, the response doesn't come from Open Notebook, so it has no CORS headers and the browser reports a CORS error with status 413. When the API rejects it, the message is `Request body exceeds the maximum allowed upload size`. To upload files larger than 100 MB, raise `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB` and send them to the API directly (port 5055, or a `/api/` location routed to 5055 as above).

Traefik example:

```yaml
http:
  middlewares:
    large-body:
      buffering:
        maxRequestBodyBytes: 104857600  # 100 MB
```

Kubernetes ingress-nginx: annotation `nginx.ingress.kubernetes.io/proxy-body-size: "100m"`.

---

## Troubleshooting

### "Unable to Connect to API Server"

The UI loaded but its first API call failed. The overlay's **Show Technical Details** shows the **Attempted URL**.

- Attempted URL ends in `:5055` behind a proxy → `API_URL` isn't set (or the container wasn't recreated after setting it). Check with `docker compose exec open_notebook printenv API_URL`, then `docker compose up -d`.
- Attempted URL is `http://...` on an HTTPS page → the browser blocks it as mixed content. Set `API_URL` with `https://`, or make sure the proxy sends `X-Forwarded-Proto`.
- Attempted URL looks right → test it: `curl https://notebook.example.com/api/config`. A healthy instance answers without a password:

```json
{"version": "1.15.0", "latestVersion": "1.15.0", "hasUpdate": false, "dbStatus": "online"}
```

If that fails, the proxy isn't reaching port 8502, or the container isn't running (`docker compose ps`, `docker compose logs open_notebook`).

### "Database Connection Failed"

The proxy and API are fine; the API can't reach SurrealDB. See [Connection Issues](../6-TROUBLESHOOTING/connection-issues.md#database-connection-failed).

### 502 Bad Gateway

- The container isn't running or is still starting: `docker compose ps`, `docker compose logs open_notebook`.
- The proxy can't resolve `open_notebook`: it must be on the same Docker network, or use `127.0.0.1:8502` from the host.

### CORS errors in the browser console

- Status 413 alongside the CORS error → an upload hit a size limit; see [Upload size](#upload-size-413-errors).
- You set `CORS_ORIGINS` → the origin in your address bar must be in it, exactly (scheme, host and port).
- `API_URL` points at a different origin than the page (another port or subdomain) and the request fails for another reason (502, timeout) → the error page from the proxy has no CORS headers. Fix the underlying error.

### `{"detail": "Missing authorization header"}`

`OPEN_NOTEBOOK_PASSWORD` is set and the request had no `Authorization: Bearer <password>` header. Expected when you open an API URL such as `/api/notebooks` in the browser. Log in through the UI, or send the header from scripts. (`/api/config` and `/health` never require it.)

### Browser console logs

The `[Config]` messages in the browser console only appear in development builds (`npm run dev`). On the Docker image, use the container log line `[runtime-config] Auto-detected API URL` and the **Attempted URL** in the error overlay instead.

---

## Checklist

1. HTTPS in front, app ports bound to `127.0.0.1` or not published.
2. `API_URL` set to the public URL (no `/api`), applied with `docker compose up -d`.
3. Proxy timeouts of at least 600 seconds.
4. Proxy body limit matching `OPEN_NOTEBOOK_MAX_UPLOAD_SIZE_MB`.
5. `OPEN_NOTEBOOK_PASSWORD` set, and `CORS_ORIGINS` set to your domain.
6. Secrets kept out of version control: put them in an untracked `docker-compose.override.yml` (see `docker-compose.override.yml.example`) or an uncommitted `env_file:`.

---

## Related

- [Security Configuration](security.md) — password, CORS, hardening
- [Environment Reference](environment-reference.md) — all variables
- [Connection Issues](../6-TROUBLESHOOTING/connection-issues.md) — when the UI can't reach the API
- [Docker Compose installation](../1-INSTALLATION/docker-compose.md)
