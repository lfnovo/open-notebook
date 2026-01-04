# Connection Issues - Network & API Problems

Frontend can't reach API or services won't communicate.

---

## "Cannot connect to server" (Most Common)

**What it looks like:**
- Browser shows error page
- "Unable to reach API"
- "Cannot connect to server"
- UI loads but can't create notebooks

**Diagnosis:**

```bash
# Check if API is running
docker ps | grep api
# Should see "api" service running

# Check if API is responding
curl http://localhost:5055/health
# Should show: {"status":"ok"}

# Check if frontend is running
docker ps | grep frontend
# Should see "frontend" or React service running
```

**Solutions:**

### Solution 1: API Not Running
```bash
# Start API
docker compose up api -d

# Wait 5 seconds
sleep 5

# Verify it's running
docker compose logs api | tail -20
```

### Solution 2: Port Not Exposed
```bash
# Check docker-compose.yml has port mapping:
# api:
#   ports:
#     - "5055:5055"

# If missing, add it and restart:
docker compose down
docker compose up -d
```

### Solution 3: API_URL Mismatch
```bash
# In .env, check API_URL:
cat .env | grep API_URL

# Should match your frontend URL:
# Frontend: http://localhost:8502
# API_URL: http://localhost:5055

# If wrong, fix it:
# API_URL=http://localhost:5055
# Then restart:
docker compose restart frontend
```

### Solution 4: Firewall Blocking
```bash
# Verify port 5055 is accessible
netstat -tlnp | grep 5055
# Should show port listening

# If on different machine, try:
# Instead of localhost, use your IP:
API_URL=http://192.168.1.100:5055
```

### Solution 5: Services Not Started
```bash
# Restart everything
docker compose restart

# Wait 10 seconds
sleep 10

# Check all services
docker compose ps
# All should show "Up"
```

---

## Connection Refused

**What it looks like:**
```
Connection refused
ECONNREFUSED
Error: socket hang up
```

**Diagnosis:**
- API port (5055) not open
- API crashed
- Wrong IP/hostname

**Solution:**

```bash
# Step 1: Check if API is running
docker ps | grep api

# Step 2: Check if port is listening
lsof -i :5055
# or
netstat -tlnp | grep 5055

# Step 3: Check API logs
docker compose logs api | tail -30
# Look for errors

# Step 4: Restart API
docker compose restart api
docker compose logs api | grep -i "error"
```

---

## Timeout / Slow Connection

**What it looks like:**
- Page loads slowly
- Request times out
- "Gateway timeout" error

**Causes:**
- API is overloaded
- Network is slow
- Reverse proxy issue

**Solutions:**

### Check API Performance
```bash
# See CPU/memory usage
docker stats

# Check logs for slow operations
docker compose logs api | grep "slow\|timeout"
```

### Reduce Load
```bash
# In .env:
SURREAL_COMMANDS_MAX_TASKS=2
API_CLIENT_TIMEOUT=600

# Restart
docker compose restart
```

### Check Network
```bash
# Test latency
ping localhost

# Test API directly
time curl http://localhost:5055/health

# Should be < 100ms
```

---

## 502 Bad Gateway (Reverse Proxy)

**What it looks like:**
```
502 Bad Gateway
The server is temporarily unable to service the request
```

**Cause:** Reverse proxy can't reach API

**Solutions:**

### Check Backend is Running
```bash
# From the reverse proxy server
curl http://localhost:5055/health

# Should work
```

### Check Reverse Proxy Config
```nginx
# Nginx example (correct):
location /api {
    proxy_pass http://localhost:5055/api;
    proxy_http_version 1.1;
}

# Common mistake (wrong):
location /api {
    proxy_pass http://localhost:5055;  # Missing /api
}
```

### Set API_URL for HTTPS
```bash
# In .env:
API_URL=https://yourdomain.com

# Restart
docker compose restart
```

---

## Intermittent Disconnects

**What it looks like:**
- Works sometimes, fails other times
- Sporadic "cannot connect" errors
- Works then stops working

**Cause:** Transient network issue or database conflicts

**Solutions:**

### Enable Retry Logic
```bash
# In .env:
SURREAL_COMMANDS_RETRY_ENABLED=true
SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS=5
SURREAL_COMMANDS_RETRY_WAIT_STRATEGY=exponential_jitter

# Restart
docker compose restart
```

### Reduce Concurrency
```bash
# In .env:
SURREAL_COMMANDS_MAX_TASKS=2

# Restart
docker compose restart
```

### Check Network Stability
```bash
# Monitor connection
ping google.com

# Long-running test
ping -c 100 google.com | grep "packet loss"
# Should be 0% loss
```

---

## Different Machine / Remote Access

**You want to access Open Notebook from another computer**

**Solution:**

### Step 1: Get Your Machine IP
```bash
# On the server running Open Notebook:
ifconfig | grep "inet "
# or
hostname -I
# Note the IP (e.g., 192.168.1.100)
```

### Step 2: Update API_URL
```bash
# In .env:
API_URL=http://192.168.1.100:5055

# Restart
docker compose restart
```

### Step 3: Access from Other Machine
```bash
# In browser on other machine:
http://192.168.1.100:8502
# (or your server IP)
```

### Step 4: Verify Port is Exposed
```bash
# On server:
docker compose ps

# Should show port mapping:
# 0.0.0.0:8502->8502/tcp
# 0.0.0.0:5055->5055/tcp
```

### If Still Doesn't Work
```bash
# Check firewall on server
sudo ufw status
# May need to open ports:
sudo ufw allow 8502
sudo ufw allow 5055

# Check on different machine:
telnet 192.168.1.100 5055
# Should connect
```

---

## CORS Error (Browser Console)

**What it looks like:**
```
Cross-Origin Request Blocked
Access-Control-Allow-Origin
```

**In browser console (F12):**
```
CORS policy: Response to preflight request doesn't pass access control check
```

**Cause:** Frontend and API URLs don't match

**Solution:**

```bash
# Check browser console error for what URLs are being used
# The error shows:
# - Requesting from: http://localhost:8502
# - Trying to reach: http://localhost:5055

# Make sure API_URL matches:
API_URL=http://localhost:5055

# And protocol matches (http/https)
# Restart
docker compose restart frontend
```

---

## Testing Connection

**Full diagnostic:**

```bash
# 1. Services running?
docker compose ps
# All should show "Up"

# 2. Ports listening?
netstat -tlnp | grep -E "8502|5055|8000"

# 3. API responding?
curl http://localhost:5055/health

# 4. Frontend accessible?
curl http://localhost:8502 | head

# 5. Network OK?
ping google.com

# 6. No firewall?
sudo ufw status | grep -E "5055|8502|8000"
```

---

## Checklist for Remote Access

- [ ] Server IP noted (e.g., 192.168.1.100)
- [ ] Ports 8502, 5055, 8000 exposed in docker-compose
- [ ] API_URL set to server IP
- [ ] Firewall allows ports 8502, 5055, 8000
- [ ] Can reach server from client machine (ping IP)
- [ ] All services running (docker compose ps)
- [ ] Can curl API from client (curl http://IP:5055/health)

---

## SSL Certificate Errors

**What it looks like:**
```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
Connection error when using HTTPS endpoints
Works with HTTP but fails with HTTPS
```

**Cause:** Self-signed certificates not trusted by Python's SSL verification

**Solutions:**

### Solution 1: Use Custom CA Bundle (Recommended)
```bash
# In .env:
ESPERANTO_SSL_CA_BUNDLE=/path/to/your/ca-bundle.pem

# For Docker, mount the certificate:
# In docker-compose.yml:
volumes:
  - /path/to/your/ca-bundle.pem:/certs/ca-bundle.pem:ro
environment:
  - ESPERANTO_SSL_CA_BUNDLE=/certs/ca-bundle.pem
```

### Solution 2: Disable SSL Verification (Development Only)
```bash
# WARNING: Only use in trusted development environments
# In .env:
ESPERANTO_SSL_VERIFY=false
```

### Solution 3: Use HTTP Instead
If services are on a trusted local network, HTTP is acceptable:
```bash
# Change endpoint from https:// to http://
OPENAI_COMPATIBLE_BASE_URL=http://localhost:1234/v1
```

> **Security Note:** Disabling SSL verification exposes you to man-in-the-middle attacks. Always prefer custom CA bundle or HTTP on trusted networks.

---

## Still Having Issues?

- Check [Quick Fixes](quick-fixes.md)
- Check [FAQ](faq.md)
- Check logs: `docker compose logs`
- Try restart: `docker compose restart`
- Check firewall: `sudo ufw status`
- Ask for help on [Discord](https://discord.gg/37XJPXfz2w)
