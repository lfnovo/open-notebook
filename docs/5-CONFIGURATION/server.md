# Server - API & Network Configuration

Configuration for how Open Notebook's API and frontend communicate.

---

## Most Important: API_URL

**What it does:** Tells the frontend where to find the API.

**Default behavior:** Auto-detected (usually works!)

**When to set it:** Only if auto-detection doesn't work (reverse proxy, custom domain, etc.)

---

## Auto-Detection (Default)

Open Notebook automatically detects the API URL from your request:

```
You visit: http://localhost:8502
It detects: http://localhost:5055 (same host, port 5055)

You visit: http://myserver.com:8502
It detects: http://myserver.com:5055 (same host, port 5055)

You visit: https://myserver.com
It detects: https://myserver.com:5055 (same host, port 5055)
```

**This works because:**
- Frontend and API are usually on same host
- API is always on port 5055
- System uses the hostname you're accessing from

---

## When to Set API_URL

Set `API_URL` only in these cases:

### Case 1: Behind Reverse Proxy

```env
# You access via: https://mynotebook.example.com
# But API is actually: https://api.example.com:5055

API_URL=https://api.example.com:5055
```

### Case 2: Custom Domain

```env
# You access via: https://notebook.mycompany.com
# API should be at: https://notebook.mycompany.com/api

API_URL=https://notebook.mycompany.com
# System will auto-add /api to the end
```

### Case 3: Different Port

```env
# You access via: http://localhost:3055 (custom port)
# API is on: http://localhost:3055

API_URL=http://localhost:3055
```

### Case 4: Explicitly Disable Auto-Detection

```env
# Force a specific URL (override auto-detection)
API_URL=http://192.168.1.100:5055
```

---

## How to Configure

### Method 1: .env File (Development)

```env
# .env
API_URL=http://localhost:5055
```

Restart services:
```bash
make api  # or your restart command
```

### Method 2: docker.env (Docker)

```env
# docker.env
API_URL=https://mynotebook.example.com
```

Restart:
```bash
docker compose restart frontend
```

### Method 3: Environment Variable

```bash
export API_URL=https://mynotebook.example.com
docker compose up
```

### Method 4: docker-compose Override

```yaml
services:
  frontend:
    environment:
      - API_URL=https://mynotebook.example.com
```

---

## Port Configuration

### Default Ports

```
Frontend: 3000 (dev) or 8502 (docker)
API: 5055
SurrealDB: 8000
```

### Changing Frontend Port

Edit docker-compose.yml:

```yaml
services:
  frontend:
    ports:
      - "8001:8502"  # Change from 8502 to 8001
```

Access at: `http://localhost:8001`

API auto-detects to: `http://localhost:5055` ✓

### Changing API Port

```yaml
services:
  api:
    ports:
      - "5056:5055"  # Change from 5055 to 5056
    environment:
      - API_URL=http://localhost:5056  # Explicitly set
```

Access API directly: `http://localhost:5056/docs`

### Changing SurrealDB Port

```yaml
services:
  surrealdb:
    ports:
      - "8001:8000"  # Change from 8000 to 8001
    environment:
      - SURREAL_URL=ws://surrealdb:8001/rpc  # Update connection
```

---

## Timeouts

How long to wait before giving up on operations.

### API_CLIENT_TIMEOUT

Controls how long the frontend waits for API responses.

```env
# Default: 300 seconds (5 minutes)
API_CLIENT_TIMEOUT=300
```

**When to increase:**
- Using Ollama on CPU (slow)
- Remote servers with high latency
- Large document processing
- Slow embeddings

**Examples:**
```env
# Ollama on GPU
API_CLIENT_TIMEOUT=300  # Default is fine

# Ollama on CPU
API_CLIENT_TIMEOUT=600  # 10 minutes

# Very large documents
API_CLIENT_TIMEOUT=900  # 15 minutes
```

### ESPERANTO_LLM_TIMEOUT

Timeout for individual LLM API calls (at the library level).

```env
# Default: 60 seconds
ESPERANTO_LLM_TIMEOUT=60
```

**When to increase:**
- Large model inference times
- Self-hosted LLMs on slow hardware
- Rate-limited APIs

**Examples:**
```env
# OpenAI/Anthropic (fast)
ESPERANTO_LLM_TIMEOUT=60  # Default fine

# Ollama large models on CPU
ESPERANTO_LLM_TIMEOUT=180  # 3 minutes

# Self-hosted remote LLM
ESPERANTO_LLM_TIMEOUT=300  # 5 minutes
```

**Note:** Set `API_CLIENT_TIMEOUT` higher than `ESPERANTO_LLM_TIMEOUT` for proper error handling.

---

## SSL/HTTPS

### Basic Setup

If using HTTPS (reverse proxy, custom domain):

```env
API_URL=https://mynotebook.example.com
```

The system auto-detects protocol from your request (HTTP or HTTPS).

### Self-Signed Certificates

If using self-signed certs for local providers (Ollama, LM Studio behind proxy):

#### Option 1: Disable Verification (Development Only)

```env
# WARNING: Only for development/testing
# Exposes you to man-in-the-middle attacks
ESPERANTO_SSL_VERIFY=false
```

#### Option 2: Custom CA Bundle (Recommended)

```env
# Point to your CA certificate
ESPERANTO_SSL_CA_BUNDLE=/path/to/ca-bundle.pem
```

To create CA bundle:
```bash
# Copy your certificate
cp your-cert.pem /path/to/ca-bundle.pem

# Or combine multiple certs
cat cert1.pem cert2.pem > ca-bundle.pem
```

---

## Reverse Proxy Setup

If you're running Open Notebook behind Nginx, Traefik, etc.:

### Nginx Example

```nginx
server {
    server_name mynotebook.example.com;
    listen 443 ssl;

    # Configure SSL...
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:8502;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # API
    location /api {
        proxy_pass http://localhost:5055/api;
        proxy_http_version 1.1;
    }
}
```

Configuration:
```env
API_URL=https://mynotebook.example.com
```

### Cloudflare Reverse Proxy Example

```env
# If using Cloudflare or similar
API_URL=https://mynotebook.example.com

# You may need to preserve headers
# (Cloudflare usually handles this automatically)
```

---

## CORS Configuration

Open Notebook automatically configures CORS to allow:
- Same domain access
- Localhost access (for development)
- Your specified API_URL

**Usually no configuration needed.**

If you get CORS errors:
1. Check `API_URL` matches your frontend URL
2. Verify no typos in domain names
3. Ensure HTTPS vs HTTP matches throughout

---

## Health Check

Test if API is running and accessible:

```bash
# From your machine:
curl http://localhost:5055/health

# Expected response:
# {"status":"ok"}

# If behind reverse proxy:
curl https://mynotebook.example.com/health
```

---

## Testing Configuration

### Step 1: Start Services

```bash
docker compose up -d
```

### Step 2: Test Frontend

```bash
# Open in browser
http://localhost:8502  # or your custom port
```

### Step 3: Test API

```bash
# Direct API access
curl http://localhost:5055/docs

# Should show Swagger UI
```

### Step 4: Test Connection

```
1. Open Open Notebook in browser
2. Go to create notebook
3. If works, configuration is correct!
```

### Step 5: Check Logs

```bash
# If there's an issue
docker compose logs frontend | grep -i "api\|error"
docker compose logs api | grep -i "error"
```

---

## Troubleshooting

### "Cannot connect to API" or "Unable to reach server"

**Cause:** Frontend can't reach API

**Checks:**
1. Is API running? `docker ps | grep api`
2. Is port 5055 exposed? `netstat -tlnp | grep 5055`
3. Is `API_URL` correct? Check browser console (F12)
4. Is frontend accessing the right domain?

**Fix:**
```env
# Explicit API_URL
API_URL=http://localhost:5055
# Restart
docker compose restart
```

### "Mixed content" or HTTPS warning

**Cause:** Frontend is HTTPS but API is HTTP (or vice versa)

**Fix:**
```env
# Make both HTTPS
API_URL=https://mynotebook.example.com

# And ensure reverse proxy uses HTTPS
```

### Slow responses

**Cause:** Timeout too short for your setup

**Fix:**
```env
# Increase timeout
API_CLIENT_TIMEOUT=600
# Restart
docker compose restart
```

### 404 on /api endpoints

**Cause:** Reverse proxy not forwarding /api correctly

**Fix (Nginx example):**
```nginx
location /api {
    proxy_pass http://localhost:5055/api;  # Keep /api in path
}
```

---

## Summary

**For most setups:**
1. Leave `API_URL` unset (auto-detection works)
2. Keep default ports (3000/8502 frontend, 5055 API)
3. Only set `API_URL` if behind reverse proxy

**Quick checklist:**
- [ ] Frontend can access API (test with curl)
- [ ] Ports are exposed correctly
- [ ] `API_URL` matches your frontend URL
- [ ] HTTPS/HTTP consistent throughout
- [ ] Timeouts set for your hardware speed

If everything works, you're good!
