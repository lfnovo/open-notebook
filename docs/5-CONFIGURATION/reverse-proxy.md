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

## Complete Docker Compose Example

```yaml
services:
  open-notebook:
    image: lfnovo/open_notebook:v1-latest-single
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

## Best Practices

1. **Always use HTTPS** in production
2. **Set API_URL explicitly** when using reverse proxies
3. **Bind to localhost** (`127.0.0.1:8502`) and let proxy handle public access
4. **Enable security headers** (HSTS, X-Frame-Options, etc.)
5. **Set up certificate renewal** for Let's Encrypt
6. **Test your configuration** before going live

---

## Related

- **[Security Configuration](security.md)** - Password protection and hardening
- **[Server Configuration](server.md)** - Ports and API settings
- **[Troubleshooting](../6-TROUBLESHOOTING/connection-issues.md)** - Connection problems
