# Quick Fixes - Top 11 Issues & Solutions

Common problems with 1-minute solutions.

---

## #1: "Cannot connect to server"

**Symptom:** Browser shows error "Cannot connect to server" or "Unable to reach API"

**Cause:** Frontend can't reach API

**Solution (1 minute):**

```bash
# Step 1: Check if API is running
docker ps | grep api

# Step 2: Verify port 5055 is accessible
curl http://localhost:5055/health

# Expected output: {"status":"ok"}

# If that doesn't work:
# Step 3: Restart services
docker compose restart

# Step 4: Try again
# Open http://localhost:8502 in browser
```

**If still broken:**
- Check `API_URL` in .env (should match your frontend URL)
- See [Connection Issues](connection-issues.md)

---

## #2: "Invalid API key" or "Models not showing"

**Symptom:** Settings → Models shows "No models available"

**Cause:** API key missing, wrong, or not set

**Solution (1 minute):**

```bash
# Step 1: Check your .env has API key
cat .env | grep OPENAI_API_KEY

# Step 2: Verify it's correct (from https://platform.openai.com/api-keys)
# Should look like: sk-proj-xxx...

# Step 3: Restart services
docker compose restart api

# Step 4: Wait 10 seconds, then refresh browser
# Go to Settings → Models

# If still no models:
# Check logs for error
docker compose logs api | grep -i "api key\|error"
```

**If still broken:**
- Make sure key has no extra spaces
- Generate a fresh key from provider dashboard
- See [AI & Chat Issues](ai-chat-issues.md)

---

## #3: "Port X already in use"

**Symptom:** Docker error "Port 8502 is already allocated"

**Cause:** Another service using that port

**Solution (1 minute):**

```bash
# Option 1: Stop the other service
# Find what's using port 8502
lsof -i :8502
# Kill it or close the app

# Option 2: Use different port
# Edit docker-compose.yml
# Change: - "8502:8502"
# To:     - "8503:8502"

# Then restart
docker compose restart
# Access at: http://localhost:8503
```

---

## #4: "Cannot process file" or "Unsupported format"

**Symptom:** Upload fails or says "File format not supported"

**Cause:** File type not supported or too large

**Solution (1 minute):**

```bash
# Check if file format is supported:
# ✓ PDF, DOCX, PPTX, XLSX (documents)
# ✓ MP3, WAV, M4A (audio)
# ✓ MP4, AVI, MOV (video)
# ✓ URLs/web links

# ✗ Pure images (.jpg without OCR)
# ✗ Files > 100MB

# Try these:
# - Convert to PDF if possible
# - Split large files
# - Try uploading again
```

---

## #5: "Chat is very slow"

**Symptom:** Chat responses take minutes or timeout

**Cause:** Slow AI provider, large context, or overloaded system

**Solution (1 minute):**

```bash
# Step 1: Check which model you're using
# Settings → Models
# Note the model name

# Step 2: Try a cheaper/faster model
# OpenAI: Switch to gpt-4o-mini (10x cheaper, slightly faster)
# Anthropic: Switch to claude-3-5-haiku (fastest)
# Groq: Use any model (ultra-fast)

# Step 3: Reduce context
# Chat: Select fewer sources
# Use "Summary Only" instead of "Full Content"

# Step 4: Check if API is overloaded
docker stats
# Look at CPU/memory usage
```

For deep dive: See [AI & Chat Issues](ai-chat-issues.md)

---

## #6: "Chat gives bad responses"

**Symptom:** AI responses are generic, wrong, or irrelevant

**Cause:** Bad context, vague question, or wrong model

**Solution (1 minute):**

```bash
# Step 1: Make sure sources are in context
# Click "Select Sources" in Chat
# Verify relevant sources are checked and set to "Full Content"

# Step 2: Ask a specific question
# Bad: "What do you think?"
# Good: "Based on the paper's methodology section, what are the 3 main limitations?"

# Step 3: Try a more powerful model
# OpenAI: Use gpt-4o (better reasoning)
# Anthropic: Use claude-3-5-sonnet (best reasoning)

# Step 4: Check citations
# Click citations to verify AI actually saw those sources
```

For detailed help: See [Chat Effectively](../3-USER-GUIDE/chat-effectively.md)

---

## #7: "Search returns nothing"

**Symptom:** Search shows 0 results even though content exists

**Cause:** Wrong search type or poor query

**Solution (1 minute):**

```bash
# Try a different search type:

# If you searched with KEYWORDS:
# Try VECTOR SEARCH instead
# (Concept-based, not keyword-based)

# If you searched for CONCEPTS:
# Try TEXT SEARCH instead
# (Look for specific words in your query)

# Try simpler search:
# Instead of: "How do transformers work in neural networks?"
# Try: "transformers" or "neural networks"

# Check sources are processed:
# Go to notebook
# All sources should show green "Ready" status
```

For detailed help: See [Search Effectively](../3-USER-GUIDE/search.md)

---

## #8: "Podcast generation failed"

**Symptom:** "Podcast generation failed" error

**Cause:** Insufficient content, API quota, or network issue

**Solution (1 minute):**

```bash
# Step 1: Make sure you have content
# Select at least 1-2 sources
# Avoid single-sentence sources

# Step 2: Try again
# Sometimes it's a temporary API issue
# Wait 30 seconds and retry

# Step 3: Check your TTS provider has quota
# OpenAI: Check account has credits
# ElevenLabs: Check monthly quota
# Google: Check API quota

# Step 4: Try different TTS provider
# In podcast generation, choose "Google" or "Local"
# instead of "ElevenLabs"
```

For detailed help: See [FAQ](faq.md)

---

## #9: "Services won't start" or Docker error

**Symptom:** Docker error when running `docker compose up`

**Cause:** Corrupt configuration, permission issue, or resource issue

**Solution (1 minute):**

```bash
# Step 1: Check logs
docker compose logs

# Step 2: Try restart
docker compose restart

# Step 3: If that fails, rebuild
docker compose down
docker compose up --build

# Step 4: Check disk space
df -h
# Need at least 5GB free

# Step 5: Check Docker has enough memory
# Docker settings → Resources → Memory: 4GB+
```

---

## #10: "Database says 'too many connections'"

**Symptom:** Error about database connections

**Cause:** Too many concurrent operations

**Solution (1 minute):**

```bash
# In .env, reduce concurrency:
SURREAL_COMMANDS_MAX_TASKS=2

# Then restart:
docker compose restart

# This makes it slower but more stable
```

---

## #11: Slow Startup or Download Timeouts (China/Slow Networks)

**Symptom:** Container crashes on startup, worker enters FATAL state, or pip/uv downloads fail

**Cause:** Slow network or restricted access to Python package repositories

**Solution:**

### Increase Download Timeout
```yaml
# In docker-compose.yml environment:
environment:
  - UV_HTTP_TIMEOUT=600  # 10 minutes (default is 30s)
```

### Use Chinese Mirrors (if in China)
```yaml
environment:
  - UV_HTTP_TIMEOUT=600
  - UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
  - PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

**Alternative Chinese mirrors:**
- Tsinghua: `https://pypi.tuna.tsinghua.edu.cn/simple`
- Aliyun: `https://mirrors.aliyun.com/pypi/simple/`
- Huawei: `https://repo.huaweicloud.com/repository/pypi/simple`

**Note:** First startup may take several minutes while dependencies download. Subsequent starts will be faster.

---

## Quick Troubleshooting Checklist

When something breaks:

- [ ] **Restart services:** `docker compose restart`
- [ ] **Check logs:** `docker compose logs`
- [ ] **Verify connectivity:** `curl http://localhost:5055/health`
- [ ] **Check .env:** API keys set? API_URL correct?
- [ ] **Check resources:** `docker stats` (CPU/memory)
- [ ] **Clear cache:** `docker system prune` (free space)
- [ ] **Rebuild if needed:** `docker compose up --build`

---

## Nuclear Options (Last Resort)

**Completely reset (will lose all data in Docker):**

```bash
docker compose down -v
docker compose up --build
```

**Reset to defaults:**
```bash
# Backup your .env first!
cp .env .env.backup

# Reset to example
cp .env.example .env

# Edit with your API keys
# Restart
docker compose up
```

---

## Prevention Tips

1. **Keep backups** — Export your notebooks regularly
2. **Monitor logs** — Check `docker compose logs` periodically
3. **Update regularly** — Pull latest image: `docker pull lfnovo/open_notebook:latest`
4. **Document changes** — Keep notes on what you configured
5. **Test after updates** — Verify everything works

---

## Still Stuck?

- **Look up your exact error** in [Troubleshooting Index](index.md)
- **Check the FAQ** in [FAQ](faq.md)
- **Check logs:** `docker compose logs | head -50`
- **Ask for help:** [Discord](https://discord.gg/37XJPXfz2w) or [GitHub Issues](https://github.com/lfnovo/open-notebook/issues)
