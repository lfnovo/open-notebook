# Database - SurrealDB Configuration

Open Notebook uses SurrealDB for data storage. This guide covers configuration (usually not needed).

---

## Default Configuration

In most deployments, SurrealDB is pre-configured. These settings work:

```env
SURREAL_URL="ws://surrealdb:8000/rpc"
SURREAL_USER="root"
SURREAL_PASSWORD="root"
SURREAL_NAMESPACE="open_notebook"
SURREAL_DATABASE="staging"
```

**If this is already configured, you can skip this page.**

---

## When to Change Configuration

You only need to change database configuration if:

1. **Using a remote SurrealDB** (not in Docker)
2. **Multiple databases** (dev/staging/production)
3. **Custom authentication** (not default credentials)
4. **Running your own SurrealDB** instance
5. **Advanced networking** (Kubernetes, proxies)

---

## Understanding the Settings

### SURREAL_URL

The connection URL for SurrealDB.

```env
# WebSocket protocol (recommended)
SURREAL_URL="ws://surrealdb:8000/rpc"

# HTTP protocol (alternative)
SURREAL_URL="http://surrealdb:8000"

# For remote instance
SURREAL_URL="ws://db.example.com:8000/rpc"

# With HTTPS
SURREAL_URL="wss://db.example.com:8000/rpc"
```

**Format:**
- Protocol: `ws://` (WebSocket) or `http://` (HTTP) or `wss://`, `https://`
- Host: `surrealdb` (Docker service name) or IP/domain
- Port: `8000` (default)
- Path: `/rpc` (for WebSocket)

**Docker to Docker:** Use service name
```
SURREAL_URL="ws://surrealdb:8000/rpc"  ✓ Correct
```

**Outside to Docker:** Use IP/domain
```
SURREAL_URL="ws://192.168.1.100:8000/rpc"  ✓ Correct
```

---

### SURREAL_USER & SURREAL_PASSWORD

Authentication credentials.

```env
SURREAL_USER="root"
SURREAL_PASSWORD="root"
```

**In production, change these!**

```env
SURREAL_USER="your_username"
SURREAL_PASSWORD="your_secure_password"
```

**Requirements:**
- Username: Any non-empty string
- Password: Any non-empty string
- No special characters recommended (can cause parsing issues)

---

### SURREAL_NAMESPACE

Logical grouping for multiple applications.

```env
SURREAL_NAMESPACE="open_notebook"
```

You can have multiple namespaces in one SurrealDB instance:
```
open_notebook
open_notebook_dev
open_notebook_test
```

**Typical setup:**
- Development: `open_notebook_dev`
- Staging: `open_notebook_staging`
- Production: `open_notebook_prod`

---

### SURREAL_DATABASE

Database within the namespace.

```env
SURREAL_DATABASE="staging"
```

Typical options:
```
staging     (development/testing)
production  (production data)
test        (automated tests)
backup      (archived data)
```

**Note:** Different databases in same namespace are completely separate.

---

## Setup Scenarios

### Scenario 1: Default Docker Setup (Most Common)

```env
# docker.env
SURREAL_URL="ws://surrealdb:8000/rpc"
SURREAL_USER="root"
SURREAL_PASSWORD="root"
SURREAL_NAMESPACE="open_notebook"
SURREAL_DATABASE="staging"
```

Used by the default docker-compose configuration. **No changes needed.**

---

### Scenario 2: Production with Custom Credentials

```env
# docker.env
SURREAL_URL="ws://surrealdb:8000/rpc"
SURREAL_USER="surrealdb_user"
SURREAL_PASSWORD="$(openssl rand -base64 32)"  # Generate secure password
SURREAL_NAMESPACE="open_notebook"
SURREAL_DATABASE="production"
```

Also configure SurrealDB with the same credentials:
```bash
docker run -e SURREAL_USER=surrealdb_user \
           -e SURREAL_PASSWORD=your_secure_password \
           surrealdb/surrealdb:v2
```

---

### Scenario 3: Remote SurrealDB Instance

```env
# .env
SURREAL_URL="ws://db.example.com:8000/rpc"
SURREAL_USER="your_username"
SURREAL_PASSWORD="your_password"
SURREAL_NAMESPACE="open_notebook"
SURREAL_DATABASE="staging"
```

Make sure:
- SurrealDB is running on remote server
- Port 8000 is accessible from your network
- Credentials match what you set on remote instance

---

### Scenario 4: Separate Databases for Dev/Test/Prod

```env
# dev .env
SURREAL_DATABASE="staging"

# prod .env
SURREAL_DATABASE="production"

# test .env
SURREAL_DATABASE="test"
```

All use same SurrealDB instance but different databases (completely isolated data).

---

## Running Your Own SurrealDB

If you need a separate SurrealDB instance:

### Option 1: Docker Container

```bash
docker run \
  --name surrealdb \
  -p 8000:8000 \
  -e SURREAL_USER=root \
  -e SURREAL_PASSWORD=root \
  surrealdb/surrealdb:v2 \
  start --bind 0.0.0.0:8000 --log trace --strict
```

Then configure Open Notebook:
```env
SURREAL_URL="ws://localhost:8000/rpc"
SURREAL_USER="root"
SURREAL_PASSWORD="root"
```

### Option 2: Install Locally

```bash
# Download from https://surrealdb.com/install
# Extract and run:
surreal start --bind 0.0.0.0:8000
```

Then configure:
```env
SURREAL_URL="ws://localhost:8000/rpc"
```

---

## Persistence and Storage

### In-Memory (Not Recommended)

```bash
# Data is lost on restart
surreal start --bind 0.0.0.0:8000 memory
```

### On-Disk (Recommended)

```bash
# Data persists
surreal start --bind 0.0.0.0:8000 file:./surreal.db
```

If using Docker Compose, the default includes volume mapping:

```yaml
services:
  surrealdb:
    image: surrealdb/surrealdb:v2
    volumes:
      - surreal_data:/data  # Data persists here
    command: start --bind 0.0.0.0:8000 file:/data/surreal.db
```

---

## Connection Testing

### Verify Connection

```bash
# Using curl to test WebSocket connection
curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     http://localhost:8000/rpc
```

### Check in Open Notebook

```
1. Start services
2. Go to Open Notebook
3. Try creating a notebook
4. If it works, database is connected
```

### Check API Logs

```bash
# For Docker
docker compose logs api | grep -i "surreal"

# Look for connection messages
```

---

## Troubleshooting

### "Cannot connect to database"

**Cause:** Connection URL is wrong or SurrealDB not running

**Fix:**
```bash
# Verify SurrealDB is running
docker ps | grep surrealdb

# Check connection URL is correct
# Try accessing directly: ws://localhost:8000 (use WebSocket client)
```

### "Authentication failed"

**Cause:** Username/password incorrect

**Fix:**
1. Check SURREAL_USER and SURREAL_PASSWORD in .env
2. Verify SurrealDB was started with same credentials
3. Credentials are case-sensitive

### "Timeout connecting to database"

**Cause:** Network/firewall issue

**Fix:**
1. Verify port 8000 is accessible
2. Check firewall rules
3. Use correct hostname/IP (not localhost if connecting from different container)

### "Connection lost during operation"

**Cause:** Network intermittent, SurrealDB restarting, or timeout

**Check** environment variable:
```env
# Increase retry configuration
SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS=5
SURREAL_COMMANDS_RETRY_WAIT_MAX=60
```

---

## Retry Configuration

For reliability with transient failures:

```env
# Enable retries (default: true)
SURREAL_COMMANDS_RETRY_ENABLED=true

# Maximum retry attempts (default: 3)
SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS=3

# Wait strategy between retries (default: exponential_jitter)
SURREAL_COMMANDS_RETRY_WAIT_STRATEGY=exponential_jitter

# Minimum wait (seconds, default: 1)
SURREAL_COMMANDS_RETRY_WAIT_MIN=1

# Maximum wait (seconds, default: 30)
SURREAL_COMMANDS_RETRY_WAIT_MAX=30
```

**Strategies:**
- `exponential_jitter` — Recommended (prevents thundering herd)
- `exponential` — Good for rate limiting
- `fixed` — Predictable retry timing
- `random` — Unpredictable timing

---

## Concurrency

Control how many concurrent database operations:

```env
# Maximum concurrent tasks (default: 5)
SURREAL_COMMANDS_MAX_TASKS=5
```

**Guidance:**
- Low-resource system: 1-2
- Normal system: 5 (recommended)
- High-resource system: 10-20

Higher concurrency increases speed but also increases database conflicts (retries handle this).

---

## Advanced: Kubernetes / Custom Networking

If using Kubernetes or complex networking:

```env
# Kubernetes example
SURREAL_URL="ws://surrealdb-service.default.svc.cluster.local:8000/rpc"
SURREAL_USER="your-user"
SURREAL_PASSWORD="your-password"
```

**Key points:**
- Use service DNS name, not IP
- Port must be exposed in service definition
- Credentials must match SurrealDB deployment

---

## Summary

**Default setup works for 99% of cases.**

Only change if:
1. Using separate/remote SurrealDB
2. Multiple databases (dev/prod separation)
3. Custom networking
4. Advanced deployment scenarios

If you're using the default docker-compose setup, **don't change anything on this page.**
