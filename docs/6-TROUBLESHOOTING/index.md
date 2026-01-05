# Troubleshooting - Problem Solving Guide

Having issues? Use this guide to diagnose and fix problems.

---

## How to Use This Guide

**Step 1: Identify your problem**
- What's the symptom? (error message, behavior, something not working?)
- When did it happen? (during install, while using, after update?)

**Step 2: Find the right guide**
- Look below for your symptom
- Go to the specific troubleshooting guide

**Step 3: Follow the steps**
- Guides are organized by symptom, not by root cause
- Each has diagnostic steps and solutions

---

## Quick Problem Map

### During Installation

- **Docker won't start** → [Quick Fixes](quick-fixes.md#9-services-wont-start-or-docker-error)
- **Port already in use** → [Quick Fixes](quick-fixes.md#3-port-x-already-in-use)
- **Permission denied** → [Quick Fixes](quick-fixes.md#9-services-wont-start-or-docker-error)
- **Can't connect to database** → [Connection Issues](connection-issues.md)

### When Starting

- **API won't start** → [Quick Fixes](quick-fixes.md#9-services-wont-start-or-docker-error)
- **Frontend won't load** → [Connection Issues](connection-issues.md)
- **"Cannot connect to server" error** → [Connection Issues](connection-issues.md)

### Settings / Configuration

- **Models not showing** → [AI & Chat Issues](ai-chat-issues.md)
- **"Invalid API key"** → [AI & Chat Issues](ai-chat-issues.md)
- **Can't find Settings** → [Quick Fixes](quick-fixes.md)

### Using Features

- **Chat not working** → [AI & Chat Issues](ai-chat-issues.md)
- **Chat responses are slow** → [AI & Chat Issues](ai-chat-issues.md)
- **Chat gives bad answers** → [AI & Chat Issues](ai-chat-issues.md)

### Adding Content

- **Can't upload PDF** → [Quick Fixes](quick-fixes.md#4-cannot-process-file-or-unsupported-format)
- **File won't process** → [Quick Fixes](quick-fixes.md#4-cannot-process-file-or-unsupported-format)
- **Web link won't extract** → [Quick Fixes](quick-fixes.md#4-cannot-process-file-or-unsupported-format)

### Search

- **Search returns no results** → [Quick Fixes](quick-fixes.md#7-search-returns-nothing)
- **Search returns wrong results** → [Quick Fixes](quick-fixes.md#7-search-returns-nothing)

### Podcasts

- **Can't generate podcast** → [Quick Fixes](quick-fixes.md#8-podcast-generation-failed)
- **Podcast audio is robotic** → [Quick Fixes](quick-fixes.md#8-podcast-generation-failed)
- **Podcast generation times out** → [Quick Fixes](quick-fixes.md#8-podcast-generation-failed)

---

## Troubleshooting by Error Message

### "Cannot connect to server"
→ [Connection Issues](connection-issues.md) — Frontend can't reach API

### "Invalid API key"
→ [AI & Chat Issues](ai-chat-issues.md) — Wrong or missing API key

### "Models not available"
→ [AI & Chat Issues](ai-chat-issues.md) — Model not configured

### "Connection refused"
→ [Connection Issues](connection-issues.md) — Service not running or port wrong

### "Port already in use"
→ [Quick Fixes](quick-fixes.md#3-port-x-already-in-use) — Port conflict

### "Permission denied"
→ [Quick Fixes](quick-fixes.md#9-services-wont-start-or-docker-error) — File permissions issue

### "Unsupported file type"
→ [Quick Fixes](quick-fixes.md#4-cannot-process-file-or-unsupported-format) — File format not supported

### "Processing timeout"
→ [Quick Fixes](quick-fixes.md#5-chat-is-very-slow) — File too large or slow processing

---

## Troubleshooting by Component

### Frontend (Browser/UI)
- Can't access UI → [Connection Issues](connection-issues.md)
- UI is slow → [Quick Fixes](quick-fixes.md)
- Button/feature missing → [Quick Fixes](quick-fixes.md)

### API (Backend)
- API won't start → [Quick Fixes](quick-fixes.md#9-services-wont-start-or-docker-error)
- API errors in logs → [Quick Fixes](quick-fixes.md#9-services-wont-start-or-docker-error)
- API is slow → [Quick Fixes](quick-fixes.md)

### Database
- Can't connect to database → [Connection Issues](connection-issues.md)
- Data lost after restart → [FAQ](faq.md#how-do-i-backup-my-data)

### AI / Chat
- Chat not working → [AI & Chat Issues](ai-chat-issues.md)
- Bad responses → [AI & Chat Issues](ai-chat-issues.md)
- Cost too high → [AI & Chat Issues](ai-chat-issues.md#high-api-costs)

### Sources
- Can't upload file → [Quick Fixes](quick-fixes.md#4-cannot-process-file-or-unsupported-format)
- File won't process → [Quick Fixes](quick-fixes.md#4-cannot-process-file-or-unsupported-format)

### Podcasts
- Won't generate → [Quick Fixes](quick-fixes.md#8-podcast-generation-failed)
- Bad audio quality → [Quick Fixes](quick-fixes.md#8-podcast-generation-failed)

---

## Diagnostic Checklist

**When something isn't working:**

- [ ] Check if services are running: `docker ps`
- [ ] Check logs: `docker compose logs api` (or frontend, surrealdb)
- [ ] Verify ports are exposed: `netstat -tlnp` or `lsof -i :5055`
- [ ] Test connectivity: `curl http://localhost:5055/health`
- [ ] Check environment variables: `docker inspect <container>`
- [ ] Try restarting: `docker compose restart`
- [ ] Check firewall/antivirus isn't blocking

---

## Getting Help

If you can't find the answer here:

1. **Check the relevant guide** — Read completely, try all steps
2. **Check the FAQ** — [Frequently Asked Questions](faq.md)
3. **Search our Discord** — Others may have had same issue
4. **Check logs** — Most issues show error messages in logs
5. **Report on GitHub** — Include error message, steps to reproduce

### How to Report an Issue

Include:
1. Error message (exact)
2. Steps to reproduce
3. Logs: `docker compose logs`
4. Your setup: Docker/local, provider, OS
5. What you've already tried

→ [Report on GitHub](https://github.com/lfnovo/open-notebook/issues)

---

## Guides

### [Quick Fixes](quick-fixes.md)
Top 10 most common issues with 1-minute solutions.

### [Connection Issues](connection-issues.md)
Frontend can't reach API, network problems.

### [AI & Chat Issues](ai-chat-issues.md)
Chat not working, bad responses, slow performance.

### [FAQ](faq.md)
Frequently asked questions about usage, costs, and best practices.

---

## Common Solutions

**Service won't start?**
```bash
# Check logs
docker compose logs

# Restart everything
docker compose restart

# Nuclear option: rebuild
docker compose down
docker compose up --build
```

**Port conflict?**
```bash
# Find what's using port 5055
lsof -i :5055
# Kill it or use different port
```

**Can't connect?**
```bash
# Test API directly
curl http://localhost:5055/health
# Should return: {"status":"ok"}
```

**Slow performance?**
```bash
# Check resource usage
docker stats

# Reduce concurrency in .env
SURREAL_COMMANDS_MAX_TASKS=2
```

**High costs?**
```bash
# Switch to cheaper model
# In Settings → Models → Choose gpt-4o-mini (OpenAI)
# Or use Ollama (free)
```

---

## Still Stuck?

**Before asking for help:**
1. Read the relevant guide completely
2. Try all the steps
3. Check the logs
4. Restart services
5. Search existing issues on GitHub

**Then:**
- **Discord**: https://discord.gg/37XJPXfz2w (fastest response)
- **GitHub Issues**: https://github.com/lfnovo/open-notebook/issues
