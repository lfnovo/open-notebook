# Reverse Proxy Configuration

Deploy Open Notebook behind nginx, Caddy, Traefik, or other reverse proxies with custom domains and HTTPS.

---

## Simplified Setup (v1.1+)

Starting with v1.1, Open Notebook uses Next.js rewrites to simplify configuration. **You only need to proxy to one port** - Next.js handles internal API routing automatically.

### How It Works

```
Browser → Reverse Proxy → Port 8502 (Next.js)
                             ↓ (internal proxy)
                          Port 5055 (FastAPI)
```

Next.js automatically forwards `/api/*` requests to the FastAPI backend, so your reverse proxy only needs one port!

---

## Quick Configuration Examples

### Nginx (Recommended)

```nginx
server {
    listen 443 ssl http2;
    server_name notebook.example.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # Allow file uploads up to 100MB
    client_max_body_size 100M;

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

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name notebook.example.com;
    return 301 https://$server_name$request_uri;
}
```

### Caddy

```caddy
notebook.example.com {
    reverse_proxy open-notebook:8502
}
```

That's it! Caddy handles HTTPS automatically.

### Traefik

```yaml
services:
  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    pull_policy: always
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

### Coolify

1. Create new service with `lfnovo/open_notebook:v1-latest-single`
2. Set port to **8502**
3. Add environment: `API_URL=https://your-domain.com`
4. Enable HTTPS in Coolify
5. Done!

---

## Environment Variables

```bash
# Required for reverse proxy setups
API_URL=https://your-domain.com

# Optional: For multi-container deployments
# INTERNAL_API_URL=http://api-service:5055
```

**Important**: Set `API_URL` to your public URL (with https://).

---

## Understanding API_URL

The frontend uses a three-tier priority system to determine the API URL:

1. **Runtime Configuration** (Highest Priority): `API_URL` environment variable set at container runtime
2. **Build-time Configuration**: `NEXT_PUBLIC_API_URL` baked into the Docker image
3. **Auto-detection** (Fallback): Infers from the incoming HTTP request headers

### Auto-Detection Details

When `API_URL` is not set, the Next.js frontend:
- Analyzes the incoming HTTP request
- Extracts the hostname from the `host` header
- Respects the `X-Forwarded-Proto` header (for HTTPS behind reverse proxies)
- Constructs the API URL as `{protocol}://{hostname}:5055`
- Example: Request to `http://10.20.30.20:8502` → API URL becomes `http://10.20.30.20:5055`

**Why set API_URL explicitly?**
- **Reliability**: Auto-detection can fail with complex proxy setups
- **HTTPS**: Ensures frontend uses `https://` when behind SSL-terminating proxy
- **Custom domains**: Works correctly with domain names instead of IP addresses
- **Port mapping**: Avoids exposing port 5055 in the URL when using reverse proxy

**Important**: Don't include `/api` at the end - the system adds this automatically!

---

## Complete Docker Compose Example

```yaml
services:
  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    pull_policy: always
    container_name: open-notebook
    environment:
      - API_URL=https://notebook.example.com
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPEN_NOTEBOOK_PASSWORD=${OPEN_NOTEBOOK_PASSWORD}
    volumes:
      - ./notebook_data:/app/data
      - ./surreal_data:/mydata
    # Only expose to localhost (nginx handles public access)
    ports:
      - "127.0.0.1:8502:8502"
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

---

## Full Nginx Configuration

```nginx
events {
    worker_connections 1024;
}

http {
    upstream notebook {
        server open-notebook:8502;
    }

    # HTTP redirect
    server {
        listen 80;
        server_name notebook.example.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name notebook.example.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Allow file uploads up to 100MB
        client_max_body_size 100M;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # Proxy settings
        location / {
            proxy_pass http://notebook;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_cache_bypass $http_upgrade;

            # Timeouts for long-running operations (podcasts, etc.)
            proxy_read_timeout 300s;
            proxy_connect_timeout 60s;
            proxy_send_timeout 300s;
        }
    }
}
```

---

## Direct API Access (Optional)

If external scripts or integrations need direct API access, route `/api/*` directly:

```nginx
# Direct API access (for external integrations)
location /api/ {
    proxy_pass http://open-notebook:5055/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Frontend (handles all other traffic)
location / {
    proxy_pass http://open-notebook:8502;
    # ... same headers as above
}
```

**Note**: This is only needed for external API integrations. Browser traffic works fine with single-port setup.

---

## Advanced Scenarios

### Remote Server Access (LAN/VPS)

Accessing Open Notebook from a different machine on your network:

**Step 1: Get your server IP**
```bash
# On the server running Open Notebook:
hostname -I
# or
ifconfig | grep "inet "
# Note the IP (e.g., 192.168.1.100)
```

**Step 2: Configure API_URL**
```bash
# In docker-compose.yml or .env:
API_URL=http://192.168.1.100:5055
```

**Step 3: Expose ports**
```yaml
services:
  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    pull_policy: always
    environment:
      - API_URL=http://192.168.1.100:5055
    ports:
      - "8502:8502"
      - "5055:5055"
```

**Step 4: Access from client machine**
```bash
# In browser on other machine:
http://192.168.1.100:8502
```

**Troubleshooting**:
- Check firewall: `sudo ufw allow 8502 && sudo ufw allow 5055`
- Verify connectivity: `ping 192.168.1.100` from client machine
- Test port: `telnet 192.168.1.100 8502` from client machine

---

### API on Separate Subdomain

Host the API and frontend on different subdomains:

**docker-compose.yml:**
```yaml
services:
  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
    pull_policy: always
    environment:
      - API_URL=https://api.notebook.example.com
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    # Don't expose ports (nginx handles routing)
```

**nginx.conf:**
```nginx
# Frontend server
server {
    listen 443 ssl http2;
    server_name notebook.example.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

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

# API server (separate subdomain)
server {
    listen 443 ssl http2;
    server_name api.notebook.example.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    location / {
        proxy_pass http://open-notebook:5055;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Use case**: Separate DNS records, different rate limiting, or isolated API access control.

---

### Multi-Container Deployment (Advanced)

For complex deployments with separate frontend and API containers:

**docker-compose.yml:**
```yaml
services:
  frontend:
    image: lfnovo/open_notebook_frontend:v1-latest
    pull_policy: always
    environment:
      - API_URL=https://notebook.example.com
    ports:
      - "8502:8502"

  api:
    image: lfnovo/open_notebook_api:v1-latest
    pull_policy: always
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "5055:5055"
    depends_on:
      - surrealdb

  surrealdb:
    image: surrealdb/surrealdb:latest
    command: start --log trace --user root --pass root file:/mydata/database.db
    ports:
      - "8000:8000"
    volumes:
      - ./surreal_data:/mydata
```

**nginx.conf:**
```nginx
http {
    upstream frontend {
        server frontend:8502;
    }

    upstream api {
        server api:5055;
    }

    server {
        listen 443 ssl http2;
        server_name notebook.example.com;

        # API routes
        location /api/ {
            proxy_pass http://api/api/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Frontend (catch-all)
        location / {
            proxy_pass http://frontend;
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
}
```

**Note**: Most users should use the single-container approach (`v1-latest-single`). Multi-container is only needed for custom scaling or isolation requirements.

---

## SSL Certificates

### Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d notebook.example.com

# Auto-renewal (usually configured automatically)
sudo certbot renew --dry-run
```

### Let's Encrypt with Caddy

Caddy handles SSL automatically - no configuration needed!

### Self-Signed (Development Only)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/privkey.pem \
  -out ssl/fullchain.pem \
  -subj "/CN=localhost"
```

---

## Troubleshooting

### "Unable to connect to server"

1. **Check API_URL is set**:
   ```bash
   docker exec open-notebook env | grep API_URL
   ```

2. **Verify reverse proxy reaches container**:
   ```bash
   curl -I http://localhost:8502
   ```

3. **Check browser console** (F12):
   - Look for connection errors
   - Check what URL it's trying to reach

### Mixed Content Errors

Frontend using HTTPS but trying to reach HTTP API:

```bash
# Ensure API_URL uses https://
API_URL=https://notebook.example.com  # Not http://
```

### WebSocket Issues

Ensure your proxy supports WebSocket upgrades:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection 'upgrade';
```

### 502 Bad Gateway

1. Check container is running: `docker ps`
2. Check container logs: `docker logs open-notebook`
3. Verify nginx can reach container (same network)

### Timeout Errors

Increase timeouts for long operations (podcast generation):

```nginx
proxy_read_timeout 300s;
proxy_send_timeout 300s;
```

---

### How to Debug Configuration Issues

**Step 1: Check browser console** (F12 → Console tab)
```
Look for messages starting with 🔧 [Config]
These show the configuration detection process
You'll see which API URL is being used
```

**Example good output:**
```
✅ [Config] Runtime API URL from server: https://your-domain.com
```

**Example bad output:**
```
❌ [Config] Failed to fetch runtime config
⚠️  [Config] Using auto-detected URL: http://localhost:5055
```

**Step 2: Test API directly**
```bash
# Should return JSON config
curl https://your-domain.com/api/config

# Expected output:
{"openai_api_key_set":true,"anthropic_api_key_set":false,...}
```

**Step 3: Check Docker logs**
```bash
docker logs open-notebook

# Look for:
# - Frontend startup: "▲ Next.js ready on http://0.0.0.0:8502"
# - API startup: "INFO:     Uvicorn running on http://0.0.0.0:5055"
# - Connection errors or CORS issues
```

**Step 4: Verify environment variable**
```bash
docker exec open-notebook env | grep API_URL

# Should show:
# API_URL=https://your-domain.com
```

---

### Frontend Adds `:5055` to URL (Versions ≤ 1.0.10)

**Symptoms** (only in older versions):
- You set `API_URL=https://your-domain.com`
- Browser console shows: "Attempted URL: https://your-domain.com:5055/api/config"
- CORS errors with "Status code: (null)"

**Root Cause:**
In versions ≤ 1.0.10, the frontend's config endpoint was at `/api/runtime-config`, which got intercepted by reverse proxies routing all `/api/*` requests to the backend. This prevented the frontend from reading the `API_URL` environment variable.

**Solution:**
Upgrade to version 1.0.11 or later. The config endpoint has been moved to `/config` which avoids the `/api/*` routing conflict.

**Verification:**
Check browser console (F12) - should see: `✅ [Config] Runtime API URL from server: https://your-domain.com`

**If you can't upgrade**, explicitly configure the `/config` route:
```nginx
# Only needed for versions ≤ 1.0.10
location = /config {
    proxy_pass http://open-notebook:8502;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

---

### File Upload Errors (413 Payload Too Large)

**Symptoms:**
```
CORS header 'Access-Control-Allow-Origin' missing. Status code: 413.
Error creating source. Please try again.
```

**Root Cause:**
When uploading files, your reverse proxy may reject the request due to body size limits *before* it reaches the application. Since the error happens at the proxy level, CORS headers are not included in the response.

**Version Requirement:**
- **Open Notebook v1.3.2+** is required for file uploads >10MB
- Uses Next.js 16+ which supports the `proxyClientMaxBodySize` configuration option
- Check your version: Settings → About (bottom of settings page)

**Solutions:**

1. **Nginx - Increase body size limit**:
   ```nginx
   server {
       # Allow larger file uploads (default is 1MB)
       client_max_body_size 100M;

       # Add CORS headers to error responses
       error_page 413 = @cors_error_413;

       location @cors_error_413 {
           add_header 'Access-Control-Allow-Origin' '*' always;
           add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
           add_header 'Access-Control-Allow-Headers' '*' always;
           return 413 '{"detail": "File too large. Maximum size is 100MB."}';
       }

       location / {
           # ... your existing proxy configuration
       }
   }
   ```

2. **Traefik - Increase buffer size**:
   ```yaml
   # In your traefik configuration
   http:
     middlewares:
       large-body:
         buffering:
           maxRequestBodyBytes: 104857600  # 100MB
   ```

   Apply middleware to your router:
   ```yaml
   labels:
     - "traefik.http.routers.notebook.middlewares=large-body"
   ```

3. **Kubernetes Ingress (nginx-ingress)**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: open-notebook
     annotations:
       nginx.ingress.kubernetes.io/proxy-body-size: "100m"
       # Add CORS headers for error responses
       nginx.ingress.kubernetes.io/configuration-snippet: |
         more_set_headers "Access-Control-Allow-Origin: *";
   ```

4. **Caddy**:
   ```caddy
   notebook.example.com {
       request_body {
           max_size 100MB
       }
       reverse_proxy open-notebook:8502
   }
   ```

**Note:** Open Notebook's API includes CORS headers in error responses, but this only works for errors that reach the application. Proxy-level errors (like 413 from nginx) need to be configured at the proxy level.

---

### CORS Errors

**Symptoms:**
```
Access-Control-Allow-Origin header is missing
Cross-Origin Request Blocked
Response to preflight request doesn't pass access control check
```

**Possible Causes:**

1. **Missing proxy headers**:
   ```nginx
   # Make sure these are set:
   proxy_set_header X-Forwarded-Proto $scheme;
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   proxy_set_header Host $host;
   ```

2. **API_URL protocol mismatch**:
   ```bash
   # Frontend is HTTPS, but API_URL is HTTP:
   API_URL=http://notebook.example.com  # ❌ Wrong
   API_URL=https://notebook.example.com # ✅ Correct
   ```

3. **Reverse proxy not forwarding `/api/*` correctly**:
   ```nginx
   # Make sure this works:
   location /api/ {
       proxy_pass http://open-notebook:5055/api/;  # Note the trailing slash!
   }
   ```

---

### Missing Authorization Header

**Symptoms:**
```json
{"detail": "Missing authorization header"}
```

This happens when:
- You have set `OPEN_NOTEBOOK_PASSWORD` for authentication
- You're trying to access `/api/config` directly without logging in first

**Solution:**
This is **expected behavior**! The frontend handles authentication automatically. Just:
1. Access the frontend URL (not `/api/` directly)
2. Log in through the UI
3. The frontend will handle authorization headers for all API calls

**For API integrations:** Include the password in the Authorization header:
```bash
curl -H "Authorization: Bearer your-password-here" \
  https://your-domain.com/api/config
```

---

### SSL/TLS Certificate Errors

**Symptoms:**
- Browser shows "Your connection is not private"
- Certificate warnings
- Mixed content errors

**Solutions:**

1. **Use Let's Encrypt** (recommended):
   ```bash
   sudo certbot --nginx -d notebook.example.com
   ```

2. **Check certificate paths** in nginx:
   ```nginx
   ssl_certificate /etc/nginx/ssl/fullchain.pem;      # Full chain
   ssl_certificate_key /etc/nginx/ssl/privkey.pem;    # Private key
   ```

3. **Verify certificate is valid**:
   ```bash
   openssl x509 -in /etc/nginx/ssl/fullchain.pem -text -noout
   ```

4. **For development**, use self-signed (not for production):
   ```bash
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout ssl/privkey.pem -out ssl/fullchain.pem \
     -subj "/CN=localhost"
   ```

---

## Best Practices

1. **Always use HTTPS** in production
2. **Set API_URL explicitly** when using reverse proxies to avoid auto-detection issues
3. **Bind to localhost** (`127.0.0.1:8502`) and let proxy handle public access for security
4. **Enable security headers** (HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)
5. **Set up certificate renewal** for Let's Encrypt (usually automatic with certbot)
6. **Keep ports 5055 and 8502 accessible** from your reverse proxy container (use Docker networks)
7. **Use environment files** (`.env` or `docker.env`) to manage configuration securely
8. **Test your configuration** before going live:
   - Check browser console for config messages
   - Test API: `curl https://your-domain.com/api/config`
   - Verify authentication works
   - Check long-running operations (podcast generation)
9. **Monitor logs** regularly: `docker logs open-notebook`
10. **Don't include `/api` in API_URL** - the system adds this automatically

---

## Legacy Configurations (Pre-v1.1)

If you're running Open Notebook **version 1.0.x or earlier**, you may need to use the legacy two-port configuration where you explicitly route `/api/*` to port 5055.

**Check your version:**
```bash
docker exec open-notebook cat /app/package.json | grep version
```

**If version < 1.1.0**, you may need:
- Explicit `/api/*` routing to port 5055 in reverse proxy
- Explicit `/config` endpoint routing for versions ≤ 1.0.10
- See the "Frontend Adds `:5055` to URL" troubleshooting section above

**Recommendation:** Upgrade to v1.1+ for simplified configuration and better performance.

---

## Related

- **[Security Configuration](security.md)** - Password protection and hardening
- **[Advanced Configuration](advanced.md)** - Ports, timeouts, and SSL settings
- **[Troubleshooting](../6-TROUBLESHOOTING/connection-issues.md)** - Connection problems
- **[Docker Deployment](../1-INSTALLATION/docker-compose.md)** - Complete deployment guide
