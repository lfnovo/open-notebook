# Reverse Proxy Configuration

This guide helps you deploy Open Notebook behind a reverse proxy (nginx, Caddy, Traefik, etc.) or with a custom domain.

## ⭐ Simplified Configuration (v1.1+)

Starting with v1.1, Open Notebook uses Next.js rewrites to dramatically simplify reverse proxy configuration. **You now only need to proxy to port 8502** - Next.js handles internal API routing automatically.

### How It Works

```
Browser → Reverse Proxy → Port 8502 (Next.js)
                             ↓ (internal proxy)
                          Port 5055 (FastAPI)
```

Next.js rewrites automatically forward `/api/*` requests to the FastAPI backend on port 5055, so your reverse proxy only needs to know about one port!

### Simple Configuration Examples

#### Nginx (Recommended)

```nginx
server {
    listen 443 ssl http2;
    server_name notebook.example.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # Single location block - that's it!
    location / {
        proxy_pass http://open-notebook:8502;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_cache_bypass $http_upgrade;
    }
}
```

#### Traefik

```yaml
services:
  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    environment:
      - API_URL=https://notebook.example.com
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.notebook.rule=Host(`notebook.example.com`)"
      - "traefik.http.routers.notebook.entrypoints=websecure"
      - "traefik.http.routers.notebook.tls.certresolver=myresolver"
      - "traefik.http.services.notebook.loadbalancer.server.port=8502"
    networks:
      - traefik-network
```

#### Caddy

```caddy
notebook.example.com {
    reverse_proxy open-notebook:8502
}
```

#### Coolify

1. Create a new service pointing to `lfnovo/open_notebook:v1-latest-single`
2. Set port to **8502** (not 5055!)
3. Add environment variable: `API_URL=https://your-domain.com`
4. Enable HTTPS in Coolify settings
5. Done! Coolify handles the reverse proxy automatically.

### Environment Variables

With the simplified approach, you typically only need:

```bash
# Required for reverse proxy setups
API_URL=https://your-domain.com

# Optional: Only needed for multi-container deployments
# Default is http://localhost:5055 (single-container)
# INTERNAL_API_URL=http://api-service:5055
```

### Optional: Direct API Access for External Integrations

If you have external scripts or integrations that need direct API access, you can still route `/api/*` directly to port 5055:

```nginx
# Optional: Direct API access (for external integrations only)
location /api/ {
    proxy_pass http://open-notebook:5055/api/;
    # ... same headers as above
}

# Primary route (handles browser traffic)
location / {
    proxy_pass http://open-notebook:8502;
    # ... same headers as above
}
```

**Note**: The simplified single-port approach (port 8502 only) works for 95% of use cases. Only add direct API routing if you specifically need it.

---

## Legacy Configuration (Pre-v1.1)

> **Note**: The configurations below are still supported but no longer necessary with v1.1+. New deployments should use the simplified configuration above.

## The API_URL Environment Variable

Starting with v1.0+, Open Notebook supports runtime configuration of the API URL through the `API_URL` environment variable. This means you can use the same Docker image in different deployment scenarios without rebuilding.

### How It Works

The frontend uses a three-tier priority system to determine the API URL:

1. **Runtime Configuration** (Highest Priority): `API_URL` environment variable set at container runtime
2. **Build-time Configuration**: `NEXT_PUBLIC_API_URL` baked into the Docker image
3. **Auto-detection** (Fallback): Infers from the incoming HTTP request headers

**Auto-detection details:**
- The Next.js frontend analyzes the incoming HTTP request
- Extracts the hostname from the `host` header
- Respects the `X-Forwarded-Proto` header (for HTTPS behind reverse proxies)
- Constructs the API URL as `{protocol}://{hostname}:5055`
- Example: Request to `http://10.20.30.20:8502` → API URL becomes `http://10.20.30.20:5055`

## Common Scenarios

### Scenario 1: Docker on Localhost (Default)

No configuration needed! The system auto-detects.

```bash
docker run -d \
  --name open-notebook \
  -p 8502:8502 -p 5055:5055 \
  -v ./notebook_data:/app/data \
  -v ./surreal_data:/mydata \
  lfnovo/open_notebook:v1-latest-single
```

### Scenario 2: Docker on Remote Server (LAN/VPS)

Access via IP address - auto-detection works, but you can be explicit:

```bash
docker run -d \
  --name open-notebook \
  -p 8502:8502 -p 5055:5055 \
  -e API_URL=http://192.168.1.100:5055 \
  -v ./notebook_data:/app/data \
  -v ./surreal_data:/mydata \
  lfnovo/open_notebook:v1-latest-single
```

> **Note**: Don't include `/api` at the end - the system adds this automatically!

### Scenario 3: Behind Reverse Proxy with Custom Domain

This is where `API_URL` is **essential**. Your reverse proxy handles HTTPS and routing.

> **Important**: If your reverse proxy forwards `/api` requests to the backend, set `API_URL` to just the domain (without `/api` suffix). The frontend will append `/api` automatically.

#### Example: nginx + Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    container_name: open-notebook
    environment:
      - API_URL=https://notebook.example.com
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./notebook_data:/app/data
      - ./surreal_data:/mydata
    ports:
      - "8502:8502"  # Frontend
      - "5055:5055"  # API
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: nginx-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - open-notebook
    restart: unless-stopped
```

**nginx.conf:**
```nginx
http {
    upstream frontend {
        server open-notebook:8502;
    }

    upstream api {
        server open-notebook:5055;
    }

    server {
        listen 80;
        server_name notebook.example.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name notebook.example.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # API
        location /api/ {
            proxy_pass http://api/api/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Frontend (catch-all - handles /config automatically)
        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }
    }
}
```

### Scenario 4: Behind Reverse Proxy with Subdomain

If you want API on a separate subdomain:

**docker-compose.yml:**
```yaml
services:
  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    environment:
      - API_URL=https://api.notebook.example.com
      # ... other env vars
```

**nginx.conf:**
```nginx
# Frontend server
server {
    listen 443 ssl http2;
    server_name notebook.example.com;

    location / {
        proxy_pass http://open-notebook:8502;
        # ... proxy headers
    }
}

# API server
server {
    listen 443 ssl http2;
    server_name api.notebook.example.com;

    location / {
        proxy_pass http://open-notebook:5055;
        # ... proxy headers
    }
}
```

### Scenario 5: Traefik

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    environment:
      - API_URL=https://notebook.example.com
    labels:
      # Frontend
      - "traefik.enable=true"
      - "traefik.http.routers.notebook-frontend.rule=Host(`notebook.example.com`)"
      - "traefik.http.routers.notebook-frontend.entrypoints=websecure"
      - "traefik.http.routers.notebook-frontend.tls.certresolver=myresolver"
      - "traefik.http.services.notebook-frontend.loadbalancer.server.port=8502"

      # API (higher priority to match first)
      - "traefik.http.routers.notebook-api.rule=Host(`notebook.example.com`) && PathPrefix(`/api`)"
      - "traefik.http.routers.notebook-api.entrypoints=websecure"
      - "traefik.http.routers.notebook-api.tls.certresolver=myresolver"
      - "traefik.http.routers.notebook-api.priority=100"
      - "traefik.http.services.notebook-api.loadbalancer.server.port=5055"
    networks:
      - traefik-network

networks:
  traefik-network:
    external: true
```

### Scenario 6: Caddy

**Caddyfile:**
```caddy
notebook.example.com {
    # API
    reverse_proxy /api/* open-notebook:5055

    # Frontend (catch-all - handles /config automatically)
    reverse_proxy / open-notebook:8502
}
```

**docker-compose.yml:**
```yaml
services:
  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    environment:
      - API_URL=https://notebook.example.com
    # No need to expose ports if using Caddy in same network
```

## Troubleshooting

### Connection Error: Unable to connect to server

**Symptoms**: Frontend displays "Unable to connect to server. Please check if the API is running."

**Possible Causes**:

1. **API_URL not set correctly** for your reverse proxy setup
   - Check browser console (F12) for connection errors
   - Look for logs showing what URL the frontend is trying

2. **Reverse proxy not forwarding to correct port**
   - API should be accessible at the URL specified in `API_URL`
   - Test: `curl https://your-domain.com/api/config` should return JSON

3. **CORS issues**
   - Ensure `X-Forwarded-Proto` and `X-Forwarded-For` headers are set in proxy config
   - Check API logs for CORS errors

4. **SSL/TLS certificate issues**
   - Ensure your reverse proxy has valid SSL certificates
   - Mixed content errors (HTTPS frontend trying to reach HTTP API)

### Frontend adds `:5055` to URL when using reverse proxy (versions ≤ 1.0.10)

**Symptoms** (only in versions 1.0.10 and earlier):
- You set `API_URL=https://your-domain.com`
- Browser console shows: "Attempted URL: https://your-domain.com:5055/api/config"
- CORS errors with "Status code: (null)"

**Root Cause**:
In versions ≤ 1.0.10, the frontend's config endpoint was at `/api/runtime-config`, which gets intercepted by reverse proxies routing all `/api/*` requests to the backend. This prevented the frontend from reading the `API_URL` environment variable.

**Solution**:
Upgrade to version 1.0.11 or later. The config endpoint has been moved to `/config` which avoids the `/api/*` routing conflict.

**Note**: Most reverse proxy configurations with a catch-all rule like `location / { proxy_pass http://frontend; }` will automatically route `/config` to the frontend without any additional configuration needed.

**Only if you have issues**, explicitly configure the `/config` route:

```nginx
# Only needed if your reverse proxy doesn't have a catch-all rule
location = /config {
    proxy_pass http://open-notebook:8502;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Verification**:
Check browser console (F12) - should see: `✅ [Config] Runtime API URL from server: https://your-domain.com`

### How to Debug

1. **Check browser console** (F12 → Console tab):
   - Look for messages starting with `🔧 [Config]`
   - These show the configuration detection process
   - You'll see which API URL is being used

2. **Test API directly**:
   ```bash
   # Should return JSON config
   curl https://your-domain.com/api/config
   ```

3. **Check Docker logs**:
   ```bash
   docker logs open-notebook
   ```
   - Look for frontend and API startup messages
   - Check for connection errors

4. **Verify environment variable**:
   ```bash
   docker exec open-notebook env | grep API_URL
   ```

### Missing Authorization Header

**Symptoms**: API returns `{"detail": "Missing authorization header"}`

This happens when:
- You have set `OPEN_NOTEBOOK_PASSWORD` for authentication
- You're trying to access `/api/config` directly without logging in first

**Solution**: This is expected behavior! The frontend handles this automatically. Just access the frontend URL and log in through the UI.

## Best Practices

1. **Always use HTTPS** in production with reverse proxies
2. **Set `API_URL` explicitly** when using reverse proxies to avoid auto-detection issues
3. **Use environment files** (`.env` or `docker.env`) to manage configuration
4. **Test your setup** by accessing the frontend and checking browser console logs
5. **Keep ports 5055 and 8502 accessible** from your reverse proxy container

## Additional Resources

- [Docker Deployment Guide](./docker.md)
- [Security Guide](./security.md)
- [Troubleshooting](../troubleshooting/common-issues.md)
