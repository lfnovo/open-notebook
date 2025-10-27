# 5-Minute Troubleshooting

**Problem:** Something isn't working? Let's fix it fast.

## Start Here: What's Your Issue?

Click your problem:

### 1. ["Unable to connect to server" or blank page](#fix-connection-error)
### 2. [Container won't start or crashes](#fix-container-crash)
### 3. [Works on server but not from my computer](#fix-remote-access)
### 4. [API or authentication errors](#fix-api-errors)
### 5. [Slow or timeout errors](#fix-performance)

---

<a name="fix-connection-error"></a>
## Fix: "Unable to connect to server"

This means your frontend can't reach the API. **99% of the time, this is an API_URL problem.**

### Step-by-Step Fix:

1. **Check if API is running:**
   ```bash
   curl http://localhost:5055/health
   # Should return: {"status": "healthy"} or similar
   ```

   - ❌ **Connection refused?** → Port 5055 is not exposed. [Jump to port fix](#fix-missing-port)
   - ✅ **Got response?** → API is running, continue below.

2. **Are you accessing from a different machine?**

   - Your browser on **Computer A**
   - Docker running on **Computer B** (server, Raspberry Pi, NAS, etc.)

   → **You MUST set API_URL**

   Find your server's IP:
   ```bash
   # On the server running Docker:
   hostname -I    # Linux
   ipconfig       # Windows
   ifconfig       # Mac
   ```

   Set API_URL (replace 192.168.1.100 with YOUR server IP):

   **Docker Compose** - Add to your `docker-compose.yml`:
   ```yaml
   environment:
     - OPENAI_API_KEY=your_key
     - API_URL=http://192.168.1.100:5055
   ```

   **Docker Run** - Add this flag:
   ```bash
   -e API_URL=http://192.168.1.100:5055
   ```

   Then restart:
   ```bash
   docker compose down && docker compose up -d
   # or for docker run, stop and restart the container
   ```

3. **Still not working?**

   Check what URL your browser is trying to access:
   - Open browser DevTools (F12)
   - Go to Network tab
   - Refresh the page
   - Look for failed requests to `/api/config`

   The URL should match: `http://YOUR_SERVER_IP:5055/api/config`

   If it shows `localhost:5055` or wrong IP, your API_URL is not set correctly.

<a name="fix-missing-port"></a>
### Fix: Port 5055 Not Exposed

**Check currently exposed ports:**
```bash
docker ps
# Look for: 0.0.0.0:5055->5055
```

**Not there?** Add it:

**Docker Compose** - Update your `docker-compose.yml`:
```yaml
services:
  open_notebook:
    ports:
      - "8502:8502"
      - "5055:5055"  # Add this line!
```

**Docker Run** - Add `-p 5055:5055`:
```bash
docker run -d \
  -p 8502:8502 \
  -p 5055:5055 \  # Add this!
  # ... rest of your command
```

Then restart the container.

---

<a name="fix-container-crash"></a>
## Fix: Container Won't Start

**Check the logs:**
```bash
docker logs open-notebook
# or
docker compose logs
```

### Common causes:

| Error Message | Fix |
|---------------|-----|
| "Port already in use" | Change port: `-p 8503:8502` or stop conflicting service |
| "Permission denied" | Add user to docker group: `sudo usermod -aG docker $USER` (then log out/in) |
| "Invalid API key" | Check OPENAI_API_KEY in environment variables |
| "Out of memory" | Increase Docker memory limit to 2GB+ in Docker Desktop settings |
| "No such file or directory" | Check volume paths exist and are accessible |

**Quick reset:**
```bash
docker compose down -v
docker compose up -d
```

---

<a name="fix-remote-access"></a>
## Fix: Works on Server But Not From My Computer

**Symptom:** Open Notebook works when accessed on the server itself (`localhost:8502`) but not from another computer.

**This is 100% an API_URL problem.**

✅ **The Fix:**

Your API_URL must match the URL you use to access Open Notebook.

| You access via | Set API_URL to |
|----------------|----------------|
| `http://192.168.1.50:8502` | `http://192.168.1.50:5055` |
| `http://myserver:8502` | `http://myserver:5055` |
| `http://10.0.0.5:8502` | `http://10.0.0.5:5055` |

**Apply the fix:**

1. Edit your `docker-compose.yml`:
   ```yaml
   environment:
     - OPENAI_API_KEY=your_key
     - API_URL=http://YOUR_SERVER_IP_OR_HOSTNAME:5055
   ```

2. Or edit your `docker.env` file:
   ```env
   API_URL=http://YOUR_SERVER_IP_OR_HOSTNAME:5055
   ```

3. Restart:
   ```bash
   docker compose down && docker compose up -d
   ```

**Common mistakes:**
- ❌ Using `localhost` in API_URL when accessing remotely
- ❌ Using your client computer's IP instead of the server's IP
- ❌ Adding `/api` to the end (it's automatic)

---

<a name="fix-api-errors"></a>
## Fix: API or Authentication Errors

### "Missing authorization header"

You have password auth enabled. Make sure it's set correctly:

```yaml
environment:
  - OPEN_NOTEBOOK_PASSWORD=your_password
```

Or provide the password when logging into the web interface.

### "API config endpoint returned status 404"

You added `/api` to API_URL. Remove it:

❌ **Wrong:** `API_URL=http://192.168.1.100:5055/api`

✅ **Correct:** `API_URL=http://192.168.1.100:5055`

The `/api` path is added automatically by the application.

### "Invalid API key" or "Incorrect API key"

1. Check key format (OpenAI keys start with `sk-`)
2. Verify you have credits in your provider account
3. Check for spaces around the key in your .env file:
   ```env
   # Wrong - has spaces
   OPENAI_API_KEY = sk-your-key

   # Correct
   OPENAI_API_KEY=sk-your-key
   ```
4. Test your key directly:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer YOUR_KEY"
   ```

---

<a name="fix-performance"></a>
## Fix: Slow or Timeout Errors

### Increase timeouts for local models:

If you're using Ollama or LM Studio:

```yaml
environment:
  - API_CLIENT_TIMEOUT=600  # 10 minutes
  - ESPERANTO_LLM_TIMEOUT=180  # 3 minutes
```

**Recommended timeouts by setup:**
- Cloud APIs (OpenAI, Anthropic): Default (300s)
- Local Ollama with GPU: 600s
- Local Ollama with CPU: 1200s
- Remote LM Studio: 900s

### Use faster models:

- **Cloud APIs:** OpenAI, Anthropic, Groq (fastest)
- **Local models:** Try smaller models first
  - Fast: `gemma2:2b`, `phi3:mini`
  - Medium: `llama3:8b`, `mistral:7b`
  - Slow: `llama3:70b`, `mixtral:8x7b`

### Preload local models:

```bash
# This prevents first-run delays
ollama run llama3
# Press Ctrl+D to exit after model loads
```

---

## Still Stuck?

### Collect diagnostics:

```bash
# Container status
docker ps

# Container logs (last 100 lines)
docker logs --tail 100 open-notebook > logs.txt

# Or for docker compose
docker compose logs --tail 100 > logs.txt

# Check resource usage
docker stats --no-stream
```

### Get help:

1. **[Discord](https://discord.gg/37XJPXfz2w)** - Fastest response from community
2. **[GitHub Issues](https://github.com/lfnovo/open-notebook/issues)** - Bug reports and features
3. **[Full Troubleshooting Guide](common-issues.md)** - More detailed solutions

**Before asking:**
- Include your `docker-compose.yml` (remove API keys!)
- Include relevant logs
- Describe your setup (local vs remote, OS, Docker version)
- What you've already tried

---

## Quick Reference: API_URL Settings

| Scenario | API_URL Value | Example |
|----------|---------------|---------|
| **Local access only** | Not needed | Leave unset |
| **Remote on same network** | `http://SERVER_IP:5055` | `http://192.168.1.100:5055` |
| **Remote with hostname** | `http://HOSTNAME:5055` | `http://myserver.local:5055` |
| **Behind reverse proxy (no SSL)** | `http://DOMAIN:5055` | `http://notebook.local:5055` |
| **Behind reverse proxy (SSL)** | `https://DOMAIN/api` | `https://notebook.example.com/api` |

**Remember:** The API_URL is from your **browser's perspective**, not the server's!
